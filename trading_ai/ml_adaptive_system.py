#!/usr/bin/env python3
"""
ml_adaptive_system.py v2.0 - Sistema ML Adaptativo Mejorado

Nuevas capacidades:
- Analiza PATRONES de perdida (no solo estadisticas simples)
- Detecta rachas perdedoras y reacciona
- Auto-ajusta SL/TP por estrategia segun resultados reales
- Ajusta max_concurrent_trades y min_signal_interval
- Penaliza estrategias que pierden en contextos especificos
- Aprende de la hora del dia y volatilidad
"""

import json
import os
from datetime import datetime, timedelta
from collections import defaultdict
import statistics


class MLAdaptiveSystem:

    def __init__(self):
        self.config_file = "bot_config.json"
        self.ml_state_file = "learning_data/ml_state.json"
        self.history_file = "learning_data/trade_history.json"
        self.setup_stats_file = "learning_data/setup_stats.json"

        self.EXPLORATION_TRADES = 50
        self.LEARNING_TRADES = 200

        os.makedirs("learning_data", exist_ok=True)

        self.state = self.load_ml_state()

    def load_ml_state(self):
        if os.path.exists(self.ml_state_file):
            try:
                with open(self.ml_state_file, 'r') as f:
                    return json.load(f)
            except:
                pass

        return {
            "mode": "EXPLORATION",
            "total_trades": 0,
            "last_adjustment": None,
            "parameter_evolution": [],
            "strategy_performance": {},
            "market_context_memory": [],
            "best_strategy_per_context": {},
            "confidence_threshold_evolution": [35],
            "current_strategy_priority": {},
            "losing_patterns": [],
            "sl_tp_adjustments": {},
            "hourly_performance": {}
        }

    def save_ml_state(self):
        with open(self.ml_state_file, 'w') as f:
            json.dump(self.state, f, indent=4)

    def get_current_mode(self):
        total = self.get_total_trades()
        if total < self.EXPLORATION_TRADES:
            return "EXPLORATION"
        elif total < self.LEARNING_TRADES:
            return "LEARNING"
        else:
            return "OPTIMIZATION"

    def _load_trades(self):
        if not os.path.exists(self.history_file):
            return []
        try:
            with open(self.history_file, 'r') as f:
                history = json.load(f)
            if isinstance(history, list):
                return history
            return history.get("trades", [])
        except:
            return []

    def get_total_trades(self):
        return len(self._load_trades())

    def _detect_losing_patterns(self, trades):
        """
        Analiza patrones de perdida para evitar repetirlos.
        Detecta:
        - Estrategias que pierden en contextos especificos
        - Rachas perdedoras
        - Horas del dia con mal rendimiento
        """
        patterns = []

        if len(trades) < 10:
            return patterns

        recent = trades[-30:]

        # 1. Detectar rachas perdedoras por estrategia
        strategy_streaks = defaultdict(list)
        for t in recent:
            setup = t.get("setup", "UNKNOWN")
            strategy_streaks[setup].append(t.get("result", ""))

        for strat, results in strategy_streaks.items():
            # Contar racha actual de perdidas
            streak = 0
            for r in reversed(results):
                if r == "LOSS":
                    streak += 1
                else:
                    break

            if streak >= 3:
                patterns.append({
                    "type": "LOSING_STREAK",
                    "strategy": strat,
                    "streak": streak,
                    "action": "PAUSE",
                    "reason": f"{strat} tiene {streak} perdidas consecutivas"
                })

        # 2. Detectar hora del dia con mal rendimiento
        hourly_results = defaultdict(lambda: {"wins": 0, "losses": 0})
        for t in trades[-100:]:
            timestamp = t.get("timestamp", "")
            try:
                hour = int(timestamp[11:13]) if len(timestamp) > 13 else -1
            except (ValueError, IndexError):
                hour = -1

            if hour >= 0:
                if t.get("result") == "WIN":
                    hourly_results[hour]["wins"] += 1
                elif t.get("result") == "LOSS":
                    hourly_results[hour]["losses"] += 1

        for hour, data in hourly_results.items():
            total = data["wins"] + data["losses"]
            if total >= 5:
                wr = data["wins"] / total
                if wr < 0.30:
                    patterns.append({
                        "type": "BAD_HOUR",
                        "hour": hour,
                        "win_rate": wr,
                        "total": total,
                        "action": "AVOID",
                        "reason": f"Hora {hour}:00 tiene solo {wr:.0%} win rate en {total} trades"
                    })

        # Guardar rendimiento por hora
        self.state["hourly_performance"] = {
            str(h): {"wins": d["wins"], "losses": d["losses"]}
            for h, d in hourly_results.items()
        }

        return patterns

    def _analyze_sl_tp_effectiveness(self, trades):
        """
        Analiza si los SL/TP actuales son efectivos por estrategia.
        Sugiere ajustes basados en pips reales ganados/perdidos.
        """
        adjustments = {}

        if len(trades) < 20:
            return adjustments

        strategy_pips = defaultdict(lambda: {"win_pips": [], "loss_pips": []})

        for t in trades[-100:]:
            setup = t.get("setup", "UNKNOWN")
            pips = t.get("pips", 0)
            if t.get("result") == "WIN":
                strategy_pips[setup]["win_pips"].append(pips)
            elif t.get("result") == "LOSS":
                strategy_pips[setup]["loss_pips"].append(abs(pips))

        for strat, data in strategy_pips.items():
            if len(data["win_pips"]) >= 3 and len(data["loss_pips"]) >= 3:
                avg_win = statistics.mean(data["win_pips"])
                avg_loss = statistics.mean(data["loss_pips"])

                # Si las perdidas promedio son mucho mayores que las ganancias,
                # sugerir ajustar SL mas ajustado
                if avg_loss > avg_win * 1.5:
                    adjustments[strat] = {
                        "suggestion": "TIGHTEN_SL",
                        "avg_win_pips": round(avg_win, 1),
                        "avg_loss_pips": round(avg_loss, 1),
                        "reason": f"Perdidas promedio ({avg_loss:.1f}) >> Ganancias ({avg_win:.1f})"
                    }
                # Si las ganancias son consistentemente altas, ampliar TP
                elif avg_win > avg_loss * 2:
                    adjustments[strat] = {
                        "suggestion": "WIDEN_TP",
                        "avg_win_pips": round(avg_win, 1),
                        "avg_loss_pips": round(avg_loss, 1),
                        "reason": f"Ganancias promedio ({avg_win:.1f}) >> Perdidas ({avg_loss:.1f})"
                    }

        return adjustments

    def analyze_performance(self, last_n=50):
        try:
            trades = self._load_trades()
            if len(trades) < 10:
                return None

            recent = trades[-last_n:]

            wins = sum(1 for t in recent if t.get("result") == "WIN")
            losses = sum(1 for t in recent if t.get("result") == "LOSS")
            total = len(recent)
            win_rate = wins / total if total > 0 else 0

            profits = [t.get("pips", t.get("profit_pips", 0)) for t in recent]
            avg_profit = statistics.mean(profits) if profits else 0

            # Performance por estrategia
            strategy_perf = defaultdict(lambda: {"wins": 0, "total": 0, "profits": []})

            for t in recent:
                strategy = t.get("setup", "UNKNOWN")
                strategy_perf[strategy]["total"] += 1
                strategy_perf[strategy]["profits"].append(t.get("pips", t.get("profit_pips", 0)))
                if t.get("result") == "WIN":
                    strategy_perf[strategy]["wins"] += 1

            strategy_analysis = {}
            for strat, data in strategy_perf.items():
                if data["total"] >= 3:
                    wr = data["wins"] / data["total"]
                    avg_p = statistics.mean(data["profits"])
                    strategy_analysis[strat] = {
                        "win_rate": wr,
                        "avg_profit": avg_p,
                        "total_trades": data["total"],
                        "score": wr * max(avg_p, 0.1)
                    }

            # Performance por contexto
            context_perf = defaultdict(lambda: {"wins": 0, "total": 0})
            for t in recent:
                trend = t.get("market_context", {}).get("trend", "UNKNOWN")
                vol = t.get("market_context", {}).get("volatility", "UNKNOWN")
                context_key = f"{trend}_{vol}"
                context_perf[context_key]["total"] += 1
                if t.get("result") == "WIN":
                    context_perf[context_key]["wins"] += 1

            context_analysis = {}
            for ctx, data in context_perf.items():
                if data["total"] >= 3:
                    context_analysis[ctx] = {
                        "win_rate": data["wins"] / data["total"],
                        "total_trades": data["total"]
                    }

            # Confidence threshold analysis
            confidence_analysis = {}
            for threshold in [30, 35, 40, 45, 50, 55, 60]:
                eligible = [t for t in recent if t.get("confidence", 0) * 100 >= threshold]
                if len(eligible) >= 5:
                    wins_at = sum(1 for t in eligible if t.get("result") == "WIN")
                    confidence_analysis[threshold] = {
                        "win_rate": wins_at / len(eligible),
                        "trades": len(eligible)
                    }

            # Nuevos analisis
            losing_patterns = self._detect_losing_patterns(trades)
            sl_tp_analysis = self._analyze_sl_tp_effectiveness(trades)

            return {
                "overall": {
                    "win_rate": win_rate,
                    "avg_profit": avg_profit,
                    "total_trades": total,
                    "wins": wins,
                    "losses": losses
                },
                "by_strategy": strategy_analysis,
                "by_context": context_analysis,
                "by_confidence": confidence_analysis,
                "losing_patterns": losing_patterns,
                "sl_tp_analysis": sl_tp_analysis
            }

        except Exception as e:
            print(f"Error en analisis: {e}")
            return None

    def learn_and_adapt(self):
        mode = self.get_current_mode()
        total_trades = self.get_total_trades()
        performance = self.analyze_performance()

        if not performance:
            return None

        try:
            with open(self.config_file, 'r') as f:
                current_config = json.load(f)
        except:
            current_config = {
                "min_confidence": 35,
                "cooldown": 30,
                "max_daily_trades": 50,
                "max_concurrent_trades": 3,
                "min_signal_interval": 60
            }

        new_config = current_config.copy()
        changes = []
        strategy_priorities = {}
        overall = performance["overall"]

        # ==========================================
        # MODO EXPLORATION (0-50 trades)
        # ==========================================
        if mode == "EXPLORATION":
            new_config["min_confidence"] = 30
            new_config["cooldown"] = 15
            new_config["max_daily_trades"] = 100
            new_config["max_concurrent_trades"] = max(current_config.get("max_concurrent_trades", 3), 2)
            changes.append("EXPLORATION: Recolectando datos")

            strategy_priorities = {
                "MEAN_REVERSION": 1.0,
                "TREND_FOLLOWING": 1.0,
                "TREND_PULLBACK": 1.0,
                "BREAKOUT": 1.0,
                "MOMENTUM": 1.0,
                "SCALPING": 1.0,
                "RANGE_TRADING": 1.0,
                "VOLATILITY_BREAKOUT": 1.0
            }

        # ==========================================
        # MODO LEARNING (50-200 trades)
        # ==========================================
        elif mode == "LEARNING":
            by_strategy = performance["by_strategy"]
            by_confidence = performance["by_confidence"]

            # 1. Ajustar min_confidence
            optimal_conf = 35
            best_wr = 0
            for conf, data in by_confidence.items():
                if data["trades"] >= 10 and data["win_rate"] > best_wr:
                    best_wr = data["win_rate"]
                    optimal_conf = conf

            if best_wr > 0.52:
                new_config["min_confidence"] = optimal_conf
                changes.append(f"ML: Confidence optimo = {optimal_conf}% (WR: {best_wr:.1%})")
            else:
                if overall["win_rate"] < 0.45:
                    new_config["min_confidence"] = min(current_config.get("min_confidence", 35) + 5, 60)
                    changes.append(f"ML: WR bajo ({overall['win_rate']:.1%}) -> Mas selectivo")
                elif overall["win_rate"] > 0.55:
                    new_config["min_confidence"] = max(current_config.get("min_confidence", 35) - 3, 30)
                    changes.append(f"ML: WR alto ({overall['win_rate']:.1%}) -> Menos selectivo")

            # 2. Ajustar cooldown
            if overall["avg_profit"] < -0.5:
                new_config["cooldown"] = min(current_config.get("cooldown", 30) + 10, 120)
                changes.append("ML: Profit negativo -> Mayor cooldown")
            elif overall["avg_profit"] > 2.0:
                new_config["cooldown"] = max(current_config.get("cooldown", 30) - 5, 15)
                changes.append("ML: Profit alto -> Menor cooldown")

            # 3. Ajustar max_concurrent segun rendimiento
            if overall["win_rate"] >= 0.55 and overall["avg_profit"] > 0:
                new_config["max_concurrent_trades"] = min(
                    current_config.get("max_concurrent_trades", 3) + 1, 5)
                changes.append("ML: Buen rendimiento -> Mas trades concurrentes")
            elif overall["win_rate"] < 0.40:
                new_config["max_concurrent_trades"] = max(
                    current_config.get("max_concurrent_trades", 3) - 1, 1)
                changes.append("ML: Mal rendimiento -> Menos trades concurrentes")

            # 4. Priorizar estrategias
            if by_strategy:
                scores = [(s, d["score"]) for s, d in by_strategy.items()]
                max_score = max(s[1] for s in scores) if scores else 1

                for strat, score in scores:
                    normalized = score / max_score if max_score > 0 else 1
                    if normalized >= 0.8:
                        priority = 1.5
                    elif normalized >= 0.6:
                        priority = 1.2
                    elif normalized >= 0.4:
                        priority = 1.0
                    elif normalized >= 0.2:
                        priority = 0.8
                    else:
                        priority = 0.6
                    strategy_priorities[strat] = priority

                best_strat = max(by_strategy.items(), key=lambda x: x[1]["score"])
                changes.append(f"ML: Mejor estrategia = {best_strat[0]}")

            # 5. Aplicar patrones de perdida
            for pattern in performance.get("losing_patterns", []):
                if pattern["type"] == "LOSING_STREAK":
                    strat = pattern["strategy"]
                    if strat in strategy_priorities:
                        strategy_priorities[strat] *= 0.3  # Penalizar fuertemente
                    else:
                        strategy_priorities[strat] = 0.3
                    changes.append(f"ML: {strat} penalizada por racha perdedora ({pattern['streak']})")

        # ==========================================
        # MODO OPTIMIZATION (200+ trades)
        # ==========================================
        elif mode == "OPTIMIZATION":
            by_strategy = performance["by_strategy"]
            by_context = performance["by_context"]
            by_confidence = performance["by_confidence"]

            # 1. Optimizacion fina de confidence
            best_threshold = 40
            best_metric = 0
            for conf, data in by_confidence.items():
                if data["trades"] >= 15:
                    metric = data["win_rate"] * data["trades"]
                    if metric > best_metric:
                        best_metric = metric
                        best_threshold = conf

            new_config["min_confidence"] = best_threshold
            changes.append(f"OPT: Threshold = {best_threshold}%")

            # 2. Mapeo estrategia-contexto
            context_strategy_map = {}
            for ctx, ctx_data in by_context.items():
                if ctx_data["total_trades"] >= 5:
                    best_for_context = None
                    best_wr = 0
                    for strat, strat_data in by_strategy.items():
                        if strat_data["total_trades"] >= 3 and strat_data["win_rate"] > best_wr:
                            best_wr = strat_data["win_rate"]
                            best_for_context = strat
                    if best_for_context:
                        context_strategy_map[ctx] = best_for_context

            self.state["best_strategy_per_context"] = context_strategy_map

            # 3. Prioridades avanzadas
            if by_strategy:
                for strat, data in by_strategy.items():
                    if data["total_trades"] >= 5:
                        wr = data["win_rate"]
                        profit = data["avg_profit"]
                        quality_score = wr * 2 + (profit / 10)

                        if quality_score >= 1.5:
                            priority = 2.0
                        elif quality_score >= 1.2:
                            priority = 1.5
                        elif quality_score >= 0.9:
                            priority = 1.0
                        elif quality_score >= 0.6:
                            priority = 0.7
                        else:
                            priority = 0.4
                        strategy_priorities[strat] = priority

            # 4. Ajuste dinamico de concurrencia y trades diarios
            if overall["win_rate"] >= 0.55:
                new_config["max_daily_trades"] = 50
                new_config["max_concurrent_trades"] = min(
                    current_config.get("max_concurrent_trades", 3) + 1, 5)
            elif overall["win_rate"] >= 0.50:
                new_config["max_daily_trades"] = 30
            else:
                new_config["max_daily_trades"] = 20
                new_config["max_concurrent_trades"] = max(
                    current_config.get("max_concurrent_trades", 3) - 1, 1)

            # 5. Ajustar min_signal_interval segun velocidad de mercado
            if overall["avg_profit"] > 1.0 and overall["win_rate"] > 0.50:
                new_config["min_signal_interval"] = max(
                    current_config.get("min_signal_interval", 60) - 10, 30)
                changes.append("OPT: Mercado rentable -> Menor intervalo entre senales")
            elif overall["avg_profit"] < -0.5:
                new_config["min_signal_interval"] = min(
                    current_config.get("min_signal_interval", 60) + 15, 180)
                changes.append("OPT: Mercado desfavorable -> Mayor intervalo")

            # 6. Patrones de perdida
            for pattern in performance.get("losing_patterns", []):
                if pattern["type"] == "LOSING_STREAK":
                    strat = pattern["strategy"]
                    if strat in strategy_priorities:
                        strategy_priorities[strat] *= 0.2
                    else:
                        strategy_priorities[strat] = 0.2
                    changes.append(f"OPT: {strat} penalizada (racha {pattern['streak']}L)")

            # 7. Guardar analisis SL/TP
            sl_tp = performance.get("sl_tp_analysis", {})
            if sl_tp:
                self.state["sl_tp_adjustments"] = sl_tp
                for strat, adj in sl_tp.items():
                    changes.append(f"OPT SL/TP: {strat} -> {adj['suggestion']} ({adj['reason']})")

        # Guardar evolucion
        self.state["parameter_evolution"].append({
            "timestamp": datetime.now().isoformat(),
            "mode": mode,
            "total_trades": total_trades,
            "config": new_config,
            "changes": changes,
            "performance": overall
        })
        self.state["parameter_evolution"] = self.state["parameter_evolution"][-100:]

        # Guardar patrones de perdida
        self.state["losing_patterns"] = performance.get("losing_patterns", [])

        self.state["current_strategy_priority"] = strategy_priorities
        self.state["mode"] = mode
        self.state["total_trades"] = total_trades
        self.state["last_adjustment"] = datetime.now().isoformat()

        self.save_ml_state()

        return {
            "new_config": new_config,
            "changes": changes,
            "mode": mode,
            "strategy_priorities": strategy_priorities,
            "should_update": new_config != current_config,
            "losing_patterns": performance.get("losing_patterns", []),
            "sl_tp_analysis": performance.get("sl_tp_analysis", {})
        }

    def get_strategy_priority(self, strategy_name, market_context):
        base_priority = self.state.get("current_strategy_priority", {}).get(strategy_name, 1.0)
        mode = self.get_current_mode()

        if mode == "OPTIMIZATION":
            context_key = f"{market_context.get('trend', 'NONE')}_{market_context.get('volatility', 'NORMAL')}"
            best_for_context = self.state.get("best_strategy_per_context", {}).get(context_key)
            if best_for_context == strategy_name:
                return base_priority * 1.5

        # Verificar si esta en racha perdedora
        for pattern in self.state.get("losing_patterns", []):
            if pattern.get("type") == "LOSING_STREAK" and pattern.get("strategy") == strategy_name:
                return base_priority * 0.3

        return base_priority

    def should_adjust(self):
        total = self.get_total_trades()
        mode = self.get_current_mode()

        if mode == "EXPLORATION":
            return total > 0 and total % 25 == 0  # Cada 25 en exploracion

        elif mode == "LEARNING":
            return total > 0 and total % 10 == 0

        else:
            return total > 0 and total % 20 == 0  # Cada 20 en optimizacion (mas frecuente)

    def get_ml_report(self):
        mode = self.get_current_mode()
        total = self.get_total_trades()
        performance = self.analyze_performance()

        report = {
            "mode": mode,
            "total_trades": total,
            "progress": {},
            "current_performance": performance,
            "strategy_priorities": self.state.get("current_strategy_priority", {}),
            "learned_mappings": self.state.get("best_strategy_per_context", {}),
            "recent_adjustments": self.state.get("parameter_evolution", [])[-5:],
            "losing_patterns": self.state.get("losing_patterns", []),
            "sl_tp_adjustments": self.state.get("sl_tp_adjustments", {}),
            "hourly_performance": self.state.get("hourly_performance", {})
        }

        if mode == "EXPLORATION":
            report["progress"] = {
                "phase": "Recoleccion de datos",
                "current": total,
                "needed": self.EXPLORATION_TRADES,
                "percent": (total / self.EXPLORATION_TRADES) * 100
            }
        elif mode == "LEARNING":
            report["progress"] = {
                "phase": "Aprendizaje activo",
                "current": total,
                "needed": self.LEARNING_TRADES,
                "percent": (total / self.LEARNING_TRADES) * 100
            }
        else:
            report["progress"] = {
                "phase": "Optimizacion continua",
                "trades": total
            }

        return report


# ==========================================
# API FUNCTIONS
# ==========================================

def ml_auto_adjust():
    ml = MLAdaptiveSystem()

    if ml.should_adjust():
        result = ml.learn_and_adapt()

        if result and result["should_update"]:
            with open("bot_config.json", 'w') as f:
                json.dump(result["new_config"], f, indent=4)

            print("\n" + "=" * 70)
            print("SISTEMA ML - AJUSTE AUTOMATICO")
            print("=" * 70)
            print(f"Modo: {result['mode']}")
            print(f"Total trades: {ml.get_total_trades()}")
            print("\nCambios aplicados:")
            for change in result["changes"]:
                print(f"  - {change}")

            if result.get("losing_patterns"):
                print("\nPatrones de perdida detectados:")
                for p in result["losing_patterns"]:
                    print(f"  ! {p['reason']}")

            if result.get("sl_tp_analysis"):
                print("\nAnalisis SL/TP:")
                for strat, adj in result["sl_tp_analysis"].items():
                    print(f"  {strat}: {adj['reason']}")

            print("=" * 70 + "\n")

            return True

    return False


def get_ml_strategy_priority(strategy_name, market_context):
    ml = MLAdaptiveSystem()
    return ml.get_strategy_priority(strategy_name, market_context)


def get_ml_status():
    ml = MLAdaptiveSystem()
    return ml.get_ml_report()


if __name__ == "__main__":
    ml = MLAdaptiveSystem()
    report = ml.get_ml_report()
    print(json.dumps(report, indent=2))

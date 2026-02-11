#!/usr/bin/env python3
"""
ml_adaptive_system.py - Sistema de Machine Learning Adaptativo

Sistema de IA que:
1. Aprende de cada trade (reinforcement learning)
2. Ajusta parámetros automáticamente
3. Cambia de estrategia según performance
4. Evoluciona con el tiempo
"""

import json
import os
from datetime import datetime, timedelta
from collections import defaultdict
import statistics


class MLAdaptiveSystem:
    """
    Sistema de ML que aprende y se adapta automáticamente
    """
    
    def __init__(self):
        self.config_file = "bot_config.json"
        self.ml_state_file = "learning_data/ml_state.json"
        self.history_file = "learning_data/trade_history.json"
        self.setup_stats_file = "learning_data/setup_stats.json"
        
        # Configuración de aprendizaje
        self.EXPLORATION_TRADES = 50  # Primeros 50 trades: exploración
        self.LEARNING_TRADES = 200    # Trades 50-200: aprendizaje activo
        # 200+: optimización continua
        
        # Crear directorios
        os.makedirs("learning_data", exist_ok=True)
        
        # Estado
        self.state = self.load_ml_state()
    
    def load_ml_state(self):
        """Carga el estado del sistema ML"""
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
            "current_strategy_priority": {}
        }
    
    def save_ml_state(self):
        """Guarda el estado ML"""
        with open(self.ml_state_file, 'w') as f:
            json.dump(self.state, f, indent=4)
    
    def get_current_mode(self):
        """Determina el modo según experiencia"""
        total = self.get_total_trades()
        
        if total < self.EXPLORATION_TRADES:
            return "EXPLORATION"
        elif total < self.LEARNING_TRADES:
            return "LEARNING"
        else:
            return "OPTIMIZATION"
    
    def _load_trades(self):
        """Carga trades del historial, soportando ambos formatos (lista o dict)"""
        if not os.path.exists(self.history_file):
            return []

        try:
            with open(self.history_file, 'r') as f:
                history = json.load(f)
            # feedback_processor guarda como lista plana [...]
            if isinstance(history, list):
                return history
            # Formato alternativo: {"trades": [...]}
            return history.get("trades", [])
        except:
            return []

    def get_total_trades(self):
        """Cuenta trades totales"""
        return len(self._load_trades())
    
    def analyze_performance(self, last_n=50):
        """
        Análisis profundo de performance
        """
        try:
            trades = self._load_trades()
            if len(trades) < 10:
                return None
            
            recent = trades[-last_n:]
            
            # Métricas básicas
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
            
            # Calcular win rate y profit por estrategia
            strategy_analysis = {}
            for strat, data in strategy_perf.items():
                if data["total"] >= 5:
                    strategy_analysis[strat] = {
                        "win_rate": data["wins"] / data["total"],
                        "avg_profit": statistics.mean(data["profits"]),
                        "total_trades": data["total"],
                        "score": (data["wins"] / data["total"]) * statistics.mean(data["profits"])
                    }
            
            # Performance por contexto de mercado
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
            
            # Análisis de confidence threshold
            confidence_analysis = {}
            for threshold in [30, 35, 40, 45, 50, 55, 60]:
                eligible = [t for t in recent if t.get("confidence", 0) * 100 >= threshold]
                if len(eligible) >= 5:
                    wins_at_threshold = sum(1 for t in eligible if t.get("result") == "WIN")
                    confidence_analysis[threshold] = {
                        "win_rate": wins_at_threshold / len(eligible),
                        "trades": len(eligible)
                    }
            
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
                "by_confidence": confidence_analysis
            }
        
        except Exception as e:
            print(f"Error en análisis: {e}")
            return None
    
    def learn_and_adapt(self):
        """
        Núcleo del sistema ML: aprende y adapta parámetros
        """
        mode = self.get_current_mode()
        total_trades = self.get_total_trades()
        performance = self.analyze_performance()
        
        if not performance:
            return None
        
        # Cargar config actual
        try:
            with open(self.config_file, 'r') as f:
                current_config = json.load(f)
        except:
            current_config = {
                "min_confidence": 35,
                "cooldown": 5,
                "max_daily_trades": 50
            }
        
        new_config = current_config.copy()
        changes = []
        strategy_priorities = {}
        
        # ==========================================
        # MODO EXPLORATION (0-50 trades)
        # ==========================================
        if mode == "EXPLORATION":
            # Mantener parámetros muy permisivos
            new_config["min_confidence"] = 30
            new_config["cooldown"] = 3
            new_config["max_daily_trades"] = 100
            changes.append("EXPLORATION: Recolectando datos con parámetros permisivos")
            
            # En exploración, todas las estrategias tienen prioridad igual
            strategy_priorities = {
                "MEAN_REVERSION": 1.0,
                "TREND_FOLLOWING": 1.0,
                "TREND_PULLBACK": 1.0,
                "BREAKOUT": 1.0,
                "MOMENTUM": 1.0,
                "SCALPING": 1.0,
                "RANGE_TRADING": 1.0,
                "NEWS_FADE": 1.0
            }
        
        # ==========================================
        # MODO LEARNING (50-200 trades)
        # ==========================================
        elif mode == "LEARNING":
            overall = performance["overall"]
            by_strategy = performance["by_strategy"]
            by_confidence = performance["by_confidence"]
            
            # 1. AJUSTAR MIN_CONFIDENCE según análisis
            optimal_conf = 35
            best_wr = 0
            
            for conf, data in by_confidence.items():
                if data["trades"] >= 10 and data["win_rate"] > best_wr:
                    best_wr = data["win_rate"]
                    optimal_conf = conf
            
            if best_wr > 0.52:
                new_config["min_confidence"] = optimal_conf
                changes.append(f"ML: Optimal confidence threshold = {optimal_conf}% (WR: {best_wr:.1%})")
            else:
                # Si no hay threshold óptimo, ajustar según WR general
                if overall["win_rate"] < 0.45:
                    new_config["min_confidence"] = min(current_config["min_confidence"] + 5, 60)
                    changes.append(f"ML: WR bajo ({overall['win_rate']:.1%}) → Aumentando selectividad")
                elif overall["win_rate"] > 0.55:
                    new_config["min_confidence"] = max(current_config["min_confidence"] - 3, 30)
                    changes.append(f"ML: WR alto ({overall['win_rate']:.1%}) → Bajando threshold")
            
            # 2. AJUSTAR COOLDOWN según profit promedio
            if overall["avg_profit"] < -0.5:
                new_config["cooldown"] = min(current_config["cooldown"] + 10, 60)
                changes.append(f"ML: Profit negativo → Aumentando cooldown")
            elif overall["avg_profit"] > 2.0:
                new_config["cooldown"] = max(current_config["cooldown"] - 5, 5)
                changes.append(f"ML: Profit alto → Reduciendo cooldown")
            
            # 3. PRIORIZAR ESTRATEGIAS según performance
            if by_strategy:
                # Calcular scores normalizados
                scores = [(strat, data["score"]) for strat, data in by_strategy.items()]
                max_score = max(s[1] for s in scores) if scores else 1
                
                for strat, score in scores:
                    # Normalizar y convertir a prioridad
                    normalized = score / max_score if max_score > 0 else 1
                    
                    if normalized >= 0.8:
                        priority = 1.5  # Boost fuerte
                    elif normalized >= 0.6:
                        priority = 1.2
                    elif normalized >= 0.4:
                        priority = 1.0
                    elif normalized >= 0.2:
                        priority = 0.8
                    else:
                        priority = 0.6  # Penalizar
                    
                    strategy_priorities[strat] = priority
                
                best_strat = max(by_strategy.items(), key=lambda x: x[1]["score"])
                changes.append(f"ML: Mejor estrategia = {best_strat[0]} (Score: {best_strat[1]['score']:.2f})")
        
        # ==========================================
        # MODO OPTIMIZATION (200+ trades)
        # ==========================================
        elif mode == "OPTIMIZATION":
            overall = performance["overall"]
            by_strategy = performance["by_strategy"]
            by_context = performance["by_context"]
            
            # 1. OPTIMIZACIÓN FINA de confidence threshold
            by_confidence = performance["by_confidence"]
            
            # Buscar el threshold que maximiza profit * win_rate
            best_threshold = 40
            best_metric = 0
            
            for conf, data in by_confidence.items():
                if data["trades"] >= 15:
                    metric = data["win_rate"] * data["trades"]  # Optimizar por volumen y calidad
                    if metric > best_metric:
                        best_metric = metric
                        best_threshold = conf
            
            new_config["min_confidence"] = best_threshold
            changes.append(f"OPTIMIZATION: Threshold óptimo = {best_threshold}%")
            
            # 2. MAPEO de estrategia por contexto
            context_strategy_map = {}
            
            for ctx, ctx_data in by_context.items():
                if ctx_data["total_trades"] >= 5:
                    # Encontrar mejor estrategia para este contexto
                    best_for_context = None
                    best_wr = 0
                    
                    for strat, strat_data in by_strategy.items():
                        if strat_data["total_trades"] >= 3 and strat_data["win_rate"] > best_wr:
                            best_wr = strat_data["win_rate"]
                            best_for_context = strat
                    
                    if best_for_context:
                        context_strategy_map[ctx] = best_for_context
                        changes.append(f"ML Mapping: {ctx} → {best_for_context} (WR: {best_wr:.1%})")
            
            # Guardar mapeo
            self.state["best_strategy_per_context"] = context_strategy_map
            
            # 3. PRIORIDADES avanzadas de estrategias
            if by_strategy:
                for strat, data in by_strategy.items():
                    if data["total_trades"] >= 10:
                        wr = data["win_rate"]
                        profit = data["avg_profit"]
                        
                        # Scoring avanzado
                        quality_score = wr * 2 + (profit / 10)
                        
                        if quality_score >= 1.5:
                            priority = 2.0  # Boost masivo
                        elif quality_score >= 1.2:
                            priority = 1.5
                        elif quality_score >= 0.9:
                            priority = 1.0
                        elif quality_score >= 0.6:
                            priority = 0.7
                        else:
                            priority = 0.4  # Casi desactivar
                        
                        strategy_priorities[strat] = priority
            
            # 4. AJUSTE DINÁMICO de max_daily_trades
            if overall["win_rate"] >= 0.55:
                new_config["max_daily_trades"] = 50
            elif overall["win_rate"] >= 0.50:
                new_config["max_daily_trades"] = 30
            else:
                new_config["max_daily_trades"] = 20
        
        # Guardar evolución
        self.state["parameter_evolution"].append({
            "timestamp": datetime.now().isoformat(),
            "mode": mode,
            "total_trades": total_trades,
            "config": new_config,
            "changes": changes,
            "performance": overall if performance else None
        })
        
        # Mantener últimos 100
        self.state["parameter_evolution"] = self.state["parameter_evolution"][-100:]
        
        # Guardar prioridades de estrategias
        self.state["current_strategy_priority"] = strategy_priorities
        
        # Actualizar estado
        self.state["mode"] = mode
        self.state["total_trades"] = total_trades
        self.state["last_adjustment"] = datetime.now().isoformat()
        
        self.save_ml_state()
        
        return {
            "new_config": new_config,
            "changes": changes,
            "mode": mode,
            "strategy_priorities": strategy_priorities,
            "should_update": new_config != current_config
        }
    
    def get_strategy_priority(self, strategy_name, market_context):
        """
        Obtiene la prioridad de una estrategia según:
        1. Performance histórica
        2. Contexto de mercado actual
        3. Modo de aprendizaje
        """
        # Prioridad base desde ML
        base_priority = self.state.get("current_strategy_priority", {}).get(strategy_name, 1.0)
        
        # Ajuste por contexto
        mode = self.get_current_mode()
        
        if mode == "OPTIMIZATION":
            # En optimización, usar mapeo aprendido
            context_key = f"{market_context.get('trend', 'NONE')}_{market_context.get('volatility', 'NORMAL')}"
            best_for_context = self.state.get("best_strategy_per_context", {}).get(context_key)
            
            if best_for_context == strategy_name:
                return base_priority * 1.5  # Boost adicional por contexto
        
        return base_priority
    
    def should_adjust(self):
        """Determina si es momento de ajustar"""
        total = self.get_total_trades()
        mode = self.get_current_mode()
        
        if mode == "EXPLORATION":
            return False  # No ajustar en exploración
        
        elif mode == "LEARNING":
            # Ajustar cada 10 trades
            return total > 0 and total % 10 == 0
        
        else:  # OPTIMIZATION
            # Ajustar cada 30 trades
            return total > 0 and total % 30 == 0
    
    def get_ml_report(self):
        """Genera reporte completo del sistema ML"""
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
            "recent_adjustments": self.state.get("parameter_evolution", [])[-5:]
        }
        
        # Progreso
        if mode == "EXPLORATION":
            report["progress"] = {
                "phase": "Recolección de datos",
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
                "phase": "Optimización continua",
                "trades": total
            }
        
        return report


# ==========================================
# API FUNCTIONS
# ==========================================

def ml_auto_adjust():
    """Función principal: ajusta automáticamente si es necesario"""
    ml = MLAdaptiveSystem()
    
    if ml.should_adjust():
        result = ml.learn_and_adapt()
        
        if result and result["should_update"]:
            # Actualizar configuración
            with open("bot_config.json", 'w') as f:
                json.dump(result["new_config"], f, indent=4)
            
            print("\n" + "=" * 70)
            print("🧠 SISTEMA ML - AJUSTE AUTOMÁTICO")
            print("=" * 70)
            print(f"Modo: {result['mode']}")
            print(f"Total trades: {ml.get_total_trades()}")
            print("\nCambios aplicados:")
            for change in result["changes"]:
                print(f"  • {change}")
            print("=" * 70 + "\n")
            
            return True
    
    return False


def get_ml_strategy_priority(strategy_name, market_context):
    """Obtiene prioridad ML de una estrategia"""
    ml = MLAdaptiveSystem()
    return ml.get_strategy_priority(strategy_name, market_context)


def get_ml_status():
    """Obtiene estado actual del sistema ML"""
    ml = MLAdaptiveSystem()
    return ml.get_ml_report()


if __name__ == "__main__":
    ml = MLAdaptiveSystem()
    report = ml.get_ml_report()
    print(json.dumps(report, indent=2))

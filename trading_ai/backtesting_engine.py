# backtesting/backtesting_engine.py

"""
Sistema de Backtesting para Trading AI Bot

Permite simular el bot sobre datos históricos sin arriesgar dinero real.
"""

import json
import os
from datetime import datetime, timedelta
from collections import defaultdict
import sys

import json
import os
from datetime import datetime, timedelta
from collections import defaultdict
import sys

# Importar módulos del bot (opcionales)
DECISION_ENGINE_AVAILABLE = False
try:
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from decision_engine.context_analyzer import analyze_market_context
    from decision_engine.setup_selector import select_setup
    from decision_engine.signal_router import evaluate_signal
    DECISION_ENGINE_AVAILABLE = True
except Exception as e:
    print(f"⚠️ Decision engine no disponible para backtesting: {e}")
    print("   Backtesting funcionará con lógica simplificada")


class BacktestEngine:
    """Motor de backtesting"""
    
    def __init__(self, historical_data, config=None):
        """
        Args:
            historical_data: Lista de datos de mercado históricos
            config: Configuración del backtest (opcional)
        """
        self.historical_data = historical_data
        self.config = config or self.get_default_config()
        
        # Resultados del backtest
        self.trades = []
        self.equity_curve = [0]
        self.balance = self.config.get("initial_balance", 10000)
        self.initial_balance = self.balance
        
        # Stats
        self.stats = {
            "total_trades": 0,
            "wins": 0,
            "losses": 0,
            "total_pips": 0.0,
            "max_drawdown": 0.0,
            "sharpe_ratio": 0.0
        }
    
    def get_default_config(self):
        """Configuración por defecto"""
        return {
            "initial_balance": 10000,
            "lot_size": 0.01,
            "pip_value": 10,  # Para EURUSD 0.01 lots
            "max_trades_per_day": 20,
            "min_confidence": 0.75,
            "commission_per_trade": 0.0  # Comisión por trade si aplica
        }
    
    def run_backtest(self, progress_callback=None):
        """
        Ejecutar backtest completo
        
        Args:
            progress_callback: Función para reportar progreso (opcional)
        
        Returns:
            dict: Resultados del backtest
        """
        print(f"🧪 Iniciando backtest con {len(self.historical_data)} puntos de datos...")
        
        total_points = len(self.historical_data)
        trades_today = 0
        current_date = None
        
        for i, market_data in enumerate(self.historical_data):
            # Reportar progreso
            if progress_callback and i % 100 == 0:
                progress = (i / total_points) * 100
                progress_callback(progress)
            
            # Resetear contador de trades diarios
            date = market_data.get("timestamp", "")[:10]
            if date != current_date:
                current_date = date
                trades_today = 0
            
            # Verificar límite diario
            if trades_today >= self.config["max_trades_per_day"]:
                continue
            
            # Analizar mercado
            try:
                if not DECISION_ENGINE_AVAILABLE:
                    # Fallback: Usar lógica simplificada sin módulos del bot
                    # Generar señal aleatoria para testing
                    import random
                    if random.random() > 0.7:  # 30% de señales
                        signal = {
                            "action": random.choice(["BUY", "SELL"]),
                            "confidence": random.uniform(0.7, 0.95),
                            "sl_pips": 15,
                            "tp_pips": 25,
                            "setup_name": "SIMPLIFIED_BACKTEST"
                        }
                        self.simulate_trade(signal, market_data, i)
                        trades_today += 1
                    continue
                
                # Usar módulos del bot si están disponibles
                context = analyze_market_context(market_data)
                
                # Seleccionar setup
                setup = select_setup(context)
                
                if not setup:
                    continue
                
                # Evaluar señal
                signal = evaluate_signal(setup["name"], context, market_data)
                
                if not signal or signal.get("action") == "NONE":
                    continue
                
                # Verificar confianza
                confidence = signal.get("confidence", 0)
                if confidence < self.config["min_confidence"]:
                    continue
                
                # Simular trade
                self.simulate_trade(signal, market_data, i)
                trades_today += 1
                
            except Exception as e:
                # Ignorar errores en datos individuales
                continue
        
        # Calcular estadísticas finales
        self.calculate_final_stats()
        
        print(f"✅ Backtest completado: {self.stats['total_trades']} trades simulados")
        
        return self.get_results()
    
    def simulate_trade(self, signal, entry_data, index):
        """
        Simular un trade individual
        
        Args:
            signal: Señal generada por el bot
            entry_data: Datos de mercado en el momento de entrada
            index: Índice en historical_data
        """
        action = signal.get("action")
        entry_price = entry_data.get("bid" if action == "SELL" else "ask", 0)
        sl_pips = signal.get("sl_pips", 15)
        tp_pips = signal.get("tp_pips", 25)
        
        if entry_price == 0:
            return
        
        # Calcular SL y TP
        pip_value_price = 0.0001  # Para EURUSD
        
        if action == "BUY":
            sl_price = entry_price - (sl_pips * pip_value_price)
            tp_price = entry_price + (tp_pips * pip_value_price)
        else:  # SELL
            sl_price = entry_price + (sl_pips * pip_value_price)
            tp_price = entry_price - (tp_pips * pip_value_price)
        
        # Buscar cierre del trade en datos futuros
        exit_index = index + 1
        exit_reason = "TIMEOUT"
        exit_price = entry_price
        pips = 0
        
        # Buscar hasta 100 puntos adelante o fin de datos
        max_look_ahead = min(index + 100, len(self.historical_data))
        
        for j in range(index + 1, max_look_ahead):
            candle = self.historical_data[j]
            high = candle.get("high", 0)
            low = candle.get("low", 0)
            
            if action == "BUY":
                # Verificar si tocó TP
                if high >= tp_price:
                    exit_price = tp_price
                    exit_reason = "TP"
                    exit_index = j
                    break
                # Verificar si tocó SL
                if low <= sl_price:
                    exit_price = sl_price
                    exit_reason = "SL"
                    exit_index = j
                    break
            else:  # SELL
                # Verificar si tocó TP
                if low <= tp_price:
                    exit_price = tp_price
                    exit_reason = "TP"
                    exit_index = j
                    break
                # Verificar si tocó SL
                if high >= sl_price:
                    exit_price = sl_price
                    exit_reason = "SL"
                    exit_index = j
                    break
        
        # Si no se cerró, cerrar al final del lookback
        if exit_reason == "TIMEOUT":
            exit_data = self.historical_data[max_look_ahead - 1]
            exit_price = exit_data.get("bid" if action == "BUY" else "ask", entry_price)
        
        # Calcular resultado
        if action == "BUY":
            pips = (exit_price - entry_price) / pip_value_price
        else:
            pips = (entry_price - exit_price) / pip_value_price
        
        profit = pips * self.config["pip_value"] * self.config["lot_size"]
        profit -= self.config["commission_per_trade"]
        
        # Actualizar balance
        self.balance += profit
        self.equity_curve.append(self.balance - self.initial_balance)
        
        # Guardar trade
        trade = {
            "entry_time": entry_data.get("timestamp", ""),
            "exit_time": self.historical_data[exit_index].get("timestamp", "") if exit_index < len(self.historical_data) else "",
            "action": action,
            "setup": signal.get("setup_name", "Unknown"),
            "entry_price": entry_price,
            "exit_price": exit_price,
            "sl_price": sl_price,
            "tp_price": tp_price,
            "pips": round(pips, 2),
            "profit": round(profit, 2),
            "exit_reason": exit_reason,
            "confidence": signal.get("confidence", 0)
        }
        
        self.trades.append(trade)
        
        # Actualizar stats
        self.stats["total_trades"] += 1
        self.stats["total_pips"] += pips
        
        if pips > 0:
            self.stats["wins"] += 1
        else:
            self.stats["losses"] += 1
    
    def calculate_final_stats(self):
        """Calcular estadísticas finales del backtest"""
        if self.stats["total_trades"] == 0:
            return
        
        # Win rate
        self.stats["win_rate"] = (self.stats["wins"] / self.stats["total_trades"]) * 100
        
        # Average win/loss
        wins = [t["pips"] for t in self.trades if t["pips"] > 0]
        losses = [abs(t["pips"]) for t in self.trades if t["pips"] < 0]
        
        self.stats["avg_win"] = sum(wins) / len(wins) if wins else 0
        self.stats["avg_loss"] = sum(losses) / len(losses) if losses else 0
        
        # Profit factor
        gross_profit = sum(wins) if wins else 0
        gross_loss = sum(losses) if losses else 1
        self.stats["profit_factor"] = gross_profit / gross_loss if gross_loss > 0 else 0
        
        # Max drawdown
        peak = 0
        max_dd = 0
        for equity in self.equity_curve:
            if equity > peak:
                peak = equity
            dd = peak - equity
            if dd > max_dd:
                max_dd = dd
        
        self.stats["max_drawdown"] = max_dd
        self.stats["max_drawdown_pct"] = (max_dd / self.initial_balance * 100) if self.initial_balance > 0 else 0
        
        # Sharpe ratio (simplificado)
        if len(self.equity_curve) > 1:
            returns = []
            for i in range(1, len(self.equity_curve)):
                if self.equity_curve[i-1] != 0:
                    ret = (self.equity_curve[i] - self.equity_curve[i-1]) / abs(self.equity_curve[i-1])
                    returns.append(ret)
            
            if returns:
                import statistics
                avg_return = statistics.mean(returns)
                std_return = statistics.stdev(returns) if len(returns) > 1 else 0
                self.stats["sharpe_ratio"] = (avg_return / std_return) if std_return > 0 else 0
        
        # Profit total
        self.stats["total_profit"] = self.balance - self.initial_balance
        self.stats["return_pct"] = (self.stats["total_profit"] / self.initial_balance) * 100
        
        # Mejor/peor trade
        if self.trades:
            self.stats["best_trade"] = max(t["pips"] for t in self.trades)
            self.stats["worst_trade"] = min(t["pips"] for t in self.trades)
    
    def get_results(self):
        """Obtener resultados del backtest"""
        return {
            "stats": self.stats,
            "trades": self.trades,
            "equity_curve": self.equity_curve,
            "config": self.config
        }
    
    def export_results(self, filepath):
        """Exportar resultados a archivo JSON"""
        results = self.get_results()
        
        with open(filepath, "w") as f:
            json.dump(results, f, indent=4)
        
        print(f"✅ Resultados exportados a {filepath}")


def load_historical_data(filepath):
    """
    Cargar datos históricos desde archivo
    
    Formatos soportados:
    - JSON: Array de objetos con datos de velas
    - CSV: Timestamp, Open, High, Low, Close, Volume
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Archivo no encontrado: {filepath}")
    
    # Detectar formato
    ext = filepath.split(".")[-1].lower()
    
    if ext == "json":
        with open(filepath, "r") as f:
            data = json.load(f)
        return data
    
    elif ext == "csv":
        import csv
        data = []
        
        with open(filepath, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Convertir CSV a formato del bot
                candle = {
                    "timestamp": row.get("timestamp") or row.get("time") or row.get("date"),
                    "open": float(row.get("open", 0)),
                    "high": float(row.get("high", 0)),
                    "low": float(row.get("low", 0)),
                    "close": float(row.get("close", 0)),
                    "volume": int(row.get("volume", 0)),
                    # Campos requeridos por el bot
                    "bid": float(row.get("close", 0)),  # Aproximación
                    "ask": float(row.get("close", 0)) + 0.0002,  # Spread aprox
                    "spread": 2.0,
                    "indicators": generate_indicators_from_candles(data + [row])
                }
                data.append(candle)
        
        return data
    
    else:
        raise ValueError(f"Formato no soportado: {ext}")


def generate_indicators_from_candles(candles):
    """
    Generar indicadores técnicos desde velas
    (Simplificado - en producción usar TA-Lib o pandas-ta)
    """
    if len(candles) < 20:
        return {}
    
    closes = [float(c.get("close", 0)) for c in candles[-20:]]
    highs = [float(c.get("high", 0)) for c in candles[-20:]]
    lows = [float(c.get("low", 0)) for c in candles[-20:]]
    
    # RSI simplificado
    gains = []
    losses = []
    for i in range(1, len(closes)):
        change = closes[i] - closes[i-1]
        if change > 0:
            gains.append(change)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(change))
    
    avg_gain = sum(gains[-14:]) / 14 if len(gains) >= 14 else 0
    avg_loss = sum(losses[-14:]) / 14 if len(losses) >= 14 else 0
    
    if avg_loss == 0:
        rsi = 100
    else:
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
    
    # EMAs simplificadas
    ema_20 = sum(closes[-20:]) / 20
    ema_50 = sum(closes) / len(closes)
    
    return {
        "rsi": rsi,
        "ema": {
            "fast": ema_20,
            "slow": ema_50,
            "long": ema_50
        },
        "macd": {
            "main": 0,
            "signal": 0,
            "histogram": 0
        },
        "bollinger": {
            "upper": max(closes[-20:]),
            "middle": sum(closes[-20:]) / 20,
            "lower": min(closes[-20:])
        },
        "atr": (max(highs[-14:]) - min(lows[-14:])) if len(highs) >= 14 else 0
    }


# Testing
if __name__ == "__main__":
    print("🧪 Testing Backtesting Engine...")
    
    # Crear datos dummy para testing
    dummy_data = []
    base_price = 1.1800
    
    for i in range(1000):
        # Simular precio con volatilidad
        import random
        change = random.uniform(-0.0010, 0.0010)
        base_price += change
        
        candle = {
            "timestamp": f"2024-01-01 {i//60:02d}:{i%60:02d}:00",
            "open": base_price,
            "high": base_price + random.uniform(0, 0.0005),
            "low": base_price - random.uniform(0, 0.0005),
            "close": base_price,
            "bid": base_price,
            "ask": base_price + 0.0002,
            "spread": 2.0,
            "volume": random.randint(100, 1000),
            "indicators": {
                "rsi": random.uniform(30, 70),
                "ema": {"fast": base_price, "slow": base_price, "long": base_price},
                "macd": {"main": 0, "signal": 0, "histogram": 0},
                "bollinger": {"upper": base_price + 0.001, "middle": base_price, "lower": base_price - 0.001},
                "atr": 0.0005
            }
        }
        dummy_data.append(candle)
    
    # Ejecutar backtest
    engine = BacktestEngine(dummy_data)
    results = engine.run_backtest()
    
    print("\n📊 RESULTADOS DEL BACKTEST:")
    print(f"Total Trades: {results['stats']['total_trades']}")
    print(f"Win Rate: {results['stats'].get('win_rate', 0):.2f}%")
    print(f"Total Profit: ${results['stats'].get('total_profit', 0):.2f}")
    print(f"Max Drawdown: ${results['stats'].get('max_drawdown', 0):.2f}")
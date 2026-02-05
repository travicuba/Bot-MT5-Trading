# decision_engine/signal_router.py

import json
import os
from datetime import datetime

# Importar evaluadores mejorados
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# NOTA: Estos imports asumen que los archivos mejorados reemplazarán a los originales
# Si no, ajustar los nombres de los módulos
try:
    from evaluator.trend_following_eval import evaluate as eval_trend_following
except:
    print("⚠️ Usando evaluador trend_following por defecto")
    eval_trend_following = None

try:
    from evaluator.mean_reversion_eval import evaluate as eval_mean_reversion
except:
    print("⚠️ Usando evaluador mean_reversion por defecto")
    eval_mean_reversion = None


# ⚠️ Ruta ABSOLUTA al directorio FILES de MT5 (Wine)
SIGNAL_PATH = "/home/travieso/.wine/drive_c/Program Files/MetaTrader 5/MQL5/Files/signals/signal.json"


def evaluate_signal(setup_name, context, market_data):
    """
    VERSIÓN MEJORADA
    Evalúa señal según el setup seleccionado usando evaluadores especializados
    """
    
    signal = None
    
    # ========== ROUTING A EVALUADORES ESPECÍFICOS ==========
    
    if setup_name == "TREND_FOLLOWING":
        if eval_trend_following:
            signal = eval_trend_following(context, market_data)
        else:
            signal = _evaluate_trend_following_fallback(context, market_data)
    
    elif setup_name == "MEAN_REVERSION":
        if eval_mean_reversion:
            signal = eval_mean_reversion(context, market_data)
        else:
            signal = _evaluate_mean_reversion_fallback(context, market_data)
    
    elif setup_name == "TREND_PULLBACK":
        signal = _evaluate_trend_pullback(context, market_data)
    
    else:
        print(f"⚠️ Setup desconocido: {setup_name}")
        return _create_no_signal()
    
    # ========== VALIDACIÓN DE SEÑAL ==========
    
    if not signal or signal.get("signal") is None:
        print(f"❌ Evaluador {setup_name} no generó señal válida")
        return _create_no_signal()
    
    # Verificar confianza mínima
    confidence = signal.get("confidence", 0)
    if confidence < 0.65:
        print(f"⚠️ Confianza muy baja ({confidence:.2f}), no se genera señal")
        return _create_no_signal()
    
    # ========== CONSTRUCCIÓN DE SEÑAL FINAL ==========
    
    action = signal["signal"]  # BUY o SELL
    sl_pips = signal.get("sl_pips", 15)
    tp_pips = signal.get("tp_pips", 25)
    
    # Generar ID único
    now = datetime.utcnow()
    signal_id = f"{now.strftime('%Y%m%d_%H%M%S')}_{action}_{setup_name}"
    
    final_signal = {
        "signal_id": signal_id,
        "action": action,
        "confidence": confidence,
        "sl_pips": sl_pips,
        "tp_pips": tp_pips,
        "symbol": market_data.get("symbol", "EURUSD"),
        "timeframe": signal.get("timeframe", "M5"),
        "timestamp": now.isoformat(),
        "setup_name": setup_name,
        "reason": signal.get("reason", "")
    }
    
    # ========== ESCRIBIR ARCHIVO ==========
    
    if not _write_signal_file(final_signal):
        return None
    
    # ========== LOGS ==========
    
    print("✅ SEÑAL GENERADA:")
    print(f"   Setup: {setup_name}")
    print(f"   Action: {action}")
    print(f"   Confidence: {confidence:.2%}")
    print(f"   SL/TP: {sl_pips}/{tp_pips} pips")
    print(f"   Reason: {signal.get('reason', 'N/A')}")
    
    return final_signal


def _write_signal_file(signal):
    """Escribe el archivo signal.json de forma segura"""
    
    try:
        # Garantizar directorio
        os.makedirs(os.path.dirname(SIGNAL_PATH), exist_ok=True)
        
        # Escritura atómica usando archivo temporal
        temp_path = SIGNAL_PATH + ".tmp"
        
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(signal, f, indent=4)
        
        os.replace(temp_path, SIGNAL_PATH)
        
        print("📍 signal.json escrito en:", SIGNAL_PATH)
        return True
        
    except Exception as e:
        print("❌ ERROR escribiendo signal.json:", e)
        return False


def _create_no_signal():
    """Crea una señal NONE cuando no hay operación"""
    return {
        "action": "NONE",
        "confidence": 0.0,
        "sl_pips": 0,
        "tp_pips": 0
    }


# ========== EVALUADORES FALLBACK (si no hay archivos mejorados) ==========

def _evaluate_trend_following_fallback(context, market_data):
    """Evaluador básico de trend following como fallback"""
    
    trend = context.get("trend", "NONE")
    
    if trend in ["UP", "STRONG_UP"]:
        return {
            "signal": "BUY",
            "confidence": 0.75,
            "timeframe": "M5",
            "sl_pips": 15,
            "tp_pips": 25,
            "reason": "Trend following BUY (fallback)"
        }
    
    if trend in ["DOWN", "STRONG_DOWN"]:
        return {
            "signal": "SELL",
            "confidence": 0.75,
            "timeframe": "M5",
            "sl_pips": 15,
            "tp_pips": 25,
            "reason": "Trend following SELL (fallback)"
        }
    
    return {"signal": None, "confidence": 0.0}


def _evaluate_mean_reversion_fallback(context, market_data):
    """Evaluador básico de mean reversion como fallback"""
    
    rsi_state = context.get("rsi_state", "NEUTRAL")
    bb_position = context.get("bb_position", "MIDDLE")
    
    if rsi_state == "OVERSOLD" and bb_position == "NEAR_LOWER":
        return {
            "signal": "BUY",
            "confidence": 0.70,
            "timeframe": "M5",
            "sl_pips": 12,
            "tp_pips": 18,
            "reason": "Mean reversion BUY (fallback)"
        }
    
    if rsi_state == "OVERBOUGHT" and bb_position == "NEAR_UPPER":
        return {
            "signal": "SELL",
            "confidence": 0.70,
            "timeframe": "M5",
            "sl_pips": 12,
            "tp_pips": 18,
            "reason": "Mean reversion SELL (fallback)"
        }
    
    return {"signal": None, "confidence": 0.0}


def _evaluate_trend_pullback(context, market_data):
    """
    Evaluador para Trend Pullback
    Opera cuando hay tendencia pero esperamos un pullback para mejor entrada
    """
    
    trend = context.get("trend", "NONE")
    rsi_state = context.get("rsi_state", "NEUTRAL")
    bb_position = context.get("bb_position", "MIDDLE")
    macd_state = context.get("macd_state", "NEUTRAL")
    
    # Necesitamos tendencia clara
    if trend not in ["STRONG_UP", "UP", "STRONG_DOWN", "DOWN"]:
        return {"signal": None, "confidence": 0.0}
    
    # Pullback alcista: tendencia UP pero precio ha retrocedido
    if trend in ["STRONG_UP", "UP"]:
        # Buscar pullback (RSI bajo pero no oversold, precio en mitad inferior de BB)
        if rsi_state in ["WEAK", "NEUTRAL"] and bb_position in ["LOWER_HALF", "MIDDLE"]:
            # Verificar que MACD siga alcista (tendencia intacta)
            if macd_state in ["BULLISH", "STRONG_BULLISH"]:
                return {
                    "signal": "BUY",
                    "confidence": 0.80,
                    "timeframe": "M5",
                    "sl_pips": 18,
                    "tp_pips": 30,
                    "reason": "Trend pullback BUY - Entrada en retroceso de tendencia alcista"
                }
    
    # Pullback bajista: tendencia DOWN pero precio ha rebotado
    if trend in ["STRONG_DOWN", "DOWN"]:
        # Buscar pullback (RSI alto pero no overbought, precio en mitad superior de BB)
        if rsi_state in ["STRONG", "NEUTRAL"] and bb_position in ["UPPER_HALF", "MIDDLE"]:
            # Verificar que MACD siga bajista
            if macd_state in ["BEARISH", "STRONG_BEARISH"]:
                return {
                    "signal": "SELL",
                    "confidence": 0.80,
                    "timeframe": "M5",
                    "sl_pips": 18,
                    "tp_pips": 30,
                    "reason": "Trend pullback SELL - Entrada en rebote de tendencia bajista"
                }
    
    return {"signal": None, "confidence": 0.0, "reason": "Sin condiciones de pullback"}

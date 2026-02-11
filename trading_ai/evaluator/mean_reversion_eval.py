# evaluator/mean_reversion_eval.py
# VERSIÓN ULTRA PERMISIVA - Para testing

"""
Evaluador de Mean Reversion MUY PERMISIVO
Opera en condiciones más amplias para generar señales
"""

def evaluate(context: dict, market_data: dict):
    """
    Evalúa señales de Mean Reversion con criterios MUY permisivos
    """
    
    result = {
        "signal": None,
        "confidence": 0.0,
        "timeframe": market_data.get("timeframe", "M5"),
        "sl_pips": 15,
        "tp_pips": 25,
        "reason": ""
    }
    
    # VALIDACIONES BÁSICAS
    if not context.get("trade_allowed", False):
        result["reason"] = "Trading bloqueado"
        return result
    
    trend = context.get("trend", "NONE")
    rsi_state = context.get("rsi_state", "NEUTRAL")
    bb_position = context.get("bb_position", "MIDDLE")
    market_regime = context.get("market_regime", "UNDEFINED")
    
    # NO bloquear por tendencia fuerte
    # Mean reversion funciona en cualquier mercado
    
    # ========================================
    # SEÑALES ALCISTAS (BUY)
    # ========================================
    
    # Condición 1: RSI OVERSOLD clásico
    if rsi_state == "OVERSOLD":
        result["signal"] = "BUY"
        result["confidence"] = 0.75
        result["reason"] = "Mean Reversion BUY - RSI oversold"
        return result
    
    # Condición 2: RSI WEAK (entre 30-40)
    if rsi_state == "WEAK":
        result["signal"] = "BUY"
        result["confidence"] = 0.60
        result["reason"] = "Mean Reversion BUY - RSI débil"
        return result
    
    # Condición 3: Precio en banda inferior
    if bb_position in ["NEAR_LOWER", "LOWER_HALF"]:
        result["signal"] = "BUY"
        result["confidence"] = 0.55
        result["reason"] = "Mean Reversion BUY - Precio bajo en BB"
        return result
    
    # Condición 4: SIDEWAYS + RSI neutral bajo (50-58)
    if trend == "SIDEWAYS" and rsi_state == "NEUTRAL":
        # Obtener RSI real del mercado
        rsi_value = market_data.get("indicators", {}).get("rsi", 50)
        
        if rsi_value < 52:  # RSI bajo en rango neutral
            result["signal"] = "BUY"
            result["confidence"] = 0.45
            result["reason"] = f"Mean Reversion BUY - SIDEWAYS con RSI={rsi_value:.1f}"
            return result
    
    # ========================================
    # SEÑALES BAJISTAS (SELL)
    # ========================================
    
    # Condición 1: RSI OVERBOUGHT clásico
    if rsi_state == "OVERBOUGHT":
        result["signal"] = "SELL"
        result["confidence"] = 0.75
        result["reason"] = "Mean Reversion SELL - RSI overbought"
        return result
    
    # Condición 2: RSI STRONG (entre 60-70)
    if rsi_state == "STRONG":
        result["signal"] = "SELL"
        result["confidence"] = 0.60
        result["reason"] = "Mean Reversion SELL - RSI fuerte"
        return result
    
    # Condición 3: Precio en banda superior
    if bb_position in ["NEAR_UPPER", "UPPER_HALF"]:
        result["signal"] = "SELL"
        result["confidence"] = 0.55
        result["reason"] = "Mean Reversion SELL - Precio alto en BB"
        return result
    
    # Condición 4: SIDEWAYS + RSI neutral alto (58-62)
    if trend == "SIDEWAYS" and rsi_state == "NEUTRAL":
        rsi_value = market_data.get("indicators", {}).get("rsi", 50)
        
        if rsi_value > 56:  # RSI alto en rango neutral
            result["signal"] = "SELL"
            result["confidence"] = 0.45
            result["reason"] = f"Mean Reversion SELL - SIDEWAYS con RSI={rsi_value:.1f}"
            return result
    
    # ========================================
    # SEÑALES EN MERCADOS QUIET
    # ========================================
    
    if market_regime == "QUIET":
        rsi_value = market_data.get("indicators", {}).get("rsi", 50)
        
        # En mercados quiet, cualquier desviación pequeña es oportunidad
        if rsi_value < 48:
            result["signal"] = "BUY"
            result["confidence"] = 0.40
            result["reason"] = f"Mean Reversion BUY - QUIET market RSI={rsi_value:.1f}"
            return result
        
        if rsi_value > 52:
            result["signal"] = "SELL"
            result["confidence"] = 0.40
            result["reason"] = f"Mean Reversion SELL - QUIET market RSI={rsi_value:.1f}"
            return result
    
    # ========================================
    # SEÑAL POR DEFECTO EN SIDEWAYS
    # ========================================
    
    # Si estamos en SIDEWAYS y no hay señal clara, generar algo
    if trend == "SIDEWAYS":
        rsi_value = market_data.get("indicators", {}).get("rsi", 50)
        
        # Preferir SELL si RSI > 50, BUY si RSI < 50
        if rsi_value >= 50:
            result["signal"] = "SELL"
            result["confidence"] = 0.35
            result["reason"] = f"Mean Reversion SELL - Default SIDEWAYS RSI={rsi_value:.1f}"
        else:
            result["signal"] = "BUY"
            result["confidence"] = 0.35
            result["reason"] = f"Mean Reversion BUY - Default SIDEWAYS RSI={rsi_value:.1f}"
        
        return result
    
    # Sin señal
    result["reason"] = f"Sin condiciones de mean reversion (RSI={rsi_state}, BB={bb_position})"
    return result

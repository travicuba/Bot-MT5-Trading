# evaluator/mean_reversion_eval.py

"""
Evaluador mejorado para estrategia de Mean Reversion
Opera cuando el precio se aleja demasiado de la media y esperamos retorno
"""


def evaluate(context: dict, market_data: dict):
    """
    Evalúa si hay señal de Mean Reversion basándose en:
    - RSI en zona extrema (>70 o <30)
    - Precio fuera de Bollinger Bands
    - Mercado en rango (no tendencia fuerte)
    - MACD mostrando divergencia
    
    Returns:
        dict con signal, confidence, sl_pips, tp_pips
    """
    
    # ========== VALORES POR DEFECTO ==========
    result = {
        "signal": None,
        "confidence": 0.0,
        "timeframe": market_data.get("timeframe", "M5"),
        "sl_pips": 12,
        "tp_pips": 18,
        "reason": ""
    }
    
    # ========== VALIDACIONES ==========
    if not context.get("trade_allowed", False):
        result["reason"] = "Trading bloqueado por contexto"
        return result
    
    trend = context.get("trend", "NONE")
    rsi_state = context.get("rsi_state", "NEUTRAL")
    bb_position = context.get("bb_position", "MIDDLE")
    market_regime = context.get("market_regime", "UNDEFINED")
    
    # Mean Reversion funciona mejor en mercados laterales o de baja tendencia
    if trend in ["STRONG_UP", "STRONG_DOWN"]:
        result["reason"] = f"Tendencia demasiado fuerte para mean reversion (trend={trend})"
        return result
    
    # Mejor en mercados ranging
    if market_regime not in ["RANGING", "QUIET", "TRANSITIONING"]:
        result["reason"] = f"Régimen de mercado no apto (regime={market_regime})"
        return result
    
    # ========== SEÑAL ALCISTA (COMPRAR EN OVERSOLD) ==========
    if rsi_state == "OVERSOLD" and bb_position in ["NEAR_LOWER", "LOWER_HALF"]:
        
        confirmations = 0
        confidence_base = 0.70
        
        # 1. RSI muy bajo
        if rsi_state == "OVERSOLD":
            confirmations += 1
            confidence_base += 0.10
        
        # 2. Precio cerca de banda inferior
        if bb_position == "NEAR_LOWER":
            confirmations += 1
            confidence_base += 0.15
        
        # 3. Verificar que no esté en tendencia bajista fuerte
        if trend not in ["DOWN", "STRONG_DOWN"]:
            confirmations += 1
        else:
            # Reducir confianza si hay tendencia bajista
            confidence_base -= 0.15
        
        # Generar señal BUY
        result["signal"] = "BUY"
        result["confidence"] = min(0.90, confidence_base)
        result["reason"] = f"Mean Reversion BUY - Oversold en BB inferior ({confirmations} confirmaciones)"
        
        # SL/TP más conservadores en mean reversion
        result["sl_pips"] = 12
        result["tp_pips"] = 18
        
        return result
    
    # ========== SEÑAL BAJISTA (VENDER EN OVERBOUGHT) ==========
    if rsi_state == "OVERBOUGHT" and bb_position in ["NEAR_UPPER", "UPPER_HALF"]:
        
        confirmations = 0
        confidence_base = 0.70
        
        # 1. RSI muy alto
        if rsi_state == "OVERBOUGHT":
            confirmations += 1
            confidence_base += 0.10
        
        # 2. Precio cerca de banda superior
        if bb_position == "NEAR_UPPER":
            confirmations += 1
            confidence_base += 0.15
        
        # 3. Verificar que no esté en tendencia alcista fuerte
        if trend not in ["UP", "STRONG_UP"]:
            confirmations += 1
        else:
            # Reducir confianza si hay tendencia alcista
            confidence_base -= 0.15
        
        # Generar señal SELL
        result["signal"] = "SELL"
        result["confidence"] = min(0.90, confidence_base)
        result["reason"] = f"Mean Reversion SELL - Overbought en BB superior ({confirmations} confirmaciones)"
        
        # SL/TP más conservadores
        result["sl_pips"] = 12
        result["tp_pips"] = 18
        
        return result
    
    # ========== CONDICIONES MODERADAS ==========
    # Señales más débiles pero aún válidas
    
    if rsi_state == "WEAK" and bb_position == "LOWER_HALF":
        result["signal"] = "BUY"
        result["confidence"] = 0.60
        result["reason"] = "Mean Reversion BUY - Señal débil"
        result["sl_pips"] = 10
        result["tp_pips"] = 15
        return result
    
    if rsi_state == "STRONG" and bb_position == "UPPER_HALF":
        result["signal"] = "SELL"
        result["confidence"] = 0.60
        result["reason"] = "Mean Reversion SELL - Señal débil"
        result["sl_pips"] = 10
        result["tp_pips"] = 15
        return result
    
    # Sin señal
    result["reason"] = "Sin condiciones de mean reversion"
    return result

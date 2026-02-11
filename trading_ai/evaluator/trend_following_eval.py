# evaluator/trend_following_eval.py

"""
Evaluador mejorado para estrategia de Trend Following
Usa datos completos de market_data.json
"""


def evaluate(context: dict, market_data: dict):
    """
    Evalúa si hay señal de Trend Following basándose en:
    - Tendencia confirmada (EMA alignment)
    - RSI no en zona extrema
    - MACD confirmando la dirección
    - Bollinger Bands para timing
    
    Returns:
        dict con signal, confidence, sl_pips, tp_pips
    """
    
    # ========== VALORES POR DEFECTO ==========
    result = {
        "signal": None,
        "confidence": 0.0,
        "timeframe": market_data.get("timeframe", "M5"),
        "sl_pips": 15,
        "tp_pips": 25,
        "reason": ""
    }
    
    # ========== VALIDACIONES ==========
    if not context.get("trade_allowed", False):
        result["reason"] = "Trading bloqueado por contexto"
        return result
    
    trend = context.get("trend", "NONE")
    confidence = context.get("confidence", 0)
    rsi_state = context.get("rsi_state", "NEUTRAL")
    macd_state = context.get("macd_state", "NEUTRAL")
    bb_position = context.get("bb_position", "MIDDLE")
    
    # Solo operar en tendencias claras
    if trend not in ["STRONG_UP", "UP", "STRONG_DOWN", "DOWN"]:
        result["reason"] = f"Sin tendencia clara (trend={trend})"
        return result
    
    # ========== SEÑAL ALCISTA ==========
    if trend in ["STRONG_UP", "UP"]:

        confirmations = 0
        confidence_base = 0.50

        # 1. MACD confirma dirección (no es hard-reject, ajusta confianza)
        if macd_state in ["STRONG_BULLISH"]:
            confirmations += 1
            confidence_base += 0.20
        elif macd_state in ["BULLISH"]:
            confirmations += 1
            confidence_base += 0.15
        elif macd_state == "NEUTRAL":
            confidence_base += 0.05
        else:
            # MACD bajista en tendencia alcista: señal débil pero no rechazar
            confidence_base -= 0.10

        # 2. RSI no debe estar sobrecomprado
        if rsi_state == "OVERBOUGHT":
            result["reason"] = f"RSI sobrecomprado, esperando pullback (rsi_state={rsi_state})"
            return result

        if rsi_state in ["STRONG", "NEUTRAL"]:
            confirmations += 1
            confidence_base += 0.05

        # 3. Mejor entrada en pullback (cerca de media de Bollinger)
        if bb_position in ["MIDDLE", "LOWER_HALF"]:
            confirmations += 1
            confidence_base += 0.10
        elif bb_position == "NEAR_UPPER":
            confidence_base -= 0.05

        # 4. Bonus si tendencia es fuerte
        if trend == "STRONG_UP":
            confidence_base += 0.10

        # Solo generar señal si hay mínima confianza
        if confidence_base < 0.30:
            result["reason"] = f"Confianza insuficiente para BUY ({confidence_base:.2f})"
            return result

        result["signal"] = "BUY"
        result["confidence"] = min(0.95, confidence_base)
        result["reason"] = f"Trend Following BUY - {confirmations} confirmaciones"

        # Ajustar SL/TP según volatilidad
        volatility = context.get("volatility", "NORMAL")
        if volatility == "HIGH":
            result["sl_pips"] = 20
            result["tp_pips"] = 35
        elif volatility == "LOW":
            result["sl_pips"] = 10
            result["tp_pips"] = 15

        return result

    # ========== SEÑAL BAJISTA ==========
    if trend in ["STRONG_DOWN", "DOWN"]:

        confirmations = 0
        confidence_base = 0.50

        # 1. MACD confirma dirección (no es hard-reject, ajusta confianza)
        if macd_state in ["STRONG_BEARISH"]:
            confirmations += 1
            confidence_base += 0.20
        elif macd_state in ["BEARISH"]:
            confirmations += 1
            confidence_base += 0.15
        elif macd_state == "NEUTRAL":
            confidence_base += 0.05
        else:
            # MACD alcista en tendencia bajista: señal débil pero no rechazar
            confidence_base -= 0.10

        # 2. RSI no debe estar sobrevendido
        if rsi_state == "OVERSOLD":
            result["reason"] = f"RSI sobrevendido, esperando rebote (rsi_state={rsi_state})"
            return result

        if rsi_state in ["WEAK", "NEUTRAL"]:
            confirmations += 1
            confidence_base += 0.05

        # 3. Mejor entrada en pullback (cerca de media de Bollinger)
        if bb_position in ["MIDDLE", "UPPER_HALF"]:
            confirmations += 1
            confidence_base += 0.10
        elif bb_position == "NEAR_LOWER":
            confidence_base -= 0.05

        # 4. Bonus si tendencia es fuerte
        if trend == "STRONG_DOWN":
            confidence_base += 0.10

        # Solo generar señal si hay mínima confianza
        if confidence_base < 0.30:
            result["reason"] = f"Confianza insuficiente para SELL ({confidence_base:.2f})"
            return result

        result["signal"] = "SELL"
        result["confidence"] = min(0.95, confidence_base)
        result["reason"] = f"Trend Following SELL - {confirmations} confirmaciones"

        # Ajustar SL/TP según volatilidad
        volatility = context.get("volatility", "NORMAL")
        if volatility == "HIGH":
            result["sl_pips"] = 20
            result["tp_pips"] = 35
        elif volatility == "LOW":
            result["sl_pips"] = 10
            result["tp_pips"] = 15

        return result
    
    # Sin señal
    result["reason"] = "Sin setup válido"
    return result

# decision_engine/context_analyzer.py
# VERSIÓN CORREGIDA v3.0 - Sin bloqueo de volatilidad LOW

def analyze_market_context(market_data: dict) -> dict:
    """
    Analiza el contexto del mercado.
    CORREGIDO: Ya NO bloquea trading por volatilidad LOW
    """
    
    context = {
        "trend": "NONE",
        "volatility": "NORMAL",
        "trade_allowed": True,  # Por defecto permitido
        "confidence": 0.0,
        "rsi_state": "NEUTRAL",
        "macd_state": "NEUTRAL",
        "bb_position": "MIDDLE",
        "market_regime": "UNDEFINED"
    }
    
    # VALIDACIÓN
    if not market_data or "indicators" not in market_data:
        print("⚠️ market_data incompleto")
        context["trade_allowed"] = False
        return context
    
    # EXTRACCIÓN
    indicators = market_data.get("indicators", {})
    analysis = market_data.get("analysis", {})
    bid = market_data.get("bid", 0)
    
    rsi = indicators.get("rsi", 50)
    
    macd = indicators.get("macd", {})
    macd_main = macd.get("main", 0)
    macd_signal = macd.get("signal", 0)
    macd_histogram = macd.get("histogram", 0)
    
    ema = indicators.get("ema", {})
    ema_fast = ema.get("fast", 0)
    ema_slow = ema.get("slow", 0)
    ema_long = ema.get("long", 0)
    
    bb = indicators.get("bollinger", {})
    bb_upper = bb.get("upper", 0)
    bb_middle = bb.get("middle", 0)
    bb_lower = bb.get("lower", 0)
    
    atr = indicators.get("atr", 0)
    
    trend_ea = analysis.get("trend", "SIDEWAYS")
    volatility_ea = analysis.get("volatility", "NORMAL")
    
    # ANÁLISIS TENDENCIA
    context["trend"] = trend_ea
    
    if ema_fast > 0 and ema_slow > 0 and ema_long > 0:
        if trend_ea in ["STRONG_UP", "UP"]:
            if ema_fast > ema_slow > ema_long and bid > ema_fast:
                context["confidence"] = 0.85
            elif ema_fast > ema_slow and bid > ema_fast:
                context["confidence"] = 0.70
            else:
                context["confidence"] = 0.50
        elif trend_ea in ["STRONG_DOWN", "DOWN"]:
            if ema_fast < ema_slow < ema_long and bid < ema_fast:
                context["confidence"] = 0.85
            elif ema_fast < ema_slow and bid < ema_fast:
                context["confidence"] = 0.70
            else:
                context["confidence"] = 0.50
        else:
            context["confidence"] = 0.40
    
    # VOLATILIDAD
    context["volatility"] = volatility_ea
    
    # RSI
    if rsi > 70:
        context["rsi_state"] = "OVERBOUGHT"
    elif rsi > 60:
        context["rsi_state"] = "STRONG"
    elif rsi < 30:
        context["rsi_state"] = "OVERSOLD"
    elif rsi < 40:
        context["rsi_state"] = "WEAK"
    else:
        context["rsi_state"] = "NEUTRAL"
    
    # MACD
    if macd_histogram > 0:
        if macd_histogram > abs(macd_main * 0.3):
            context["macd_state"] = "STRONG_BULLISH"
        else:
            context["macd_state"] = "BULLISH"
    elif macd_histogram < 0:
        if abs(macd_histogram) > abs(macd_main * 0.3):
            context["macd_state"] = "STRONG_BEARISH"
        else:
            context["macd_state"] = "BEARISH"
    else:
        context["macd_state"] = "NEUTRAL"
    
    # BOLLINGER BANDS
    if bb_upper > 0 and bb_lower > 0 and bb_middle > 0:
        bb_range = bb_upper - bb_lower
        if bb_range > 0:
            bb_position = (bid - bb_lower) / bb_range
            
            if bb_position > 0.9:
                context["bb_position"] = "NEAR_UPPER"
            elif bb_position > 0.7:
                context["bb_position"] = "UPPER_HALF"
            elif bb_position < 0.1:
                context["bb_position"] = "NEAR_LOWER"
            elif bb_position < 0.3:
                context["bb_position"] = "LOWER_HALF"
            else:
                context["bb_position"] = "MIDDLE"
    
    # RÉGIMEN DE MERCADO
    if context["volatility"] == "HIGH":
        if context["trend"] in ["STRONG_UP", "STRONG_DOWN"]:
            context["market_regime"] = "TRENDING_VOLATILE"
        else:
            context["market_regime"] = "CHOPPY"
    elif context["volatility"] == "LOW":
        context["market_regime"] = "QUIET"
    else:
        if context["trend"] in ["STRONG_UP", "STRONG_DOWN"]:
            context["market_regime"] = "TRENDING"
        elif context["trend"] == "SIDEWAYS":
            context["market_regime"] = "RANGING"
        else:
            context["market_regime"] = "TRANSITIONING"
    
    # ========================================
    # BLOQUEOS DE TRADING (SIMPLIFICADOS)
    # ========================================
    
    # ✅ ELIMINADO: Bloqueo por volatilidad LOW
    # Los mercados QUIET pueden generar señales de mean reversion
    
    # Bloquear solo mercado CHOPPY (alta volatilidad sin tendencia)
    if context["market_regime"] == "CHOPPY":
        context["trade_allowed"] = False
        print("⛔ Trading bloqueado: Mercado choppy")
    
    # Bloquear divergencias extremas
    if context["trend"] in ["UP", "STRONG_UP"] and context["rsi_state"] == "OVERBOUGHT":
        if context["macd_state"] in ["BEARISH", "STRONG_BEARISH"]:
            # Permitir trading pero con confianza reducida
            context["confidence"] = max(0.3, context["confidence"] - 0.2)
            print("⚠️ Divergencia bajista detectada - Confianza reducida")
    
    if context["trend"] in ["DOWN", "STRONG_DOWN"] and context["rsi_state"] == "OVERSOLD":
        if context["macd_state"] in ["BULLISH", "STRONG_BULLISH"]:
            # Permitir trading pero con confianza reducida
            context["confidence"] = max(0.3, context["confidence"] - 0.2)
            print("⚠️ Divergencia alcista detectada - Confianza reducida")
    
    # Bonus de confianza con confirmaciones
    if context["trade_allowed"]:
        confirmations = 0
        
        if context["trend"] in ["STRONG_UP", "UP"]:
            if context["macd_state"] in ["BULLISH", "STRONG_BULLISH"]:
                confirmations += 1
            if context["rsi_state"] in ["STRONG", "NEUTRAL"]:
                confirmations += 1
        elif context["trend"] in ["STRONG_DOWN", "DOWN"]:
            if context["macd_state"] in ["BEARISH", "STRONG_BEARISH"]:
                confirmations += 1
            if context["rsi_state"] in ["WEAK", "NEUTRAL"]:
                confirmations += 1
        
        context["confidence"] = min(0.95, context["confidence"] + (confirmations * 0.1))
    
    return context

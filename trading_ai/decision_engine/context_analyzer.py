# decision_engine/context_analyzer.py

def analyze_market_context(market_data: dict) -> dict:
    """
    Analiza el contexto general del mercado.
    NO decide trades.
    SOLO clasifica el entorno.
    """

    context = {
        "trend": "NONE",
        "volatility": "NORMAL",
        "trade_allowed": True,
        "confidence": 0.0
    }

    trend_strength = market_data.get("trend_strength", 0)
    volatility = market_data.get("volatility", 0)

    # ---- Tendencia ----
    if trend_strength > 0.7:
        context["trend"] = "STRONG_UP"
    elif trend_strength < -0.7:
        context["trend"] = "STRONG_DOWN"
    else:
        context["trend"] = "RANGE"

    # ---- Volatilidad ----
    if volatility > 0.8:
        context["volatility"] = "HIGH"
    elif volatility < 0.2:
        context["volatility"] = "LOW"

    # ---- Reglas de bloqueo ----
    if context["volatility"] == "LOW":
        context["trade_allowed"] = False

    # ---- Confianza (muy simple por ahora) ----
    context["confidence"] = abs(trend_strength)

    return context
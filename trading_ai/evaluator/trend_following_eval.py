def evaluate(context: dict, market_data: dict):
    if context["trend"] == "STRONG_UP":
        return {
            "signal": "BUY",
            "confidence": 0.7,
            "timeframe": "M5"
        }

    if context["trend"] == "STRONG_DOWN":
        return {
            "signal": "SELL",
            "confidence": 0.7,
            "timeframe": "M5"
        }

    return {
        "signal": None,
        "confidence": 0.0,
        "timeframe": None
    }
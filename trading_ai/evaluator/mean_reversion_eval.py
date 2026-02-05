def evaluate(context: dict, market_data: dict):
    if context["trend"] == "RANGE" and market_data.get("overextended"):
        return {
            "signal": "SELL",
            "confidence": 0.6,
            "timeframe": "M5"
        }

    return {
        "signal": None,
        "confidence": 0.0,
        "timeframe": None
    }
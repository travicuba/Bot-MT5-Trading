def is_valid(context: dict) -> bool:
    return (
        context["trend"] == "RANGE"
        and context["volatility"] != "HIGH"
        and context["trade_allowed"]
    )

def meta():
    return {
        "name": "MEAN_REVERSION",
        "timeframes": ["M5"],
        "risk_profile": "conservative"
    }
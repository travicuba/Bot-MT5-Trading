def is_valid(context: dict) -> bool:
    return (
        context["trend"] in ["STRONG_UP", "STRONG_DOWN"]
        and context["volatility"] == "NORMAL"
        and context["trade_allowed"]
    )

def meta():
    return {
        "name": "TREND_FOLLOWING",
        "timeframes": ["M5", "M15"],
        "risk_profile": "normal"
    }
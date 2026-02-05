from indicators.ema import ema

def check(market, tf):
    closes = market["timeframes"][tf]["close"]
    ema20 = ema(closes[-50:], 20)
    ema50 = ema(closes[-50:], 50)

    if ema20 > ema50:
        return {"valid": True, "direction": "BUY"}
    if ema20 < ema50:
        return {"valid": True, "direction": "SELL"}

    return {"valid": False}

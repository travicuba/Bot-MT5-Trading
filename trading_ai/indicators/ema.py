def ema(prices, period):
    k = 2 / (period + 1)
    ema_val = prices[0]
    for p in prices[1:]:
        ema_val = p * k + ema_val * (1 - k)
    return ema_val

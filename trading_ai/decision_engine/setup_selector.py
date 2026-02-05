from decision_engine.setup_scorer import score_setups


def get_available_setups():
    """
    Define TODOS los setups que el sistema conoce.
    Aquí NO hay lógica, solo definición.
    """
    return [
        {
            "name": "ema_pullback_trend",
            "type": "TREND",
            "timeframes": ["M5", "M15"],
            "conditions": ["ema_trend", "pullback"]
        },
        {
            "name": "range_reversal",
            "type": "RANGE",
            "timeframes": ["M5"],
            "conditions": ["range", "reversal"]
        },
        {
            "name": "breakout_volatility",
            "type": "BREAKOUT",
            "timeframes": ["M15"],
            "conditions": ["volatility", "breakout"]
        }
    ]


def select_setup(context):
    """
    Decide qué setup usar según el contexto y el scoring dinámico.
    Puede devolver None si NO hay setup válido.
    """
    setups = get_available_setups()

    if not setups:
        return None

    scored_setups = score_setups(setups, context)

    best = scored_setups[0]

    # Umbral mínimo de calidad
    if best["score"] < 0.55:
        return None

    return best
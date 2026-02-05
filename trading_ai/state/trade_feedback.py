from datetime import datetime
from state.state_manager import load_state, save_state


def register_trade_result(
    setup_name: str,
    result: str,          # "WIN" o "LOSS"
    pips: float
):
    """
    Registra el resultado de una operación y actualiza
    la memoria del bot.
    """

    state = load_state()

    # -------------------------------
    # Inicializaciones seguras
    # -------------------------------
    state.setdefault("consecutive_losses", 0)
    state.setdefault("setup_stats", {})
    state.setdefault("last_trade_result", None)
    state.setdefault("last_trade_pips", None)

    # -------------------------------
    # Actualizar resultado global
    # -------------------------------
    state["last_trade_result"] = result
    state["last_trade_pips"] = pips
    state["last_trade_time"] = datetime.utcnow().isoformat()

    # -------------------------------
    # Manejo de pérdidas consecutivas
    # -------------------------------
    if result == "LOSS":
        state["consecutive_losses"] += 1
    else:
        state["consecutive_losses"] = 0

    # -------------------------------
    # Estadísticas por setup
    # -------------------------------
    setup_stats = state["setup_stats"].get(setup_name, {
        "wins": 0,
        "losses": 0,
        "total_pips": 0.0,
        "trades": 0,
        "last_used": None
    })

    setup_stats["trades"] += 1
    setup_stats["total_pips"] += pips
    setup_stats["last_used"] = datetime.utcnow().isoformat()

    if result == "WIN":
        setup_stats["wins"] += 1
    else:
        setup_stats["losses"] += 1

    # Guardar de nuevo
    state["setup_stats"][setup_name] = setup_stats

    # -------------------------------
    # Cooldown automático (opcional)
    # -------------------------------
    if state["consecutive_losses"] >= 3:
        state["cooldown_until"] = (
            datetime.utcnow().isoformat()
        )

    save_state(state)

    print("🧠 Trade feedback registrado:")
    print(f"   Setup: {setup_name}")
    print(f"   Resultado: {result}")
    print(f"   Pips: {pips}")
    print(f"   Pérdidas seguidas: {state['consecutive_losses']}")
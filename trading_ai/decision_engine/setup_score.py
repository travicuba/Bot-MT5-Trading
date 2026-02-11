from state.state_manager import load_state, save_state
from datetime import datetime


def score_setups(setups, context):
    """
    Devuelve lista de setups con score dinámico.
    La lógica base se mantiene intacta.
    Se añaden solo metadatos para aprendizaje futuro.
    """

    state = load_state()
    setup_stats = state.get("setup_stats", {})

    scored = []

    for setup in setups:
        name = setup["name"]

        # -----------------------------
        # Estadísticas históricas
        # -----------------------------
        stats = setup_stats.get(name, {
            "wins": 0,
            "losses": 0,
            "last_used": None,
            "last_score": None
        })

        total = stats["wins"] + stats["losses"]
        winrate = stats["wins"] / total if total > 0 else 0.5

        # -----------------------------
        # Penalizaciones (lógica original)
        # -----------------------------
        penalty = 0.0

        if context.get("market_phase") == "RANGE" and setup.get("type") == "TREND":
            penalty += 0.2

        if stats["losses"] >= 3:
            penalty += 0.3

        score = max(0.0, winrate - penalty)

        # -----------------------------
        # Registro pasivo para aprendizaje
        # (NO afecta la decisión actual)
        # -----------------------------
        stats["last_used"] = datetime.utcnow().isoformat()
        stats["last_score"] = round(score, 3)

        setup_stats[name] = stats

        scored.append({
            **setup,
            "score": round(score, 3),
            "winrate": round(winrate, 2),
            "stats": {
                "wins": stats["wins"],
                "losses": stats["losses"],
                "total": total
            }
        })

    # Guardar estado actualizado (sin modificar resultados)
    state["setup_stats"] = setup_stats
    save_state(state)

    # Orden final (lógica original)
    return sorted(scored, key=lambda x: x["score"], reverse=True)
import json
import os
from datetime import datetime

STATE_FILE = "state/bot_state.json"


# ==============================
# CARGA DE ESTADO
# ==============================
def load_state():
    if not os.path.exists(STATE_FILE):
        return _default_state()

    with open(STATE_FILE, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return _default_state()


# ==============================
# GUARDADO DE ESTADO
# ==============================
def save_state(state):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=4)


# ==============================
# ESTADO BASE (MEMORIA DEL BOT)
# ==============================
def _default_state():
    return {
        "bot": {
            "started_at": None,
            "last_update": None,
            "status": "IDLE"
        },
        "setup_stats": {
            # "TREND_FOLLOWING": {"wins": 0, "losses": 0, "total": 0}
        },
        "trade_history": [],
        "learning": {
            "total_trades": 0,
            "wins": 0,
            "losses": 0
        }
    }


# ==============================
# ACTUALIZACIONES GENERALES
# ==============================
def update_bot_status(status):
    state = load_state()
    state["bot"]["status"] = status
    state["bot"]["last_update"] = datetime.utcnow().isoformat()
    save_state(state)


# ==============================
# REGISTRAR RESULTADO DE SETUP
# ==============================
def register_setup_result(setup_name, result):
    """
    result: 'win' o 'loss'
    """
    state = load_state()

    stats = state["setup_stats"].get(setup_name, {
        "wins": 0,
        "losses": 0,
        "total": 0
    })

    if result == "win":
        stats["wins"] += 1
        state["learning"]["wins"] += 1
    else:
        stats["losses"] += 1
        state["learning"]["losses"] += 1

    stats["total"] += 1
    state["learning"]["total_trades"] += 1

    state["setup_stats"][setup_name] = stats
    state["bot"]["last_update"] = datetime.utcnow().isoformat()

    save_state(state)


# ==============================
# REGISTRAR TRADE COMPLETO
# ==============================
def log_trade(trade_data):
    """
    trade_data: dict con info del trade (setup, symbol, result, etc.)
    """
    state = load_state()
    trade_data["logged_at"] = datetime.utcnow().isoformat()
    state["trade_history"].append(trade_data)
    save_state(state)
import json
import os
from datetime import datetime

# ⚠️ Ruta ABSOLUTA al directorio FILES de MT5 (Wine)
SIGNAL_PATH = "/home/travieso/.wine/drive_c/Program Files/MetaTrader 5/MQL5/Files/signals/signal.json"


def evaluate_signal(setup_name, context, market_data):
    """
    Evalúa señal, la devuelve y la guarda en signal.json para MT5
    """

    # --- LÓGICA EXISTENTE (NO TOCADA) ---
    if context["trend"] in ["UP", "STRONG_UP", "BULLISH"]:
        action = "BUY"
        confidence = 0.82
        sl_pips = 10
        tp_pips = 15

    elif context["trend"] in ["DOWN", "STRONG_DOWN", "BEARISH"]:
        action = "SELL"
        confidence = 0.80
        sl_pips = 10
        tp_pips = 15

    else:
        print("❌ No hay señal válida")
        return {
            "action": "NONE",
            "confidence": 0.0,
            "sl_pips": 0,
            "tp_pips": 0
        }

    # =========================
    # 🔑 SIGNAL ID (NUEVO)
    # =========================
    now = datetime.utcnow()
    signal_id = f"{now.strftime('%Y%m%d_%H%M%S')}_{action}_EURUSD"

    signal = {
        "signal_id": signal_id,              
        "action": action,
        "confidence": confidence,
        "sl_pips": sl_pips,
        "tp_pips": tp_pips,
        "symbol": "EURUSD",
        "timeframe": "M5",
        "timestamp": now.isoformat()
    }


    # --- GARANTIZAR DIRECTORIO ---
    try:
        os.makedirs(os.path.dirname(SIGNAL_PATH), exist_ok=True)
    except Exception as e:
        print("❌ ERROR creando directorio de signals:", e)
        return None

    # --- ESCRITURA SEGURA DEL JSON ---
    try:
        temp_path = SIGNAL_PATH + ".tmp"

        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(signal, f, indent=4)

        os.replace(temp_path, SIGNAL_PATH)

    except Exception as e:
        print("❌ ERROR escribiendo signal.json:", e)
        return None

    # --- LOGS CLAROS ---
    print("✅ signal.json creado correctamente")
    print("📍 Ruta absoluta:", SIGNAL_PATH)
    print("📦 Contenido:")
    print(json.dumps(signal, indent=4))

    return signal
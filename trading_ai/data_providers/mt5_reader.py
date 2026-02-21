import json
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from mt5_paths import MARKET_DATA_FILE as MT5_MARKET_FILE


def read_market_data():
    if not os.path.exists(MT5_MARKET_FILE):
        print("⚠️ market_data.json no encontrado")
        return None

    try:
        with open(MT5_MARKET_FILE, "r") as f:
            data = json.load(f)

        print("📥 Market data cargado desde MT5")
        return data

    except Exception as e:
        print("❌ Error leyendo market_data.json:", e)
        return None
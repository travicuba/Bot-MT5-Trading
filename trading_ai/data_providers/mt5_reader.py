import json
import os

MT5_MARKET_FILE = "/home/travieso/.wine/drive_c/Program Files/MetaTrader 5/MQL5/Files/market_data.json"


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
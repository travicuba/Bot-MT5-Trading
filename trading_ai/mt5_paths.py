"""
mt5_paths.py - Configuracion centralizada de rutas MT5

En modo VPS (nuevo): apunta a carpeta local mt5_exchange/
  que el puente Windows sincroniza con el MT5 nativo en la PC.

En modo Wine (legacy): mantener el comportamiento anterior
  definiendo MT5_FILES_BASE=/home/travieso/.wine/drive_c/Program Files/MetaTrader 5/MQL5/Files

La variable de entorno MT5_FILES_BASE permite cambiar el modo sin tocar codigo.
"""

import os
from pathlib import Path

# Base del intercambio de archivos MT5
# Por defecto apunta a carpeta local del VPS (modo nuevo)
# Se puede sobreescribir con variable de entorno
_DEFAULT_BASE = os.path.join(os.path.dirname(__file__), "mt5_exchange")

BASE = os.environ.get("MT5_FILES_BASE", _DEFAULT_BASE)

# ==============================
# RUTAS DE ARCHIVOS MT5
# ==============================

SIGNAL_FILE        = os.path.join(BASE, "signals", "signal.json")
BOT_STATUS_FILE    = os.path.join(BASE, "bot_status.json")
MARKET_DATA_FILE   = os.path.join(BASE, "market_data.json")
FEEDBACK_FILE_LEGACY = os.path.join(BASE, "trade_feedback.json")
FEEDBACK_FOLDER    = os.path.join(BASE, "trade_feedback")

def ensure_dirs():
    """Crea los directorios necesarios si no existen"""
    os.makedirs(os.path.join(BASE, "signals"), exist_ok=True)
    os.makedirs(FEEDBACK_FOLDER, exist_ok=True)

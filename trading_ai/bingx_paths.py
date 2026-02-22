"""
bingx_paths.py — Rutas de archivos exclusivas para el bot BingX.

IMPORTANTE: BingX usa rutas completamente separadas de MT5.
Ningún archivo es compartido entre ambos bots.
"""
import os
from pathlib import Path

_DIR = os.path.dirname(__file__)

# Base de intercambio de archivos BingX (carpeta propia, nunca la de MT5)
BINGX_BASE = os.path.join(_DIR, "bingx_exchange")

# ── Archivos de estado ────────────────────────────────────────────────────────
BINGX_STATUS_FILE   = os.path.join(BINGX_BASE, "bingx_status.json")
BINGX_SIGNAL_FILE   = os.path.join(BINGX_BASE, "bingx_signal.json")
BINGX_MARKET_FILE   = os.path.join(BINGX_BASE, "bingx_market.json")

# ── Datos persistentes ────────────────────────────────────────────────────────
BINGX_STATS_FILE    = os.path.join(_DIR, "bingx_stats.json")
BINGX_HISTORY_FILE  = os.path.join(_DIR, "bingx_history.json")
BINGX_CONFIG_FILE   = os.path.join(_DIR, "bingx_config.json")

# ── Aprendizaje (exclusivo BingX, separado de MT5) ───────────────────────────
BINGX_LEARNING_DIR  = os.path.join(_DIR, "bingx_learning_data")
BINGX_SETUP_STATS   = os.path.join(BINGX_LEARNING_DIR, "setup_stats.json")
BINGX_TRADE_HISTORY = os.path.join(BINGX_LEARNING_DIR, "trade_history.json")
BINGX_ML_STATE      = os.path.join(BINGX_LEARNING_DIR, "ml_state.json")
BINGX_PROCESSED     = os.path.join(BINGX_LEARNING_DIR, "processed_signals.txt")

# ── Logs ──────────────────────────────────────────────────────────────────────
BINGX_LOG_FILE      = os.path.join(BINGX_BASE, "bingx_bot.log")

# ── Feedback (trades cerrados para aprendizaje) ───────────────────────────────
BINGX_FEEDBACK_DIR  = os.path.join(BINGX_BASE, "bingx_feedback")


def ensure_dirs():
    """Crea todos los directorios necesarios para BingX si no existen."""
    os.makedirs(BINGX_BASE, exist_ok=True)
    os.makedirs(BINGX_FEEDBACK_DIR, exist_ok=True)
    os.makedirs(BINGX_LEARNING_DIR, exist_ok=True)
    # Escribir al log de BingX en lugar de print() para no contaminar sys.stdout
    # (bot_gui_professional.py redirige sys.stdout al panel de logs de MT5)
    try:
        with open(BINGX_LOG_FILE, "a", encoding="utf-8") as _f:
            from datetime import datetime as _dt
            _f.write(f"[{_dt.now():%Y-%m-%d %H:%M:%S}] [BingX] Rutas inicializadas en: {BINGX_BASE}\n")
    except Exception:
        pass

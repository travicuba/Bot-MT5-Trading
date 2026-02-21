#!/usr/bin/env python3
"""
api_server.py v1.0 - API REST del Bot de Trading para la App Windows

Expone:
  - Control del bot (start/stop/status)
  - Estadisticas e historial
  - Configuracion
  - Puente de archivos MT5 (sincronizacion con MT5 nativo en Windows PC)
  - Modo mantenimiento

Uso:
  python api_server.py
  MT5_FILES_BASE=./mt5_exchange BOT_API_KEY=mi-clave python api_server.py
"""

import os
import sys
import json
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

# Asegurar que el directorio del bot esta en el path
BOT_DIR = Path(__file__).parent
sys.path.insert(0, str(BOT_DIR))

try:
    from fastapi import FastAPI, HTTPException, Header, Depends, Query
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse
    from pydantic import BaseModel
    import uvicorn
except ImportError:
    print("ERROR: Instalar dependencias: pip install fastapi uvicorn")
    sys.exit(1)

from mt5_paths import (
    BASE as MT5_EXCHANGE,
    SIGNAL_FILE,
    BOT_STATUS_FILE,
    MARKET_DATA_FILE,
    FEEDBACK_FILE_LEGACY,
    FEEDBACK_FOLDER,
    ensure_dirs,
)

# ==============================
# CONFIGURACION
# ==============================
API_KEY  = os.environ.get("BOT_API_KEY", "changeme-2024")
API_PORT = int(os.environ.get("API_PORT", "8080"))
API_HOST = os.environ.get("API_HOST", "0.0.0.0")

BOT_CONFIG_FILE   = BOT_DIR / "bot_config.json"
MAINTENANCE_FILE  = BOT_DIR / "maintenance.json"
HISTORY_FILE      = BOT_DIR / "learning_data" / "trade_history.json"
STATS_FILE        = BOT_DIR / "learning_data" / "setup_stats.json"
DEBUG_FILE        = BOT_DIR / "logs" / "debug.json"
ML_STATE_FILE     = BOT_DIR / "learning_data" / "ml_state.json"

# ==============================
# ESTADO DEL PROCESO BOT
# ==============================
bot_process: Optional[subprocess.Popen] = None
bot_start_time: Optional[float] = None
bot_lock = threading.Lock()


def is_bot_running() -> bool:
    global bot_process
    if bot_process is None:
        return False
    return bot_process.poll() is None


# ==============================
# APP FASTAPI
# ==============================
app = FastAPI(
    title="Trading Bot API",
    description="API REST para la app de escritorio del Bot MT5",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==============================
# AUTENTICACION
# ==============================
def verify_key(x_api_key: Optional[str] = Header(default=None)):
    if not x_api_key or x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="API key invalida o ausente")
    return x_api_key


# ==============================
# HELPERS
# ==============================
def read_json(path: Path) -> Optional[Any]:
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return None


def write_json(path: Path, data: Any) -> bool:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"[API] Error escribiendo {path}: {e}")
        return False


def get_today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


# ==============================
# MODELOS PYDANTIC
# ==============================
class BotConfigUpdate(BaseModel):
    min_confidence: Optional[int] = None
    cooldown: Optional[int] = None
    max_daily_trades: Optional[int] = None
    max_losses: Optional[int] = None
    lot_size: Optional[float] = None
    start_hour: Optional[str] = None
    end_hour: Optional[str] = None
    max_concurrent_trades: Optional[int] = None
    min_signal_interval: Optional[int] = None
    avoid_repeat_strategy: Optional[bool] = None
    auto_optimize: Optional[bool] = None


class MaintenanceUpdate(BaseModel):
    enabled: bool
    message: str = ""


class MarketDataUpload(BaseModel):
    data: Dict[str, Any]


class FeedbackUpload(BaseModel):
    signal_id: str
    result: str        # WIN, LOSS, BREAKEVEN
    pips: float
    timestamp: Optional[str] = None


# ==============================
# RUTAS - SALUD Y VERSION
# ==============================
@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
    }


# ==============================
# RUTAS - ESTADO DEL BOT
# ==============================
@app.get("/api/status", dependencies=[Depends(verify_key)])
def get_status():
    running = is_bot_running()
    uptime  = int(time.time() - bot_start_time) if (bot_start_time and running) else 0

    bot_status = read_json(Path(BOT_STATUS_FILE)) or {}
    active_trades = 0

    # Intentar leer trades activos del debug
    debug = read_json(DEBUG_FILE) or []
    if debug:
        last = debug[-1] if isinstance(debug, list) else {}
        msg  = str(last.get("message", ""))
        if "Activos:" in msg:
            try:
                active_trades = int(msg.split("Activos:")[1].strip().split()[0])
            except Exception:
                pass

    return {
        "running":       running,
        "uptime_seconds": uptime,
        "pid":           bot_process.pid if (bot_process and running) else None,
        "active_trades": active_trades,
        "bot_status":    bot_status,
        "timestamp":     datetime.now().isoformat(),
    }


# ==============================
# RUTAS - CONTROL DEL BOT
# ==============================
@app.post("/api/bot/start", dependencies=[Depends(verify_key)])
def start_bot():
    global bot_process, bot_start_time

    with bot_lock:
        if is_bot_running():
            return {"success": False, "message": "El bot ya esta corriendo"}

        main_py = BOT_DIR / "main.py"
        if not main_py.exists():
            raise HTTPException(status_code=500, detail="main.py no encontrado")

        try:
            env = os.environ.copy()
            env["MT5_FILES_BASE"] = str(MT5_EXCHANGE)

            bot_process = subprocess.Popen(
                [sys.executable, str(main_py)],
                cwd=str(BOT_DIR),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            bot_start_time = time.time()
            time.sleep(1.5)

            if bot_process.poll() is not None:
                stderr_out = bot_process.stderr.read().decode("utf-8", errors="ignore")
                bot_process = None
                bot_start_time = None
                return {"success": False, "message": f"Bot fallo al iniciar: {stderr_out[:300]}"}

            return {
                "success": True,
                "message": "Bot iniciado correctamente",
                "pid":     bot_process.pid,
            }
        except Exception as e:
            bot_process = None
            bot_start_time = None
            return {"success": False, "message": str(e)}


@app.post("/api/bot/stop", dependencies=[Depends(verify_key)])
def stop_bot():
    global bot_process, bot_start_time

    with bot_lock:
        if not is_bot_running():
            return {"success": False, "message": "El bot no esta corriendo"}

        try:
            bot_process.terminate()
            bot_process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            bot_process.kill()
        except Exception:
            pass

        bot_process    = None
        bot_start_time = None
        return {"success": True, "message": "Bot detenido correctamente"}


# ==============================
# RUTAS - CONFIGURACION
# ==============================
_DEFAULT_CONFIG = {
    "min_confidence": 35,
    "cooldown": 30,
    "max_daily_trades": 50,
    "max_losses": 5,
    "lot_size": 0.01,
    "start_hour": "00:00",
    "end_hour": "23:59",
    "max_concurrent_trades": 3,
    "min_signal_interval": 60,
    "avoid_repeat_strategy": True,
    "auto_optimize": True,
}


@app.get("/api/config", dependencies=[Depends(verify_key)])
def get_config():
    config = read_json(BOT_CONFIG_FILE) or _DEFAULT_CONFIG.copy()
    return config


@app.put("/api/config", dependencies=[Depends(verify_key)])
def update_config(update: BotConfigUpdate):
    config = read_json(BOT_CONFIG_FILE) or _DEFAULT_CONFIG.copy()

    for field, value in update.dict(exclude_none=True).items():
        config[field] = value

    if write_json(BOT_CONFIG_FILE, config):
        return {"success": True, "config": config}
    raise HTTPException(status_code=500, detail="Error guardando configuracion")


# ==============================
# RUTAS - ESTADISTICAS E HISTORIAL
# ==============================
@app.get("/api/stats", dependencies=[Depends(verify_key)])
def get_stats():
    history: List[Dict] = read_json(HISTORY_FILE) or []
    setup_stats = read_json(STATS_FILE) or {}
    ml_state    = read_json(ML_STATE_FILE) or {}

    total  = len(history)
    wins   = sum(1 for t in history if t.get("result") == "WIN")
    losses = sum(1 for t in history if t.get("result") == "LOSS")
    total_pips = sum(float(t.get("pips", 0)) for t in history)
    win_rate   = (wins / total * 100) if total > 0 else 0.0

    today = get_today_str()
    today_trades = [t for t in history if str(t.get("timestamp", "")).startswith(today)]
    today_wins   = sum(1 for t in today_trades if t.get("result") == "WIN")
    today_pips   = sum(float(t.get("pips", 0)) for t in today_trades)

    # Stats por semana (ultimos 7 dias)
    from datetime import timedelta
    week_start = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    week_trades = [t for t in history if str(t.get("timestamp", "")) >= week_start]
    week_wins   = sum(1 for t in week_trades if t.get("result") == "WIN")
    week_pips   = sum(float(t.get("pips", 0)) for t in week_trades)

    return {
        "total_trades": total,
        "wins":         wins,
        "losses":       losses,
        "win_rate":     round(win_rate, 1),
        "total_pips":   round(total_pips, 1),
        "today": {
            "trades": len(today_trades),
            "wins":   today_wins,
            "pips":   round(today_pips, 1),
        },
        "week": {
            "trades": len(week_trades),
            "wins":   week_wins,
            "pips":   round(week_pips, 1),
        },
        "setup_stats": setup_stats,
        "ml_state":    ml_state,
    }


@app.get("/api/history", dependencies=[Depends(verify_key)])
def get_history(
    limit:  int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    history: List[Dict] = read_json(HISTORY_FILE) or []
    history = list(reversed(history))   # mas reciente primero
    total = len(history)
    page  = history[offset : offset + limit]
    return {"trades": page, "total": total, "limit": limit, "offset": offset}


@app.get("/api/debug", dependencies=[Depends(verify_key)])
def get_debug(limit: int = Query(default=100, ge=1, le=500)):
    logs = read_json(DEBUG_FILE) or []
    if isinstance(logs, list):
        logs = list(reversed(logs))
    return logs[:limit]


# ==============================
# RUTAS - MODO MANTENIMIENTO
# ==============================
@app.get("/api/maintenance")
def get_maintenance():
    """Sin autenticacion - la app necesita saber esto antes de conectar"""
    data = read_json(MAINTENANCE_FILE)
    if not data:
        return {"enabled": False, "message": "", "since": None}
    return data


@app.put("/api/maintenance", dependencies=[Depends(verify_key)])
def set_maintenance(update: MaintenanceUpdate):
    data = {
        "enabled": update.enabled,
        "message": update.message,
        "since":   datetime.now().isoformat() if update.enabled else None,
    }
    if write_json(MAINTENANCE_FILE, data):
        return {"success": True, "maintenance": data}
    raise HTTPException(status_code=500, detail="Error actualizando modo mantenimiento")


# ==============================
# RUTAS - PUENTE MT5 (Bridge Windows <-> VPS)
# ==============================
@app.get("/api/mt5/signal", dependencies=[Depends(verify_key)])
def get_signal():
    """Windows bridge obtiene la señal pendiente del bot Python"""
    signal_path = Path(SIGNAL_FILE)
    if signal_path.exists():
        data = read_json(signal_path)
        if data:
            return data
    raise HTTPException(status_code=404, detail="No hay señal pendiente")


@app.delete("/api/mt5/signal", dependencies=[Depends(verify_key)])
def consume_signal():
    """
    Windows bridge llama esto cuando el EA de MT5 leyó y borró signal.json localmente.
    Indica al bot Python que puede enviar la siguiente señal.
    """
    signal_path = Path(SIGNAL_FILE)
    if signal_path.exists():
        try:
            signal_path.unlink()
            return {"success": True, "message": "Señal consumida"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    return {"success": True, "message": "Señal ya no existia"}


@app.get("/api/mt5/bot_status", dependencies=[Depends(verify_key)])
def get_mt5_bot_status():
    """Windows bridge descarga bot_status.json para escribirlo en MT5 local"""
    data = read_json(Path(BOT_STATUS_FILE))
    if data:
        return data
    return {"running": False, "timestamp": int(time.time())}


@app.put("/api/mt5/market_data", dependencies=[Depends(verify_key)])
def upload_market_data(upload: MarketDataUpload):
    """Windows bridge sube market_data.json del MT5 Windows al VPS"""
    if write_json(Path(MARKET_DATA_FILE), upload.data):
        return {"success": True}
    raise HTTPException(status_code=500, detail="Error guardando market_data")


@app.post("/api/mt5/feedback", dependencies=[Depends(verify_key)])
def upload_feedback(feedback: FeedbackUpload):
    """Windows bridge sube feedback de un trade cerrado por el EA"""
    folder = Path(FEEDBACK_FOLDER)
    folder.mkdir(parents=True, exist_ok=True)

    filename = f"feedback_{feedback.signal_id}_{int(time.time())}.json"
    path = folder / filename

    data = {
        "signal_id": feedback.signal_id,
        "result":    feedback.result,
        "pips":      feedback.pips,
        "timestamp": feedback.timestamp or datetime.now().isoformat(),
    }

    if write_json(path, data):
        return {"success": True, "file": filename}
    raise HTTPException(status_code=500, detail="Error guardando feedback")


# ==============================
# STARTUP
# ==============================
@app.on_event("startup")
def on_startup():
    ensure_dirs()

    if not MAINTENANCE_FILE.exists():
        write_json(MAINTENANCE_FILE, {"enabled": False, "message": "", "since": None})

    print(f"[API] ========================================")
    print(f"[API] Trading Bot API iniciada")
    print(f"[API] Host:         http://{API_HOST}:{API_PORT}")
    print(f"[API] MT5 Exchange: {MT5_EXCHANGE}")
    print(f"[API] Docs:         http://{API_HOST}:{API_PORT}/docs")
    print(f"[API] ========================================")


# ==============================
# MAIN
# ==============================
if __name__ == "__main__":
    uvicorn.run(
        app,
        host=API_HOST,
        port=API_PORT,
        log_level="info",
    )

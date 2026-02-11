#!/usr/bin/env python3
"""
main.py v4.0 - BOT CON MACHINE LEARNING REAL

Sistema completo con:
- Aprendizaje automático
- 8+ estrategias
- Ajuste dinámico de parámetros
- Selección inteligente de estrategia
"""

import time
import os
import json
import sys
import logging
from datetime import datetime
from pathlib import Path

sys.path.append(os.path.dirname(__file__))


# ==============================
# STATUS DEL BOT
# ==============================
BOT_STATUS_FILE = "/home/travieso/.wine/drive_c/Program Files/MetaTrader 5/MQL5/Files/bot_status.json"

def write_bot_status(running: bool):
        data = {
            "running": running,
            "timestamp": int(time.time())
        }
        os.makedirs(os.path.dirname(BOT_STATUS_FILE), exist_ok=True)
        with open(BOT_STATUS_FILE, "w") as f:
            json.dump(data, f)
            f.flush()
            os.fsync(f.fileno())
        os.utime(BOT_STATUS_FILE, None)


# ==============================
# DEBUG JSON
# ==============================
DEBUG_FILE = Path(__file__).parent / "logs" / "debug.json"

def write_debug(level, message):
    entry = {
        "timestamp": datetime.now().isoformat(),
        "level": level,
        "message": message
    }

    DEBUG_FILE.parent.mkdir(exist_ok=True)

    if DEBUG_FILE.exists():
        try:
            with open(DEBUG_FILE, "r") as f:
                data = json.load(f)
                if not isinstance(data, list):
                    data = []
        except:
            data = []
    else:
        data = []

    data.append(entry)

    with open(DEBUG_FILE, "w") as f:
        json.dump(data, f, indent=2)


# ==============================
# LOGGING
# ==============================
def setup_logging():
    log_dir = Path(__file__).parent / "logs"
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / f"bot_{datetime.now().strftime('%Y%m%d')}.log"
    
    formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)
    
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)
    
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

logger = setup_logging()


# ==============================
# IMPORTS DEL BOT
# ==============================
try:
    from decision_engine.context_analyzer import analyze_market_context
    from decision_engine.signal_router import evaluate_signal
    from data_providers.mt5_reader import read_market_data
    logger.info("✅ Módulos principales cargados")
    write_debug("INFO", "Módulos principales cargados")
except Exception as e:
    logger.error(f"❌ Error cargando módulos: {e}")
    write_debug("ERROR", f"Error cargando módulos: {e}")
    sys.exit(1)


# Selector inteligente
try:
    from decision_engine.intelligent_selector import select_intelligent_strategy as select_setup
    logger.info("✅ Selector inteligente cargado")
    write_debug("INFO", "Selector inteligente cargado")
except:
    logger.warning("⚠️ Usando selector básico")
    write_debug("WARN", "Usando selector básico")
    from decision_engine.setup_selector import select_setup


# Sistema ML
try:
    from ml_adaptive_system import ml_auto_adjust, get_ml_status
    ML_AVAILABLE = True
    logger.info("✅ Sistema ML disponible")
    write_debug("INFO", "Sistema ML disponible")
except:
    ML_AVAILABLE = False
    logger.warning("⚠️ Sistema ML no disponible")
    write_debug("WARN", "Sistema ML no disponible")
    def ml_auto_adjust():
        return False
    def get_ml_status():
        return {"mode": "DISABLED"}


# Feedback
try:
    from feedback.feedback_processor import process_feedback, get_overall_stats
    logger.info("✅ Módulo de feedback cargado")
    write_debug("INFO", "Módulo de feedback cargado")
except Exception as e:
    logger.warning(f"⚠️ Feedback no disponible: {e}")
    write_debug("WARN", f"Feedback no disponible: {e}")
    def process_feedback():
        return False
    def get_overall_stats():
        return {"total_trades": 0, "total_wins": 0, "total_losses": 0, "win_rate": 0, "total_pips": 0}


# ==============================
# CONFIG
# ==============================
def load_config():
    config_file = "bot_config.json"
    
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
            logger.info(f"✅ Config cargada: min_conf={config.get('min_confidence')}%")
            write_debug("INFO", "Config cargada correctamente")
            return config
        except Exception as e:
            logger.warning(f"⚠️ Error leyendo config: {e}")
            write_debug("ERROR", f"Error leyendo config: {e}")
    
    logger.info("📄 Usando config por defecto")
    write_debug("INFO", "Usando configuración por defecto")
    return {
        "min_confidence": 35,
        "cooldown": 5,
        "max_daily_trades": 50,
        "max_losses": 5,
        "lot_size": 0.01,
        "start_hour": "00:00",
        "end_hour": "23:59"
    }


# ==============================
# GLOBALS
# ==============================
RUNNING = False
CONFIG = {}
last_trade_time = 0
consecutive_losses = 0
paused_until = 0
cycle_count = 0
signal_pending = False  # True cuando hay una señal activa esperando ejecución/cierre
signal_pending_since = 0  # Timestamp de cuándo se envió la señal
SIGNAL_PENDING_TIMEOUT = 300  # 5 minutos máximo esperando por un trade

SIGNAL_FILE_PATH = "/home/travieso/.wine/drive_c/Program Files/MetaTrader 5/MQL5/Files/signals/signal.json"
FEEDBACK_FILE_PATH = "/home/travieso/.wine/drive_c/Program Files/MetaTrader 5/MQL5/Files/trade_feedback.json"


def clear_signal_file():
    if os.path.exists(SIGNAL_FILE_PATH):
        try:
            os.remove(SIGNAL_FILE_PATH)
            logger.info("🗑️ signal.json eliminado")
            write_debug("INFO", "signal.json eliminado")
            return True
        except Exception as e:
            logger.error(f"❌ Error: {e}")
            write_debug("ERROR", f"Error eliminando signal.json: {e}")
            return False
    return True


def create_stop_signal():
    try:
        os.makedirs(os.path.dirname(SIGNAL_FILE_PATH), exist_ok=True)
        
        stop_signal = {
            "signal_id": f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_STOP",
            "action": "NONE",
            "confidence": 0.0,
            "sl_pips": 0,
            "tp_pips": 0,
            "symbol": "EURUSD",
            "timeframe": "M5",
            "timestamp": datetime.now().isoformat(),
            "setup_name": "SYSTEM_STOP",
            "reason": "Bot detenido"
        }
        
        with open(SIGNAL_FILE_PATH, "w") as f:
            json.dump(stop_signal, f, indent=4)
        
        logger.info("🛑 Señal STOP creada")
        write_debug("INFO", "Señal STOP creada")
        return True
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        write_debug("ERROR", f"Error creando señal STOP: {e}")
        return False


def run_cycle():
    global last_trade_time, consecutive_losses, paused_until, cycle_count
    global signal_pending, signal_pending_since

    cycle_count += 1

    logger.info("=" * 60)
    logger.info(f"🧠 Ciclo #{cycle_count}: {datetime.now()}")
    logger.info("=" * 60)
    write_debug("INFO", f"Ciclo #{cycle_count} iniciado")

    # SISTEMA ML
    if ML_AVAILABLE:
        try:
            if ml_auto_adjust():
                global CONFIG
                CONFIG = load_config()
                write_debug("INFO", "ML ajustó configuración")
        except Exception as e:
            logger.debug(f"ML adjust: {e}")
            write_debug("ERROR", f"ML adjust error: {e}")

    # FEEDBACK - siempre procesar (incluso si hay señal pendiente)
    try:
        if process_feedback():
            logger.info("📊 Feedback procesado - señal completada")
            write_debug("INFO", "Feedback procesado")
            signal_pending = False  # Trade cerrado, podemos generar nueva señal
            last_trade_time = time.time()  # Resetear cooldown desde cierre del trade
    except:
        pass

    # VERIFICAR SI HAY SEÑAL PENDIENTE (esperando ejecución/cierre)
    if signal_pending:
        elapsed = time.time() - signal_pending_since
        if elapsed < SIGNAL_PENDING_TIMEOUT:
            write_debug("INFO", f"Señal pendiente ({elapsed:.0f}s), esperando feedback...")
            return
        else:
            # Timeout - la señal no fue ejecutada o el feedback se perdió
            logger.warning(f"⚠️ Timeout de señal pendiente ({elapsed:.0f}s), reseteando")
            write_debug("WARN", "Timeout de señal pendiente")
            signal_pending = False
            clear_signal_file()

    # COOLDOWN - esperar entre trades
    cooldown = CONFIG.get("cooldown", 30)
    elapsed_since_trade = time.time() - last_trade_time
    if last_trade_time > 0 and elapsed_since_trade < cooldown:
        write_debug("INFO", f"Cooldown activo ({elapsed_since_trade:.0f}s/{cooldown}s)")
        return

    # MERCADO
    try:
        market_data = read_market_data()
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        write_debug("ERROR", f"Error leyendo mercado: {e}")
        return

    if not market_data:
        logger.warning("⏩ Sin datos")
        write_debug("WARN", "Sin datos de mercado")
        return

    # CONTEXTO
    try:
        context = analyze_market_context(market_data)
        write_debug("INFO", f"Contexto: {context}")
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        write_debug("ERROR", f"Error analizando contexto: {e}")
        return

    # SETUP
    try:
        setup = select_setup(context)
        write_debug("INFO", f"Setup seleccionado: {setup}")
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        write_debug("ERROR", f"Error seleccionando setup: {e}")
        return

    if not setup:
        logger.info("❌ NO SETUP")
        write_debug("WARN", "No se encontró setup")
        return

    # SEÑAL
    try:
        signal = evaluate_signal(setup["name"], context, market_data)
        write_debug("INFO", f"Resultado evaluate_signal: {signal}")
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        write_debug("ERROR", f"Error evaluando señal: {e}")
        return

    if signal is None:
        write_debug("WARN", "Signal = None")
        return

    if signal.get("action") == "NONE":
        write_debug("INFO", "Action NONE")
        return

    confidence = signal.get("confidence", 0)
    min_conf = CONFIG.get("min_confidence", 35) / 100.0
    # MODO EXPRORACION ML ----------------------ELIMINAR LUEGO DE QUE APRENDA
    if ML_AVAILABLE:
        ml_status = get_ml_status()
        total_ml_trades = ml_status.get("total_trades", 0)

        if total_ml_trades < 20:
            logger.info("MODO EXPLORACION ML ACTIVO (min_conf reducido a 10%)")
            min_conf = 0.10

    if confidence < min_conf:
        write_debug("WARN", f"Confianza insuficiente: {confidence}")
        return

    write_debug("OK", "SEÑAL VÁLIDA DETECTADA")
    signal_pending = True
    signal_pending_since = time.time()
    last_trade_time = time.time()


def start_bot():
    global RUNNING, paused_until, consecutive_losses, CONFIG, cycle_count
    
    CONFIG = load_config()
    
    RUNNING = True
    write_bot_status(True)
    write_debug("INFO", "Bot iniciado")
    paused_until = 0
    consecutive_losses = 0
    cycle_count = 0

    loop_interval = 5
    
    while RUNNING:
        write_bot_status(True)
        try:
            run_cycle()
            time.sleep(loop_interval)
        except KeyboardInterrupt:
            break
        except Exception as e:
            write_debug("ERROR", f"ERROR LOOP: {e}")
            time.sleep(5)

    write_bot_status(False)
    write_debug("INFO", "Bot detenido")
    clear_signal_file()
    create_stop_signal()


def stop_bot():
    global RUNNING
    RUNNING = False
    write_bot_status(False)
    write_debug("INFO", "Solicitud de parada")


if __name__ == "__main__":
    try:
        start_bot()
    except KeyboardInterrupt:
        stop_bot()
    except Exception as e:
        write_debug("CRITICAL", f"FATAL: {e}")
    finally:
        clear_signal_file()
        create_stop_signal()
        write_debug("INFO", "Proceso finalizado")

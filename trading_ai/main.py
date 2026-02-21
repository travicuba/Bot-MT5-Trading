#!/usr/bin/env python3
"""
main.py v5.0 - BOT INTELIGENTE MULTI-TRADE

Cambios principales:
- Multi-trade: abre varias operaciones simultaneas (configurable)
- Anti-spam: no repite misma estrategia+direccion en ventana de tiempo
- Anti-repeticion: detecta cuando repite la misma accion sin exito
- Senales inteligentes: varia estrategias entre trades abiertos
- El EA borra signal.json tras leer, asi Python sabe cuando enviar nueva
- Feedback por cola de archivos (soporta cierres masivos)
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
from mt5_paths import BOT_STATUS_FILE, SIGNAL_FILE as _SIGNAL_FILE_PATH, FEEDBACK_FILE_LEGACY as _FEEDBACK_FILE_PATH, ensure_dirs
ensure_dirs()

def write_bot_status(running: bool):
    min_conf_pct = CONFIG.get("min_confidence", 35) if CONFIG else 35
    max_concurrent = CONFIG.get("max_concurrent_trades", 3) if CONFIG else 3
    lot_size = CONFIG.get("lot_size", 0.01) if CONFIG else 0.01
    data = {
        "running": running,
        "timestamp": int(time.time()),
        "min_confidence": min_conf_pct / 100.0,
        "max_concurrent_trades": max_concurrent,
        "lot_size": lot_size
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

    # Mantener solo ultimas 500 entradas
    if len(data) > 500:
        data = data[-500:]

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
    logger.info("Modulos principales cargados")
    write_debug("INFO", "Modulos principales cargados")
except Exception as e:
    logger.error(f"Error cargando modulos: {e}")
    write_debug("ERROR", f"Error cargando modulos: {e}")
    sys.exit(1)


# Selector inteligente
try:
    from decision_engine.intelligent_selector import select_intelligent_strategy as select_setup
    logger.info("Selector inteligente cargado")
    write_debug("INFO", "Selector inteligente cargado")
except:
    logger.warning("Usando selector basico")
    write_debug("WARN", "Usando selector basico")
    from decision_engine.setup_selector import select_setup


# Sistema ML
try:
    from ml_adaptive_system import ml_auto_adjust, get_ml_status
    ML_AVAILABLE = True
    logger.info("Sistema ML disponible")
    write_debug("INFO", "Sistema ML disponible")
except:
    ML_AVAILABLE = False
    logger.warning("Sistema ML no disponible")
    write_debug("WARN", "Sistema ML no disponible")
    def ml_auto_adjust():
        return False
    def get_ml_status():
        return {"mode": "DISABLED"}


# Feedback
try:
    from feedback.feedback_processor import process_feedback, get_overall_stats
    logger.info("Modulo de feedback cargado")
    write_debug("INFO", "Modulo de feedback cargado")
except Exception as e:
    logger.warning(f"Feedback no disponible: {e}")
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
            logger.info(f"Config cargada: min_conf={config.get('min_confidence')}%")
            write_debug("INFO", "Config cargada correctamente")
            return config
        except Exception as e:
            logger.warning(f"Error leyendo config: {e}")
            write_debug("ERROR", f"Error leyendo config: {e}")

    logger.info("Usando config por defecto")
    write_debug("INFO", "Usando configuracion por defecto")
    return {
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
        "auto_optimize": True
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

SIGNAL_FILE_PATH = _SIGNAL_FILE_PATH
FEEDBACK_FILE_PATH = _FEEDBACK_FILE_PATH

# ==============================
# MULTI-TRADE TRACKING
# ==============================
# Senales activas: {signal_id: {strategy, direction, timestamp, context_snapshot}}
active_signals = {}

# Historial reciente de senales para anti-spam
# Lista de {strategy, direction, timestamp, signal_id}
recent_signals = []
MAX_RECENT_SIGNALS = 50

# Contador de repeticiones fallidas por estrategia
strategy_fail_count = {}


def get_active_count():
    """Numero de trades activos del bot"""
    return len(active_signals)


def add_active_signal(signal_id, strategy, direction, context):
    """Registrar nueva senal activa"""
    active_signals[signal_id] = {
        "strategy": strategy,
        "direction": direction,
        "timestamp": time.time(),
        "context_snapshot": {
            "trend": context.get("trend"),
            "volatility": context.get("volatility"),
            "market_regime": context.get("market_regime"),
            "rsi_state": context.get("rsi_state"),
        }
    }


def remove_active_signal(signal_id):
    """Eliminar senal activa (cuando recibimos feedback)"""
    if signal_id in active_signals:
        del active_signals[signal_id]


def add_recent_signal(strategy, direction, signal_id):
    """Registrar senal en historial reciente"""
    recent_signals.append({
        "strategy": strategy,
        "direction": direction,
        "timestamp": time.time(),
        "signal_id": signal_id
    })
    while len(recent_signals) > MAX_RECENT_SIGNALS:
        recent_signals.pop(0)


def cleanup_expired_signals():
    """Limpiar senales activas que expiraron (timeout de 10 min)"""
    timeout = 600
    now = time.time()
    expired = [sid for sid, data in active_signals.items()
               if now - data["timestamp"] > timeout]
    for sid in expired:
        logger.warning(f"Signal expirada (timeout): {sid}")
        write_debug("WARN", f"Signal expirada: {sid}")
        del active_signals[sid]


def is_signal_consumed():
    """
    Verifica si el EA ya consumio el signal.json (lo borra tras leer).
    Si no existe, significa que esta libre para recibir nueva senal.
    """
    return not os.path.exists(SIGNAL_FILE_PATH)


def is_strategy_spam(strategy, direction):
    """
    Verifica si estariamos haciendo spam con la misma estrategia+direccion.

    Reglas anti-spam:
    1. No repetir misma estrategia+direccion dentro de min_signal_interval
    2. No tener 2 trades activos con la misma estrategia+direccion
    3. Si una estrategia tiene 3+ fallos consecutivos, pausarla temporalmente
    """
    min_interval = CONFIG.get("min_signal_interval", 60)
    avoid_repeat = CONFIG.get("avoid_repeat_strategy", True)
    now = time.time()

    # Regla 1: No repetir misma estrategia+direccion dentro del intervalo
    for sig in reversed(recent_signals):
        age = now - sig["timestamp"]
        if age > min_interval:
            break
        if sig["strategy"] == strategy and sig["direction"] == direction:
            write_debug("INFO", f"Anti-spam: {strategy}/{direction} ya enviada hace {age:.0f}s")
            return True

    # Regla 2: No duplicar estrategia+direccion en trades activos
    if avoid_repeat:
        for sig_data in active_signals.values():
            if sig_data["strategy"] == strategy and sig_data["direction"] == direction:
                write_debug("INFO", f"Anti-spam: {strategy}/{direction} ya tiene trade activo")
                return True

    # Regla 3: Estrategia con muchos fallos consecutivos
    fail_key = f"{strategy}_{direction}"
    if strategy_fail_count.get(fail_key, 0) >= 3:
        last_fail_time = strategy_fail_count.get(f"{fail_key}_time", 0)
        if now - last_fail_time < 300:  # Pausa de 5 minutos
            write_debug("INFO", f"Anti-repeticion: {strategy}/{direction} pausada por fallos consecutivos")
            return True
        else:
            strategy_fail_count[fail_key] = 0

    return False


def update_strategy_fail_count(strategy, direction, result):
    """Actualizar contador de fallos por estrategia"""
    fail_key = f"{strategy}_{direction}"

    if result == "LOSS":
        strategy_fail_count[fail_key] = strategy_fail_count.get(fail_key, 0) + 1
        strategy_fail_count[f"{fail_key}_time"] = time.time()
    elif result == "WIN":
        strategy_fail_count[fail_key] = 0


def clear_signal_file():
    if os.path.exists(SIGNAL_FILE_PATH):
        try:
            os.remove(SIGNAL_FILE_PATH)
            logger.info("signal.json eliminado")
            write_debug("INFO", "signal.json eliminado")
            return True
        except Exception as e:
            logger.error(f"Error: {e}")
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

        logger.info("Senal STOP creada")
        write_debug("INFO", "Senal STOP creada")
        return True
    except Exception as e:
        logger.error(f"Error: {e}")
        write_debug("ERROR", f"Error creando senal STOP: {e}")
        return False


def run_cycle():
    global last_trade_time, consecutive_losses, paused_until, cycle_count

    cycle_count += 1

    if cycle_count % 12 == 0:
        logger.info("=" * 60)
        logger.info(f"Ciclo #{cycle_count}: {datetime.now()} | Activos: {get_active_count()}")
        logger.info("=" * 60)
    write_debug("INFO", f"Ciclo #{cycle_count} | Activos: {get_active_count()}")

    # SISTEMA ML
    global CONFIG
    if ML_AVAILABLE and CONFIG.get("auto_optimize", True):
        try:
            if ml_auto_adjust():
                CONFIG = load_config()
                write_debug("INFO", "ML ajusto configuracion")
        except Exception as e:
            logger.debug(f"ML adjust: {e}")
            write_debug("ERROR", f"ML adjust error: {e}")

    # FEEDBACK - siempre procesar (puede haber multiples)
    try:
        if process_feedback():
            logger.info("Feedback procesado")
            write_debug("INFO", "Feedback procesado")
            last_trade_time = time.time()
            _sync_active_with_feedback()
    except:
        pass

    # Limpiar senales expiradas
    cleanup_expired_signals()

    # VERIFICAR LIMITES
    max_concurrent = CONFIG.get("max_concurrent_trades", 3)
    active_count = get_active_count()

    if active_count >= max_concurrent:
        write_debug("INFO", f"Limite de trades concurrentes alcanzado ({active_count}/{max_concurrent})")
        return

    # Verificar si el EA ya consumio la senal anterior
    if not is_signal_consumed():
        write_debug("INFO", "signal.json aun existe, esperando a que EA la consuma")
        return

    # COOLDOWN
    cooldown = CONFIG.get("cooldown", 30)
    elapsed_since_trade = time.time() - last_trade_time
    if last_trade_time > 0 and elapsed_since_trade < cooldown:
        write_debug("INFO", f"Cooldown activo ({elapsed_since_trade:.0f}s/{cooldown}s)")
        return

    # MERCADO
    try:
        market_data = read_market_data()
    except Exception as e:
        logger.error(f"Error: {e}")
        write_debug("ERROR", f"Error leyendo mercado: {e}")
        return

    if not market_data:
        logger.warning("Sin datos")
        write_debug("WARN", "Sin datos de mercado")
        return

    # CONTEXTO
    try:
        context = analyze_market_context(market_data)
        write_debug("INFO", f"Contexto: trend={context.get('trend')} vol={context.get('volatility')} regime={context.get('market_regime')}")
    except Exception as e:
        logger.error(f"Error: {e}")
        write_debug("ERROR", f"Error analizando contexto: {e}")
        return

    # SETUP
    try:
        setup = select_setup(context)
        write_debug("INFO", f"Setup seleccionado: {setup}")
    except Exception as e:
        logger.error(f"Error: {e}")
        write_debug("ERROR", f"Error seleccionando setup: {e}")
        return

    if not setup:
        logger.info("NO SETUP disponible")
        write_debug("WARN", "No se encontro setup")
        return

    # SENAL
    try:
        signal = evaluate_signal(setup["name"], context, market_data)
        write_debug("INFO", f"Resultado evaluate_signal: {signal}")
    except Exception as e:
        logger.error(f"Error: {e}")
        write_debug("ERROR", f"Error evaluando senal: {e}")
        return

    if signal is None:
        write_debug("WARN", "Signal = None")
        return

    if signal.get("action") == "NONE":
        write_debug("INFO", "Action NONE")
        return

    confidence = signal.get("confidence", 0)
    min_conf = CONFIG.get("min_confidence", 35) / 100.0

    # MODO EXPLORACION ML
    if ML_AVAILABLE:
        ml_status = get_ml_status()
        total_ml_trades = ml_status.get("total_trades", 0)
        if total_ml_trades < 20:
            logger.info("MODO EXPLORACION ML ACTIVO (min_conf reducido a 10%)")
            min_conf = 0.10

    if confidence < min_conf:
        write_debug("WARN", f"Confianza insuficiente: {confidence:.2f} < {min_conf:.2f}")
        return

    # ANTI-SPAM
    strategy_name = setup["name"]
    direction = signal.get("action", "NONE")

    if is_strategy_spam(strategy_name, direction):
        write_debug("INFO", f"Anti-spam bloqueo: {strategy_name}/{direction}")
        return

    # SENAL VALIDA - registrar y enviar
    signal_id = signal.get("signal_id", "")

    write_debug("OK", f"SENAL VALIDA: {strategy_name}/{direction} conf={confidence:.2f}")

    add_active_signal(signal_id, strategy_name, direction, context)
    add_recent_signal(strategy_name, direction, signal_id)

    last_trade_time = time.time()

    logger.info(f"SENAL ENVIADA: {strategy_name} {direction} | Conf: {confidence:.2f} | Activos: {get_active_count()}/{max_concurrent}")


def _sync_active_with_feedback():
    """
    Sincronizar active_signals eliminando los que ya tienen feedback.
    """
    processed_file = "learning_data/processed_signals.txt"
    if not os.path.exists(processed_file):
        return

    try:
        with open(processed_file, "r") as f:
            processed = set(f.read().splitlines())
    except:
        return

    # Leer resultados recientes para contadores de fallo
    history_file = "learning_data/trade_history.json"
    recent_results = {}
    if os.path.exists(history_file):
        try:
            with open(history_file, "r") as f:
                history = json.load(f)
            for trade in history[-20:]:
                recent_results[trade.get("signal_id", "")] = trade.get("result", "")
        except:
            pass

    to_remove = []
    for signal_id, data in active_signals.items():
        if signal_id in processed:
            to_remove.append(signal_id)
            result = recent_results.get(signal_id, "")
            if result:
                update_strategy_fail_count(data["strategy"], data["direction"], result)

    for signal_id in to_remove:
        del active_signals[signal_id]
        write_debug("INFO", f"Signal sincronizada (feedback recibido): {signal_id}")


def start_bot():
    global RUNNING, paused_until, consecutive_losses, CONFIG, cycle_count

    CONFIG = load_config()

    RUNNING = True
    write_bot_status(True)
    write_debug("INFO", "Bot iniciado v5.0 - Multi-trade")
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

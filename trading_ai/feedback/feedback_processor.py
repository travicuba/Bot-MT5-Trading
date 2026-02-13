# feedback/feedback_processor.py

"""
Modulo de feedback v2.0 - SOPORTA COLA DE FEEDBACK

Cambios principales:
- Lee de carpeta trade_feedback/ (archivos individuales por trade)
- Procesa TODOS los feedbacks en un ciclo (cierres masivos)
- Mantiene compatibilidad con el archivo unico legacy
- Acumula historial completo sin limites
"""

import os
import json
import glob
from datetime import datetime


# Ruta legacy (archivo unico - compatibilidad)
FEEDBACK_FILE_LEGACY = "/home/travieso/.wine/drive_c/Program Files/MetaTrader 5/MQL5/Files/trade_feedback.json"

# Ruta nueva (carpeta con archivos individuales)
FEEDBACK_FOLDER = "/home/travieso/.wine/drive_c/Program Files/MetaTrader 5/MQL5/Files/trade_feedback"

STATS_FILE = "learning_data/setup_stats.json"
HISTORY_FILE = "learning_data/trade_history.json"
PROCESSED_SIGNALS_FILE = "learning_data/processed_signals.txt"


def is_already_processed(signal_id):
    """Verificar si una senal ya fue procesada"""
    if not os.path.exists(PROCESSED_SIGNALS_FILE):
        return False

    try:
        with open(PROCESSED_SIGNALS_FILE, "r") as f:
            processed = f.read().splitlines()
        return signal_id in processed
    except:
        return False


def mark_as_processed(signal_id):
    """Marcar una senal como procesada"""
    os.makedirs(os.path.dirname(PROCESSED_SIGNALS_FILE), exist_ok=True)

    try:
        with open(PROCESSED_SIGNALS_FILE, "a") as f:
            f.write(signal_id + "\n")
        return True
    except:
        return False


def load_stats():
    """Cargar estadisticas de setups"""
    if not os.path.exists(STATS_FILE):
        return {}

    try:
        with open(STATS_FILE, "r") as f:
            return json.load(f)
    except:
        return {}


def save_stats(stats):
    """Guardar estadisticas de setups"""
    os.makedirs(os.path.dirname(STATS_FILE), exist_ok=True)

    try:
        with open(STATS_FILE, "w") as f:
            json.dump(stats, f, indent=4)
        return True
    except Exception as e:
        print(f"Error guardando stats: {e}")
        return False


def load_history():
    """Cargar historial completo de trades"""
    if not os.path.exists(HISTORY_FILE):
        return []

    try:
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    except:
        return []


def save_history(history):
    """Guardar historial de trades SIN LIMITE"""
    os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)

    try:
        with open(HISTORY_FILE, "w") as f:
            json.dump(history, f, indent=4)
        return True
    except:
        return False


def _collect_feedback_files():
    """
    Recolecta todos los archivos de feedback pendientes.
    Soporta tanto la carpeta nueva como el archivo legacy.

    Returns:
        list: Lista de tuplas (filepath, feedback_dict)
    """
    pending = []

    # 1. Carpeta de feedback (nuevo sistema - archivos individuales)
    if os.path.isdir(FEEDBACK_FOLDER):
        pattern = os.path.join(FEEDBACK_FOLDER, "fb_*.json")
        for filepath in glob.glob(pattern):
            try:
                with open(filepath, "r") as f:
                    feedback = json.load(f)
                if "signal_id" in feedback and "result" in feedback:
                    pending.append((filepath, feedback))
            except Exception as e:
                print(f"Error leyendo {filepath}: {e}")
                # Archivo corrupto, eliminarlo
                try:
                    os.remove(filepath)
                except:
                    pass

    # 2. Archivo legacy (compatibilidad)
    if os.path.exists(FEEDBACK_FILE_LEGACY):
        try:
            with open(FEEDBACK_FILE_LEGACY, "r") as f:
                feedback = json.load(f)
            if "signal_id" in feedback and "result" in feedback:
                pending.append((FEEDBACK_FILE_LEGACY, feedback))
        except Exception as e:
            print(f"Error leyendo feedback legacy: {e}")
            try:
                os.remove(FEEDBACK_FILE_LEGACY)
            except:
                pass

    return pending


def _process_single_feedback(feedback):
    """
    Procesa un unico feedback y actualiza stats/historial.

    Returns:
        dict or None: El trade_record procesado, o None si fue ignorado
    """
    signal_id = feedback.get("signal_id", "")
    result = feedback.get("result", "")
    pips = feedback.get("pips", 0)

    # Ignorar trades manuales
    if not signal_id or signal_id.strip() == "":
        return None

    # Verificar si ya procesado
    if is_already_processed(signal_id):
        return None

    # Extraer setup del signal_id
    # Formato: YYYYMMDD_HHMMSS_ACTION_SETUP_NAME
    parts = signal_id.split("_")
    if len(parts) < 4:
        print(f"Signal ID formato incorrecto: {signal_id}")
        return None

    setup_name = "_".join(parts[3:])

    # Cargar estadisticas
    stats = load_stats()

    # Inicializar setup si no existe
    if setup_name not in stats:
        stats[setup_name] = {
            "wins": 0,
            "losses": 0,
            "total_pips": 0.0,
            "avg_win": 0.0,
            "avg_loss": 0.0,
            "total_trades": 0
        }

    # Actualizar estadisticas
    stats[setup_name]["total_trades"] = stats[setup_name].get("total_trades", 0) + 1

    if result == "WIN":
        stats[setup_name]["wins"] += 1
        old_avg = stats[setup_name].get("avg_win", 0.0)
        total_wins = stats[setup_name]["wins"]
        stats[setup_name]["avg_win"] = ((old_avg * (total_wins - 1)) + pips) / total_wins
    else:
        stats[setup_name]["losses"] += 1
        old_avg = stats[setup_name].get("avg_loss", 0.0)
        total_losses = stats[setup_name]["losses"]
        stats[setup_name]["avg_loss"] = ((old_avg * (total_losses - 1)) + abs(pips)) / total_losses

    stats[setup_name]["total_pips"] = stats[setup_name].get("total_pips", 0.0) + pips

    save_stats(stats)

    # Crear registro de trade
    trade_record = {
        "signal_id": signal_id,
        "setup": setup_name,
        "result": result,
        "pips": pips,
        "timestamp": feedback.get("timestamp", datetime.now().isoformat()),
        "processed_at": datetime.now().isoformat()
    }

    # Marcar como procesado
    mark_as_processed(signal_id)

    return trade_record


def process_feedback():
    """
    Procesar TODOS los feedbacks pendientes de MT5.

    Ahora lee de la carpeta trade_feedback/ (archivos individuales)
    y tambien del archivo legacy trade_feedback.json para compatibilidad.

    Procesa TODOS los archivos en un ciclo, resolviendo el bug de
    cierres masivos donde solo se registraba uno.

    Returns:
        bool: True si se proceso al menos un feedback, False si no
    """
    pending = _collect_feedback_files()

    if not pending:
        return False

    processed_count = 0
    history = load_history()

    for filepath, feedback in pending:
        trade_record = _process_single_feedback(feedback)

        if trade_record:
            history.append(trade_record)
            processed_count += 1

            print(f"FEEDBACK PROCESADO: {trade_record['setup']} "
                  f"| {trade_record['result']} | {trade_record['pips']:.2f} pips")

        # Eliminar archivo procesado
        try:
            os.remove(filepath)
        except:
            pass

    # Guardar historial una sola vez (eficiente para cierres masivos)
    if processed_count > 0:
        save_history(history)
        print(f"Total feedbacks procesados en este ciclo: {processed_count}")
        print(f"Historial total: {len(history)} trades")

    return processed_count > 0


def get_setup_performance(setup_name):
    """Obtener el performance de un setup especifico"""
    stats = load_stats()

    if setup_name not in stats:
        return {
            "win_rate": 0,
            "total_trades": 0,
            "profit_factor": 0,
            "exists": False
        }

    s = stats[setup_name]
    wins = s.get("wins", 0)
    losses = s.get("losses", 0)
    total = wins + losses

    win_rate = (wins / total * 100) if total > 0 else 0

    avg_win = s.get("avg_win", 0)
    avg_loss = s.get("avg_loss", 0)

    gross_profit = avg_win * wins
    gross_loss = avg_loss * losses

    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else 0

    return {
        "win_rate": win_rate,
        "total_trades": total,
        "profit_factor": profit_factor,
        "total_pips": s.get("total_pips", 0),
        "exists": True
    }


def get_overall_stats():
    """Obtener estadisticas generales de TODOS los setups ACUMULADOS"""
    stats = load_stats()

    total_wins = 0
    total_losses = 0
    total_pips = 0.0
    total_trades = 0

    for setup_name, s in stats.items():
        total_wins += s.get("wins", 0)
        total_losses += s.get("losses", 0)
        total_pips += s.get("total_pips", 0.0)
        total_trades += s.get("total_trades", 0)

    history = load_history()

    win_rate = (total_wins / total_trades * 100) if total_trades > 0 else 0

    return {
        "total_trades": total_trades,
        "total_wins": total_wins,
        "total_losses": total_losses,
        "win_rate": win_rate,
        "total_pips": total_pips,
        "history_count": len(history)
    }


def get_today_stats():
    """Obtener estadisticas solo del dia de hoy"""
    history = load_history()
    today = datetime.now().strftime("%Y-%m-%d")

    today_trades = [t for t in history if t.get("timestamp", "").startswith(today)]

    wins = sum(1 for t in today_trades if t.get("result") == "WIN")
    losses = sum(1 for t in today_trades if t.get("result") == "LOSS")
    total = len(today_trades)

    total_pips = sum(t.get("pips", 0) for t in today_trades)

    win_rate = (wins / total * 100) if total > 0 else 0

    return {
        "total_trades": total,
        "total_wins": wins,
        "total_losses": losses,
        "win_rate": win_rate,
        "total_pips": total_pips
    }


def reset_daily_stats():
    """Resetear estadisticas diarias (el historial completo se mantiene)"""
    pass


if __name__ == "__main__":
    print("TESTING FEEDBACK PROCESSOR v2.0")
    print("=" * 50)

    if process_feedback():
        print("\nFeedback procesado correctamente")
    else:
        print("\nNo hay feedback para procesar")

    print("\nESTADISTICAS TOTALES:")
    overall = get_overall_stats()
    print(f"Total Trades: {overall['total_trades']}")
    print(f"Wins: {overall['total_wins']}")
    print(f"Losses: {overall['total_losses']}")
    print(f"Win Rate: {overall['win_rate']:.2f}%")
    print(f"Total Pips: {overall['total_pips']:.2f}")
    print(f"Trades en historial: {overall['history_count']}")

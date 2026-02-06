# feedback/feedback_processor.py

"""
Módulo mejorado que ACUMULA el historial completo de trades
NO sobrescribe, sino que AGREGA al historial existente
"""

import os
import json
from datetime import datetime


FEEDBACK_FILE = "/home/travieso/.wine/drive_c/Program Files/MetaTrader 5/MQL5/Files/trade_feedback.json"
STATS_FILE = "learning_data/setup_stats.json"
HISTORY_FILE = "learning_data/trade_history.json"
PROCESSED_SIGNALS_FILE = "learning_data/processed_signals.txt"


def is_already_processed(signal_id):
    """
    Verificar si una señal ya fue procesada
    Para evitar procesar el mismo trade múltiples veces
    """
    if not os.path.exists(PROCESSED_SIGNALS_FILE):
        return False
    
    try:
        with open(PROCESSED_SIGNALS_FILE, "r") as f:
            processed = f.read().splitlines()
        return signal_id in processed
    except:
        return False


def mark_as_processed(signal_id):
    """Marcar una señal como procesada"""
    os.makedirs(os.path.dirname(PROCESSED_SIGNALS_FILE), exist_ok=True)
    
    try:
        with open(PROCESSED_SIGNALS_FILE, "a") as f:
            f.write(signal_id + "\n")
        return True
    except:
        return False


def load_stats():
    """Cargar estadísticas de setups"""
    if not os.path.exists(STATS_FILE):
        return {}
    
    try:
        with open(STATS_FILE, "r") as f:
            return json.load(f)
    except:
        return {}


def save_stats(stats):
    """Guardar estadísticas de setups"""
    os.makedirs(os.path.dirname(STATS_FILE), exist_ok=True)
    
    try:
        with open(STATS_FILE, "w") as f:
            json.dump(stats, f, indent=4)
        return True
    except Exception as e:
        print(f"❌ Error guardando stats: {e}")
        return False


def load_history():
    """Cargar historial completo de trades (TODOS, no solo últimos 100)"""
    if not os.path.exists(HISTORY_FILE):
        return []
    
    try:
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    except:
        return []


def save_history(history):
    """Guardar historial de trades SIN LÍMITE"""
    os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
    
    try:
        with open(HISTORY_FILE, "w") as f:
            json.dump(history, f, indent=4)
        return True
    except:
        return False


def process_feedback():
    """
    Procesar feedback de MT5 y actualizar estadísticas ACUMULATIVAS
    
    Returns:
        bool: True si se procesó nuevo feedback, False si no
    """
    
    # Verificar que existe el archivo de feedback
    if not os.path.exists(FEEDBACK_FILE):
        return False
    
    try:
        # Leer feedback
        with open(FEEDBACK_FILE, "r") as f:
            feedback = json.load(f)
        
        # Verificar que tiene los campos necesarios
        if "signal_id" not in feedback or "result" not in feedback:
            print("⚠️ Feedback incompleto")
            return False
        
        signal_id = feedback["signal_id"]
        result = feedback["result"]  # WIN o LOSS
        pips = feedback.get("pips", 0)
        
        # NUEVO: Verificar si ya fue procesado
        if is_already_processed(signal_id):
            print(f"ℹ️ Señal {signal_id} ya fue procesada anteriormente, ignorando...")
            # Eliminar el archivo feedback para que no siga intentando
            try:
                os.remove(FEEDBACK_FILE)
            except:
                pass
            return False
        
        # Extraer el setup del signal_id
        parts = signal_id.split("_")
        if len(parts) < 4:
            print(f"⚠️ Signal ID con formato incorrecto: {signal_id}")
            return False
        
        setup_name = "_".join(parts[3:])
        
        # Cargar estadísticas actuales
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
        
        # ACTUALIZAR ESTADÍSTICAS (ACUMULATIVO)
        stats[setup_name]["total_trades"] = stats[setup_name].get("total_trades", 0) + 1
        
        if result == "WIN":
            stats[setup_name]["wins"] += 1
            
            # Actualizar avg_win
            old_avg = stats[setup_name].get("avg_win", 0.0)
            total_wins = stats[setup_name]["wins"]
            stats[setup_name]["avg_win"] = ((old_avg * (total_wins - 1)) + pips) / total_wins
            
        else:  # LOSS
            stats[setup_name]["losses"] += 1
            
            # Actualizar avg_loss
            old_avg = stats[setup_name].get("avg_loss", 0.0)
            total_losses = stats[setup_name]["losses"]
            stats[setup_name]["avg_loss"] = ((old_avg * (total_losses - 1)) + abs(pips)) / total_losses
        
        # Actualizar total pips
        stats[setup_name]["total_pips"] = stats[setup_name].get("total_pips", 0.0) + pips
        
        # Guardar estadísticas
        if not save_stats(stats):
            print("❌ No se pudo guardar stats")
            return False
        
        # AGREGAR AL HISTORIAL (NO SOBRESCRIBIR)
        history = load_history()
        
        trade_record = {
            "signal_id": signal_id,
            "setup": setup_name,
            "result": result,
            "pips": pips,
            "timestamp": feedback.get("timestamp", datetime.now().isoformat()),
            "processed_at": datetime.now().isoformat()
        }
        
        history.append(trade_record)
        
        # NUEVO: NO LIMITAR, guardar TODOS los trades
        save_history(history)
        
        # Marcar como procesado
        mark_as_processed(signal_id)
        
        # Log del procesamiento
        total_today = stats[setup_name]["total_trades"]
        print(f"✅ FEEDBACK PROCESADO:")
        print(f"   Setup: {setup_name}")
        print(f"   Result: {result}")
        print(f"   Pips: {pips:.2f}")
        print(f"   Stats del setup: {stats[setup_name]['wins']}W / {stats[setup_name]['losses']}L ({total_today} trades totales)")
        print(f"   Total en historial: {len(history)} trades")
        
        # Borrar el archivo de feedback
        try:
            os.remove(FEEDBACK_FILE)
            print("📄 trade_feedback.json eliminado (procesado)")
        except:
            pass
        
        return True
        
    except Exception as e:
        print(f"❌ Error procesando feedback: {e}")
        import traceback
        traceback.print_exc()
        return False


def get_setup_performance(setup_name):
    """
    Obtener el performance de un setup específico
    """
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
    """
    Obtener estadísticas generales de TODOS los setups ACUMULADOS
    """
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
    
    # También contar desde el historial para verificar
    history = load_history()
    
    win_rate = (total_wins / total_trades * 100) if total_trades > 0 else 0
    
    return {
        "total_trades": total_trades,
        "total_wins": total_wins,
        "total_losses": total_losses,
        "win_rate": win_rate,
        "total_pips": total_pips,
        "history_count": len(history)  # Para verificar consistencia
    }


def get_today_stats():
    """
    Obtener estadísticas solo del día de hoy
    """
    history = load_history()
    today = datetime.now().strftime("%Y-%m-%d")
    
    today_trades = [t for t in history if t.get("timestamp", "").startswith(today)]
    
    wins = sum(1 for t in today_trades if t["result"] == "WIN")
    losses = sum(1 for t in today_trades if t["result"] == "LOSS")
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
    """
    Resetear estadísticas para un nuevo día
    (Opcional - llamar a las 00:00 si quieres stats por día)
    """
    # NO eliminar el historial, solo las stats del día
    # El historial completo se mantiene
    pass


# Función de testing
if __name__ == "__main__":
    print("🧪 TESTING FEEDBACK PROCESSOR")
    print("=" * 50)
    
    # Procesar feedback si existe
    if process_feedback():
        print("\n✅ Feedback procesado correctamente")
    else:
        print("\n⚠️ No hay feedback para procesar")
    
    # Mostrar estadísticas generales
    print("\n📊 ESTADÍSTICAS TOTALES:")
    overall = get_overall_stats()
    print(f"Total Trades: {overall['total_trades']}")
    print(f"Wins: {overall['total_wins']}")
    print(f"Losses: {overall['total_losses']}")
    print(f"Win Rate: {overall['win_rate']:.2f}%")
    print(f"Total Pips: {overall['total_pips']:.2f}")
    print(f"Trades en historial: {overall['history_count']}")
    
    # Mostrar estadísticas de hoy
    print("\n📅 ESTADÍSTICAS DE HOY:")
    today = get_today_stats()
    print(f"Total Trades: {today['total_trades']}")
    print(f"Wins: {today['total_wins']}")
    print(f"Losses: {today['total_losses']}")
    print(f"Win Rate: {today['win_rate']:.2f}%")
    print(f"Total Pips: {today['total_pips']:.2f}")
    
    # Mostrar performance por setup
    print("\n📈 PERFORMANCE POR SETUP:")
    stats = load_stats()
    for setup_name in stats.keys():
        perf = get_setup_performance(setup_name)
        print(f"\n{setup_name}:")
        print(f"  Win Rate: {perf['win_rate']:.2f}%")
        print(f"  Total Trades: {perf['total_trades']}")
        print(f"  Profit Factor: {perf['profit_factor']:.2f}")
        print(f"  Total Pips: {perf['total_pips']:.2f}")

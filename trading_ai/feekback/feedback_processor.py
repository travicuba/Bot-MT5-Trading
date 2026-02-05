# feedback/feedback_processor.py

"""
Módulo para procesar feedback de trades desde MT5 y actualizar learning data
Este módulo se ejecuta en cada ciclo para leer resultados de trades cerrados
"""

import os
import json
from datetime import datetime


FEEDBACK_FILE = "/home/travieso/.wine/drive_c/Program Files/MetaTrader 5/MQL5/Files/trade_feedback.json"
STATS_FILE = "learning_data/setup_stats.json"
HISTORY_FILE = "learning_data/trade_history.json"


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
    """Cargar historial completo de trades"""
    if not os.path.exists(HISTORY_FILE):
        return []
    
    try:
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    except:
        return []


def save_history(history):
    """Guardar historial de trades"""
    os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
    
    try:
        with open(HISTORY_FILE, "w") as f:
            json.dump(history, f, indent=4)
        return True
    except:
        return False


def process_feedback():
    """
    Procesar feedback de MT5 y actualizar estadísticas
    
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
        
        # Extraer el setup del signal_id
        # Formato: "20260205_200526_SELL_TREND_FOLLOWING"
        parts = signal_id.split("_")
        if len(parts) < 4:
            print(f"⚠️ Signal ID con formato incorrecto: {signal_id}")
            return False
        
        # El setup es la parte después de BUY/SELL
        setup_name = "_".join(parts[3:])
        
        # Cargar estadísticas actuales
        stats = load_stats()
        
        # Inicializar setup si no existe
        if setup_name not in stats:
            stats[setup_name] = {
                "wins": 0,
                "losses": 0,
                "total_pips": 0,
                "avg_win": 0,
                "avg_loss": 0
            }
        
        # Actualizar estadísticas
        if result == "WIN":
            stats[setup_name]["wins"] += 1
            
            # Actualizar avg_win
            old_avg = stats[setup_name].get("avg_win", 0)
            total_wins = stats[setup_name]["wins"]
            stats[setup_name]["avg_win"] = ((old_avg * (total_wins - 1)) + pips) / total_wins
            
        else:  # LOSS
            stats[setup_name]["losses"] += 1
            
            # Actualizar avg_loss
            old_avg = stats[setup_name].get("avg_loss", 0)
            total_losses = stats[setup_name]["losses"]
            stats[setup_name]["avg_loss"] = ((old_avg * (total_losses - 1)) + abs(pips)) / total_losses
        
        # Actualizar total pips
        stats[setup_name]["total_pips"] = stats[setup_name].get("total_pips", 0) + pips
        
        # Guardar estadísticas
        if not save_stats(stats):
            print("❌ No se pudo guardar stats")
            return False
        
        # Agregar al historial
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
        
        # Mantener solo últimos 100 trades
        if len(history) > 100:
            history = history[-100:]
        
        save_history(history)
        
        # Log del procesamiento
        print(f"✅ FEEDBACK PROCESADO:")
        print(f"   Setup: {setup_name}")
        print(f"   Result: {result}")
        print(f"   Pips: {pips:.2f}")
        print(f"   Stats actualizadas: {stats[setup_name]['wins']}W / {stats[setup_name]['losses']}L")
        
        # Borrar el archivo de feedback para evitar procesarlo de nuevo
        try:
            os.remove(FEEDBACK_FILE)
            print("📄 trade_feedback.json eliminado (procesado)")
        except:
            pass
        
        return True
        
    except Exception as e:
        print(f"❌ Error procesando feedback: {e}")
        return False


def get_setup_performance(setup_name):
    """
    Obtener el performance de un setup específico
    
    Args:
        setup_name: Nombre del setup
    
    Returns:
        dict con win_rate, total_trades, profit_factor
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
    
    # Profit factor = (avg_win * wins) / (avg_loss * losses)
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
    Obtener estadísticas generales de todos los setups
    
    Returns:
        dict con total_trades, total_wins, total_losses, win_rate, total_pips
    """
    stats = load_stats()
    
    total_wins = 0
    total_losses = 0
    total_pips = 0
    
    for setup_name, s in stats.items():
        total_wins += s.get("wins", 0)
        total_losses += s.get("losses", 0)
        total_pips += s.get("total_pips", 0)
    
    total_trades = total_wins + total_losses
    win_rate = (total_wins / total_trades * 100) if total_trades > 0 else 0
    
    return {
        "total_trades": total_trades,
        "total_wins": total_wins,
        "total_losses": total_losses,
        "win_rate": win_rate,
        "total_pips": total_pips
    }


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
    print("\n📊 ESTADÍSTICAS GENERALES:")
    overall = get_overall_stats()
    print(f"Total Trades: {overall['total_trades']}")
    print(f"Wins: {overall['total_wins']}")
    print(f"Losses: {overall['total_losses']}")
    print(f"Win Rate: {overall['win_rate']:.2f}%")
    print(f"Total Pips: {overall['total_pips']:.2f}")
    
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

import time
import os
from datetime import datetime

from decision_engine.context_analyzer import analyze_market_context
from decision_engine.setup_selector import select_setup
from decision_engine.signal_router import evaluate_signal
from data_providers.mt5_reader import read_market_data

# NUEVO: Importar feedback processor
import sys
sys.path.append(os.path.dirname(__file__))

try:
    from feedback.feedback_processor import process_feedback, get_overall_stats
except:
    # Si no existe el módulo, crear funciones dummy
    def process_feedback():
        return False
    def get_overall_stats():
        return {"total_trades": 0, "total_wins": 0, "total_losses": 0, "win_rate": 0, "total_pips": 0}

RUNNING = False

# ==============================
# CONFIG
# ==============================
LOOP_INTERVAL_SECONDS = 10
RUNNING = True

# RUTAS DE ARCHIVOS
SIGNAL_FILE_PATH = "/home/travieso/.wine/drive_c/Program Files/MetaTrader 5/MQL5/Files/signals/signal.json"

# PROTECCIONES
MAX_DAILY_TRADES = 20
COOLDOWN_SECONDS = 60
MAX_CONSECUTIVE_LOSSES = 3
PAUSE_AFTER_LOSSES_MINUTES = 30
MIN_CONFIDENCE_THRESHOLD = 0.75

# Variables de control
last_trade_time = 0
consecutive_losses = 0
paused_until = 0


def clear_signal_file():
    """
    Elimina el archivo signal.json para que el EA no opere con señales viejas
    """
    if os.path.exists(SIGNAL_FILE_PATH):
        try:
            os.remove(SIGNAL_FILE_PATH)
            print("🗑️ signal.json eliminado correctamente")
            return True
        except Exception as e:
            print(f"❌ Error eliminando signal.json: {e}")
            return False
    else:
        print("ℹ️ signal.json no existe (ya estaba limpio)")
        return True


def create_stop_signal():
    """
    Crea un signal.json con acción NONE para indicar al EA que no opere
    """
    try:
        # Crear directorio si no existe
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
            "reason": "Bot detenido por el usuario"
        }
        
        import json
        with open(SIGNAL_FILE_PATH, "w") as f:
            json.dump(stop_signal, f, indent=4)
        
        print("🛑 Señal de STOP escrita para el EA")
        return True
        
    except Exception as e:
        print(f"❌ Error creando señal de stop: {e}")
        return False


# ==============================
# UN CICLO DE DECISIÓN
# ==============================
def run_cycle():
    global last_trade_time, consecutive_losses, paused_until
    
    print("\n==============================")
    print("🧠 Nuevo ciclo:", datetime.now())
    print("==============================")

    # PROCESAR FEEDBACK DE TRADES CERRADOS
    if process_feedback():
        print("📊 Feedback procesado y estadísticas actualizadas")
    
    # VERIFICAR PROTECCIONES
    current_time = time.time()
    if paused_until > current_time:
        remaining = int((paused_until - current_time) / 60)
        print(f"⏸️ BOT EN PAUSA por pérdidas consecutivas (faltan {remaining} min)")
        return
    
    # Verificar cooldown entre trades
    if last_trade_time > 0:
        time_since_last = current_time - last_trade_time
        if time_since_last < COOLDOWN_SECONDS:
            remaining = int(COOLDOWN_SECONDS - time_since_last)
            print(f"⏳ Cooldown activo: esperando {remaining}s antes del próximo trade")
            return
    
    # Verificar máximo de trades diarios
    stats = get_overall_stats()
    if stats["total_trades"] >= MAX_DAILY_TRADES:
        print(f"🛑 LÍMITE DIARIO ALCANZADO: {stats['total_trades']} trades")
        print("   El bot se reactivará mañana")
        return
    
    # Mostrar estadísticas actuales
    if stats["total_trades"] > 0:
        print(f"📊 Stats del día: {stats['total_wins']}W / {stats['total_losses']}L | WR: {stats['win_rate']:.1f}% | Pips: {stats['total_pips']:.2f}")

    # INPUT DE MERCADO
    market_data = read_market_data()
    
    if not market_data:
        print("⏩ No hay datos de mercado, ciclo omitido")
        return

    # CONTEXTO
    context = analyze_market_context(market_data)
    print("📊 CONTEXTO:", context)

    # SELECCIÓN DE SETUP
    setup = select_setup(context)

    if not setup:
        print("❌ NO SETUP → no se genera señal")
        return

    print("🧠 SETUP SELECCIONADO:", setup["name"], f"(score: {setup['score']:.2f})")

    # EVALUAR SEÑAL
    signal = evaluate_signal(setup["name"], context, market_data)

    if signal is None:
        print("⚠️ SIGNAL = None → no se escribió signal.json")
        return

    if signal.get("action") == "NONE":
        print("ℹ️ Acción NONE → MT5 no debe operar")
        return
    
    # VERIFICAR CONFIANZA MÍNIMA
    confidence = signal.get("confidence", 0)
    if confidence < MIN_CONFIDENCE_THRESHOLD:
        print(f"⚠️ Confianza {confidence:.2%} < {MIN_CONFIDENCE_THRESHOLD:.2%} → señal rechazada")
        print("   Esperando oportunidad con mayor confianza...")
        return

    # LOG FINAL
    print("📈 SIGNAL FINAL:")
    print(f"   Action: {signal['action']}")
    print(f"   Confidence: {confidence:.2%}")
    print(f"   SL/TP: {signal.get('sl_pips')}/{signal.get('tp_pips')} pips")
    print(f"   Reason: {signal.get('reason', 'N/A')}")
    print("✅ Señal lista para ser leída por MT5")
    
    # Actualizar tiempo del último trade
    last_trade_time = current_time


# ==============================
# LOOP AUTÓNOMO
# ==============================
def start_bot():
    global RUNNING, paused_until, consecutive_losses
    RUNNING = True
    paused_until = 0
    consecutive_losses = 0
    
    print("🚀 BOT INICIADO")
    print(f"⚙️ CONFIGURACIÓN:")
    print(f"   Intervalo de análisis: {LOOP_INTERVAL_SECONDS}s")
    print(f"   Cooldown entre trades: {COOLDOWN_SECONDS}s")
    print(f"   Máximo trades/día: {MAX_DAILY_TRADES}")
    print(f"   Confianza mínima: {MIN_CONFIDENCE_THRESHOLD:.0%}")
    print(f"   Max pérdidas consecutivas: {MAX_CONSECUTIVE_LOSSES}")
    
    # IMPORTANTE: Limpiar señales viejas al iniciar
    print("\n🧹 Limpiando señales antiguas...")
    clear_signal_file()

    while RUNNING:
        try:
            run_cycle()
            time.sleep(LOOP_INTERVAL_SECONDS)
        except Exception as e:
            print("❌ ERROR :", e)
            import traceback
            traceback.print_exc()
            time.sleep(5)

    print("🧯 BOT DETENIDO")
    
    # CRÍTICO: Al detener, eliminar signal.json y crear señal STOP
    print("\n🛑 Deteniendo sistema de trading...")
    print("   1. Eliminando señales antiguas...")
    clear_signal_file()
    print("   2. Creando señal de STOP para el EA...")
    create_stop_signal()
    print("✅ Sistema detenido correctamente")
    
    
def stop_bot():
    global RUNNING
    print("\n⏹️ Solicitando detención del bot...")
    RUNNING = False


# ==============================
# ENTRY POINT
# ==============================
if __name__ == "__main__":
    try:
        start_bot()
    except KeyboardInterrupt:
        print("\n\n⌨️ Ctrl+C detectado - Deteniendo bot...")
        stop_bot()
    finally:
        # Asegurar limpieza al salir
        print("\n🧹 Limpieza final...")
        clear_signal_file()
        create_stop_signal()
        print("👋 Bot cerrado completamente")

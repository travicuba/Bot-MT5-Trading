import time
from datetime import datetime

from decision_engine.context_analyzer import analyze_market_context
from decision_engine.setup_selector import select_setup
from decision_engine.signal_router import evaluate_signal
from data_providers.mt5_reader import read_market_data

# NUEVO: Importar feedback processor
import sys
import os
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
LOOP_INTERVAL_SECONDS = 10   # cada cuántos segundos piensa el bot
RUNNING = True               # flag de control (GUI lo usará luego)

# ======== NUEVO: PROTECCIONES ========
MAX_DAILY_TRADES = 20        # Máximo de trades por día
COOLDOWN_SECONDS = 60        # Segundos entre trades (1 minuto)
MAX_CONSECUTIVE_LOSSES = 3   # Máximo de pérdidas consecutivas antes de pausar
PAUSE_AFTER_LOSSES_MINUTES = 30  # Minutos de pausa después de muchas pérdidas
MIN_CONFIDENCE_THRESHOLD = 0.75  # Confianza mínima aumentada

# Variables de control
last_trade_time = 0
consecutive_losses = 0
paused_until = 0


# ==============================
# UN CICLO DE DECISIÓN
# ==============================
def run_cycle():
    global last_trade_time, consecutive_losses, paused_until
    
    print("\n==============================")
    print("🧠 Nuevo ciclo:", datetime.now())
    print("==============================")

    # ------------------------------------------------------------------
    # NUEVO: PROCESAR FEEDBACK DE TRADES CERRADOS
    # ------------------------------------------------------------------
    if process_feedback():
        print("📊 Feedback procesado y estadísticas actualizadas")
    
    # ------------------------------------------------------------------
    # NUEVO: VERIFICAR PROTECCIONES
    # ------------------------------------------------------------------
    
    # Verificar si estamos en pausa
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

    # ------------------------------------------------------------------
    # 1. INPUT DE MERCADO (luego vendrá de MT5 / CSV / API)
    # ------------------------------------------------------------------
    market_data = read_market_data()
    
    if not market_data:
        print("⏩ No hay datos de mercado, ciclo omitido")
        return

    # ------------------------------------------------------------------
    # 2. CONTEXTO
    # ------------------------------------------------------------------
    context = analyze_market_context(market_data)
    print("📊 CONTEXTO:", context)

    # ------------------------------------------------------------------
    # 3. SELECCIÓN DE SETUP
    # ------------------------------------------------------------------
    setup = select_setup(context)

    if not setup:
        print("❌ NO SETUP → no se genera señal")
        return

    print("🧠 SETUP SELECCIONADO:", setup["name"], f"(score: {setup['score']:.2f})")

    # ------------------------------------------------------------------
    # 4. EVALUAR SEÑAL (ÚNICO PUNTO DE ESCRITURA)
    # ------------------------------------------------------------------
    signal = evaluate_signal(setup["name"], context, market_data)

    if signal is None:
        print("⚠️ SIGNAL = None → no se escribió signal.json")
        return

    if signal.get("action") == "NONE":
        print("ℹ️ Acción NONE → MT5 no debe operar")
        return
    
    # ------------------------------------------------------------------
    # NUEVO: VERIFICAR CONFIANZA MÍNIMA (MÁS ESTRICTO)
    # ------------------------------------------------------------------
    confidence = signal.get("confidence", 0)
    if confidence < MIN_CONFIDENCE_THRESHOLD:
        print(f"⚠️ Confianza {confidence:.2%} < {MIN_CONFIDENCE_THRESHOLD:.2%} → señal rechazada")
        print("   Esperando oportunidad con mayor confianza...")
        return

    # ------------------------------------------------------------------
    # 5. LOG FINAL
    # ------------------------------------------------------------------
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
    
def stop_bot():
    global RUNNING
    RUNNING = False


# ==============================
# ENTRY POINT
# ==============================
if __name__ == "__main__":
    start_bot()

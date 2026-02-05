import time
from datetime import datetime

from decision_engine.context_analyzer import analyze_market_context
from decision_engine.setup_selector import select_setup
from decision_engine.signal_router import evaluate_signal
from data_providers.mt5_reader import read_market_data
from decision_engine.setup_selector import select_setup

RUNNING = False

# ==============================
# CONFIG
# ==============================
LOOP_INTERVAL_SECONDS = 10   # cada cuántos segundos piensa el bot
RUNNING = True               # flag de control (GUI lo usará luego)


# ==============================
# UN CICLO DE DECISIÓN
# ==============================
def run_cycle():
    print("\n==============================")
    print("🧠 Nuevo ciclo:", datetime.now())
    print("==============================")

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

    print("🧠 SETUP SELECCIONADO:", setup["name"])

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
    # 5. LOG FINAL
    # ------------------------------------------------------------------
    print("📈 SIGNAL FINAL:")
    print(signal)
    print("✅ Señal lista para ser leída por MT5")


# ==============================
# LOOP AUTÓNOMO
# ==============================
def start_bot():
    global RUNNING
    RUNNING = True
    print("🚀 BOT INICIADO")

    while RUNNING:
        try:
            run_cycle()
            time.sleep(LOOP_INTERVAL_SECONDS)
        except Exception as e:
            print("❌ ERROR :", e)
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
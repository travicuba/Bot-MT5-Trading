"""
bingx_gui.py — Panel completo de BingX Perpetual Futures (REAL, sin demo)

Tabs:
  1. Dashboard     — Stats de cuenta + mercado + controles del bot (estilo MT5)
  2. Posiciones    — Posiciones abiertas en tiempo real desde la API
  3. Estadísticas  — Métricas acumuladas de rendimiento
  4. Historial     — Historial de trades locales
  5. Aprendizaje   — Sistema de aprendizaje y análisis de rendimiento
  6. Configuración — Parámetros de estrategia y operación
  7. Sistema       — Info técnica y diagnóstico
"""

import json
import os
import sys
import threading
import time
from datetime import datetime

import tkinter as tk
from tkinter import ttk, messagebox


# ──────────────────────────────────────────────────────────────────────────────
# Rutas de archivos — siempre desde bingx_paths (NUNCA compartir con MT5)
# ──────────────────────────────────────────────────────────────────────────────

_DIR = os.path.dirname(os.path.abspath(__file__))

try:
    from bingx_paths import (
        BINGX_CONFIG_FILE  as BINGX_CFG,
        BINGX_STATS_FILE   as BINGX_STATS,
        BINGX_HISTORY_FILE as BINGX_HISTORY,
        BINGX_STATUS_FILE  as BINGX_STATUS,
        ensure_dirs        as _bingx_ensure_dirs,
    )
    _bingx_ensure_dirs()
except ImportError:
    BINGX_CFG     = os.path.join(_DIR, "bingx_config.json")
    BINGX_STATS   = os.path.join(_DIR, "bingx_stats.json")
    BINGX_HISTORY = os.path.join(_DIR, "bingx_history.json")
    BINGX_STATUS  = os.path.join(_DIR, "bingx_status.json")

# ──────────────────────────────────────────────────────────────────────────────
# Matplotlib (opcional)
# ──────────────────────────────────────────────────────────────────────────────
try:
    import matplotlib
    matplotlib.use("TkAgg")
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    HAS_MPL = True
except ImportError:
    HAS_MPL = False

# ──────────────────────────────────────────────────────────────────────────────
# Paleta de colores (dark theme)
# ──────────────────────────────────────────────────────────────────────────────
BG_DARK   = "#0a0e27"
BG_PANEL  = "#151b3d"
BG_WIDGET = "#1e2749"
BG_ENTRY  = "#252d55"
FG_TEXT   = "#e0e6ff"
FG_MUTED  = "#8b9dc3"
C_BLUE    = "#4895ef"
C_GREEN   = "#06ffa5"
C_RED     = "#ff006e"
C_YELLOW  = "#ffbe0b"
C_ORANGE  = "#ff9a00"
C_PURPLE  = "#7b5ea7"

# ──────────────────────────────────────────────────────────────────────────────
# Rutas de archivos — siempre desde bingx_paths (NUNCA compartir con MT5)
# ──────────────────────────────────────────────────────────────────────────────
try:
    from bingx_paths import (
        BINGX_CONFIG_FILE  as BINGX_CFG,
        BINGX_STATS_FILE   as BINGX_STATS,
        BINGX_HISTORY_FILE as BINGX_HISTORY,
        BINGX_STATUS_FILE  as BINGX_STATUS,
        ensure_dirs        as _bingx_ensure_dirs,
    )
    _bingx_ensure_dirs()
except ImportError:
    _DIR          = os.path.dirname(os.path.abspath(__file__))
    BINGX_CFG     = os.path.join(_DIR, "bingx_config.json")
    BINGX_STATS   = os.path.join(_DIR, "bingx_stats.json")
    BINGX_HISTORY = os.path.join(_DIR, "bingx_history.json")
    BINGX_STATUS  = os.path.join(_DIR, "bingx_status.json")

BINGX_DEFAULTS = {
    # Credenciales (gestionadas en Settings global)
    "api_key":          "",
    "api_secret":       "",
    "default_symbol":   "BTC-USDT",
    "default_leverage": 10,
    "margin_type":      "ISOLATED",
    "risk_percent":     1.0,
    "max_positions":    3,
    "max_daily_trades": 20,
    "max_losses":       3,
    # Estrategia (gestionados en pestaña Configuración del bot)
    "timeframe":        "15m",
    "ema_short":        9,
    "ema_long":         21,
    "rsi_period":       14,
    "rsi_overbought":   70,
    "rsi_oversold":     30,
    "atr_sl_mult":      1.5,
    "atr_tp_mult":      3.0,
    "cooldown":         60,
    "min_confidence":   30,
}

STATS_DEFAULTS = {
    "total_trades": 0, "wins": 0, "losses": 0,
    "total_pnl": 0.0, "win_rate": 0.0,
    "best_trade": 0.0, "worst_trade": 0.0,
    "current_streak": 0, "streak_type": "—",
}

# ──────────────────────────────────────────────────────────────────────────────
# Helpers de I/O
# ──────────────────────────────────────────────────────────────────────────────

def _load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(default, dict):
                out = dict(default)
                out.update(data)
                return out
            return data
        except Exception:
            pass
    return dict(default) if isinstance(default, dict) else default


def _save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


# ──────────────────────────────────────────────────────────────────────────────
# Widget helper: fila label / valor
# ──────────────────────────────────────────────────────────────────────────────

def _info_row(parent, row, label, value="—", value_fg=None):
    tk.Label(
        parent, text=label,
        bg=BG_PANEL, fg=FG_MUTED,
        font=("Consolas", 9), anchor="w",
    ).grid(row=row, column=0, sticky="w", padx=(0, 12), pady=2)
    var = tk.StringVar(value=value)
    tk.Label(
        parent, textvariable=var,
        bg=BG_PANEL, fg=value_fg or FG_TEXT,
        font=("Consolas", 9, "bold"), anchor="w",
    ).grid(row=row, column=1, sticky="w", pady=2)
    return var


# ══════════════════════════════════════════════════════════════════════════════
# Clase principal
# ══════════════════════════════════════════════════════════════════════════════

class BingXPanel(tk.Frame):
    """Panel completo de BingX Perpetual Futures — trading real."""

    VERSION = "4.0.0"

    def __init__(self, parent, root, on_home=None):
        super().__init__(parent, bg=BG_DARK)
        self.root    = root
        self.on_home = on_home

        # Estado de conexión
        self._client       = None
        self._conn_status  = "DISCONNECTED"
        self._balance_data = {}
        self._uid          = "—"
        self._positions    = []

        # Estado del bot
        self.bot_state      = "STOPPED"
        self._bot_thread    = None
        self._daily_trades  = 0
        self._consec_losses = 0

        # Config y stats
        self.cfg   = _load_json(BINGX_CFG,  BINGX_DEFAULTS)
        self.stats = _load_json(BINGX_STATS, STATS_DEFAULTS)

        self._build_ui()
        self._start_clock()
        self._start_auto_update()

        # Auto-conectar si hay credenciales
        if self.cfg.get("api_key") and self.cfg.get("api_secret"):
            self.after(500, self._connect_api)

    # ──────────────────────────────────────────
    # UI principal
    # ──────────────────────────────────────────

    def _build_ui(self):
        # Barra superior
        top = tk.Frame(self, bg=BG_PANEL, height=48)
        top.pack(fill="x", side="top")
        top.pack_propagate(False)

        if self.on_home:
            tk.Button(
                top, text="← Inicio",
                bg=BG_WIDGET, fg=FG_MUTED,
                font=("Consolas", 9), bd=0, padx=10,
                activebackground=BG_WIDGET, activeforeground=FG_TEXT,
                cursor="hand2", relief="flat",
                command=self.on_home,
            ).pack(side="left", padx=8, pady=8)

        tk.Label(
            top, text="⚡  BingX Perpetual Futures",
            bg=BG_PANEL, fg=FG_TEXT,
            font=("Consolas", 12, "bold"),
        ).pack(side="left", padx=8)

        self._conn_dot   = tk.Label(top, text="●", bg=BG_PANEL, fg=C_RED,  font=("Consolas", 14))
        self._conn_dot.pack(side="right", padx=(0, 6), pady=8)
        self._conn_label = tk.Label(top, text="Desconectado", bg=BG_PANEL, fg=FG_MUTED, font=("Consolas", 9))
        self._conn_label.pack(side="right", pady=8)

        self._clock_lbl = tk.Label(top, text="", bg=BG_PANEL, fg=FG_MUTED, font=("Consolas", 9))
        self._clock_lbl.pack(side="right", padx=16, pady=8)

        # Notebook
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("BX.TNotebook",
                         background=BG_DARK, borderwidth=0, tabmargins=[0, 0, 0, 0])
        style.configure("BX.TNotebook.Tab",
                         background=BG_WIDGET, foreground=FG_MUTED,
                         font=("Consolas", 9, "bold"), padding=[14, 6], borderwidth=0)
        style.map("BX.TNotebook.Tab",
                  background=[("selected", BG_PANEL)],
                  foreground=[("selected", C_BLUE)])

        self._nb = ttk.Notebook(self, style="BX.TNotebook")
        self._nb.pack(fill="both", expand=True)

        self._build_tab_dashboard()
        self._build_tab_positions()
        self._build_tab_stats()
        self._build_tab_history()
        self._build_tab_learning()
        self._build_tab_config()
        self._build_tab_system()

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 1 — Dashboard
    # ══════════════════════════════════════════════════════════════════════════

    def _make_stat_box(self, parent, label, value="—", color=None):
        """Crea un bloque de estadística 2x2 al estilo MT5."""
        f = tk.Frame(parent, bg=BG_WIDGET, padx=10, pady=8)
        tk.Label(f, text=label, bg=BG_WIDGET, fg=FG_MUTED,
                 font=("Consolas", 8)).pack(anchor="w")
        var = tk.StringVar(value=value)
        tk.Label(f, textvariable=var, bg=BG_WIDGET, fg=color or FG_TEXT,
                 font=("Consolas", 17, "bold")).pack(anchor="w")
        return f, var

    def _build_tab_dashboard(self):
        tab = tk.Frame(self._nb, bg=BG_DARK)
        self._nb.add(tab, text="  Dashboard  ")

        # ══════════════════════════════════════════════════════════════════════
        # HEADER — conexión + bot + controles
        # ══════════════════════════════════════════════════════════════════════
        header = tk.Frame(tab, bg=BG_PANEL, height=110)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Frame(header, bg=C_ORANGE, height=2).pack(fill="x", side="bottom")

        # ── Bloque izquierdo: estado de conexión ──
        conn_blk = tk.Frame(header, bg=BG_PANEL)
        conn_blk.pack(side="left", padx=20, pady=10)

        conn_top = tk.Frame(conn_blk, bg=BG_PANEL)
        conn_top.pack(anchor="w")

        self._big_dot    = tk.Label(conn_top, text="●", bg=BG_PANEL, fg=C_RED, font=("Consolas", 22))
        self._big_dot.pack(side="left")
        self._big_status = tk.Label(conn_top, text="DESCONECTADO", bg=BG_PANEL, fg=C_RED,
                                    font=("Consolas", 13, "bold"))
        self._big_status.pack(side="left", padx=8)

        conn_bot = tk.Frame(conn_blk, bg=BG_PANEL)
        conn_bot.pack(anchor="w", pady=(6, 0))

        self._reconnect_btn = tk.Button(
            conn_bot, text="Conectar API",
            bg=C_BLUE, fg="white",
            font=("Consolas", 9, "bold"), bd=0,
            padx=12, pady=4, cursor="hand2", relief="flat",
            command=self._connect_api,
        )
        self._reconnect_btn.pack(side="left")

        self._v_uid    = tk.StringVar(value="UID: —")
        self._v_conn_t = tk.StringVar(value="")
        tk.Label(conn_bot, textvariable=self._v_uid,
                 bg=BG_PANEL, fg=FG_MUTED, font=("Consolas", 9)).pack(side="left", padx=12)
        tk.Label(conn_bot, textvariable=self._v_conn_t,
                 bg=BG_PANEL, fg=FG_MUTED, font=("Consolas", 8)).pack(side="left")

        # ── Separador central ──
        tk.Frame(header, bg=BG_WIDGET, width=1).pack(side="left", fill="y", pady=16)

        # ── Bloque central: bot ──
        bot_blk = tk.Frame(header, bg=BG_PANEL)
        bot_blk.pack(side="left", padx=20, pady=10)

        bot_top = tk.Frame(bot_blk, bg=BG_PANEL)
        bot_top.pack(anchor="w")
        self._bot_dot = tk.Label(bot_top, text="●", bg=BG_PANEL, fg=C_RED, font=("Consolas", 22))
        self._bot_dot.pack(side="left")
        self._bot_lbl = tk.Label(bot_top, text="DETENIDO", bg=BG_PANEL, fg=C_RED,
                                 font=("Consolas", 13, "bold"))
        self._bot_lbl.pack(side="left", padx=8)

        bot_bot = tk.Frame(bot_blk, bg=BG_PANEL)
        bot_bot.pack(anchor="w", pady=(6, 0))

        self._start_btn = tk.Button(
            bot_bot, text="▶  INICIAR BOT",
            bg=BG_WIDGET, fg=FG_MUTED,
            font=("Consolas", 10, "bold"), bd=0,
            padx=14, pady=5, cursor="hand2", relief="flat",
            command=self._start_bot, state="disabled",
        )
        self._start_btn.pack(side="left", padx=(0, 6))

        self._stop_btn = tk.Button(
            bot_bot, text="◼  DETENER",
            bg=BG_WIDGET, fg=FG_MUTED,
            font=("Consolas", 10, "bold"), bd=0,
            padx=14, pady=5, cursor="hand2", relief="flat",
            command=self._stop_bot, state="disabled",
        )
        self._stop_btn.pack(side="left")

        # ── Separador ──
        tk.Frame(header, bg=BG_WIDGET, width=1).pack(side="left", fill="y", pady=16)

        # ── Bloque derecho: info de bot ──
        info_blk = tk.Frame(header, bg=BG_PANEL)
        info_blk.pack(side="left", padx=20, pady=12, fill="y")

        ig = tk.Frame(info_blk, bg=BG_PANEL)
        ig.pack(expand=True)
        self._v_sym_bot  = _info_row(ig, 0, "Símbolo:")
        self._v_lev_bot  = _info_row(ig, 1, "Apalancamiento:")
        self._v_risk_bot = _info_row(ig, 2, "Riesgo/trade:")
        self._v_trades_d = _info_row(ig, 3, "Trades hoy:")

        # ── Última señal (header derecha) ──
        sig_blk = tk.Frame(header, bg=BG_PANEL)
        sig_blk.pack(side="right", padx=20, pady=12)
        tk.Label(sig_blk, text="ÚLTIMA SEÑAL", bg=BG_PANEL, fg=FG_MUTED,
                 font=("Consolas", 8)).pack(anchor="e")
        self._v_signal = tk.StringVar(value="—")
        tk.Label(sig_blk, textvariable=self._v_signal, bg=BG_PANEL, fg=C_YELLOW,
                 font=("Consolas", 11, "bold")).pack(anchor="e")

        # ══════════════════════════════════════════════════════════════════════
        # MAIN — panel izquierdo + log derecho
        # ══════════════════════════════════════════════════════════════════════
        main = tk.Frame(tab, bg=BG_DARK)
        main.pack(fill="both", expand=True, padx=8, pady=6)

        # ── Panel izquierdo (ancho fijo 430px) ──
        left = tk.Frame(main, bg=BG_DARK, width=430)
        left.pack(side="left", fill="y", padx=(0, 6))
        left.pack_propagate(False)

        # ┌ Stats de cuenta 2×2 ──────────────────────────────────────────────┐
        acc_lf = tk.LabelFrame(left, text=" ▦ CUENTA ",
                               bg=BG_PANEL, fg=C_BLUE,
                               font=("Consolas", 9, "bold"), bd=1, relief="solid")
        acc_lf.pack(fill="x", pady=(0, 4))

        acc_grid = tk.Frame(acc_lf, bg=BG_PANEL)
        acc_grid.pack(fill="x", padx=8, pady=6)
        acc_grid.columnconfigure(0, weight=1)
        acc_grid.columnconfigure(1, weight=1)

        bx0, self._v_bal    = self._make_stat_box(acc_grid, "Balance (USDT)",    color=C_GREEN)
        bx1, self._v_equity = self._make_stat_box(acc_grid, "Equity (USDT)")
        bx2, self._v_avail  = self._make_stat_box(acc_grid, "Margen disponible")
        bx3, self._v_upnl   = self._make_stat_box(acc_grid, "PnL no realizado",  color=C_YELLOW)
        bx0.grid(row=0, column=0, sticky="ew", padx=(0, 4), pady=(0, 4))
        bx1.grid(row=0, column=1, sticky="ew", pady=(0, 4))
        bx2.grid(row=1, column=0, sticky="ew", padx=(0, 4))
        bx3.grid(row=1, column=1, sticky="ew")

        # ┌ Stats de trading 2×2 ─────────────────────────────────────────────┐
        trd_lf = tk.LabelFrame(left, text=" ▦ ESTADÍSTICAS RÁPIDAS ",
                               bg=BG_PANEL, fg=C_BLUE,
                               font=("Consolas", 9, "bold"), bd=1, relief="solid")
        trd_lf.pack(fill="x", pady=(0, 4))

        trd_grid = tk.Frame(trd_lf, bg=BG_PANEL)
        trd_grid.pack(fill="x", padx=8, pady=6)
        trd_grid.columnconfigure(0, weight=1)
        trd_grid.columnconfigure(1, weight=1)

        bt0, self._sv_trades = self._make_stat_box(trd_grid, "Total Trades",   color=C_BLUE)
        bt1, self._sv_wins   = self._make_stat_box(trd_grid, "Ganadas",        color=C_GREEN)
        bt2, self._sv_losses = self._make_stat_box(trd_grid, "Perdidas",       color=C_RED)
        bt3, self._sv_wr     = self._make_stat_box(trd_grid, "Win Rate",       color=C_YELLOW)
        bt0.grid(row=0, column=0, sticky="ew", padx=(0, 4), pady=(0, 4))
        bt1.grid(row=0, column=1, sticky="ew", pady=(0, 4))
        bt2.grid(row=1, column=0, sticky="ew", padx=(0, 4))
        bt3.grid(row=1, column=1, sticky="ew")

        # Inicializar stats
        self._sv_trades.set(str(self.stats.get("total_trades", 0)))
        self._sv_wins.set(str(self.stats.get("wins", 0)))
        self._sv_losses.set(str(self.stats.get("losses", 0)))
        self._sv_wr.set(f"{self.stats.get('win_rate', 0):.1f}%")

        # ┌ Mercado actual ────────────────────────────────────────────────────┐
        mkt_lf = tk.LabelFrame(left, text=" ◐ MERCADO ACTUAL ",
                               bg=BG_PANEL, fg=C_ORANGE,
                               font=("Consolas", 9, "bold"), bd=1, relief="solid")
        mkt_lf.pack(fill="x", pady=(0, 4))

        mg = tk.Frame(mkt_lf, bg=BG_PANEL)
        mg.pack(fill="x", padx=12, pady=6)
        self._v_symbol  = _info_row(mg, 0, "Símbolo:")
        self._v_price   = _info_row(mg, 1, "Precio:",      value_fg=C_BLUE)
        self._v_change  = _info_row(mg, 2, "Cambio 24h:")
        self._v_vol24   = _info_row(mg, 3, "Volumen 24h:")
        self._v_funding = _info_row(mg, 4, "Financiamiento:")
        self._v_margin  = _info_row(mg, 5, "Margen usado:")

        # ┌ Última señal (texto) ──────────────────────────────────────────────┐
        sig_lf = tk.LabelFrame(left, text=" ◉ ÚLTIMA SEÑAL ",
                               bg=BG_PANEL, fg=C_GREEN,
                               font=("Consolas", 9, "bold"), bd=1, relief="solid")
        sig_lf.pack(fill="x", pady=(0, 4))

        self._sig_text = tk.Text(
            sig_lf, bg=BG_WIDGET, fg=FG_TEXT,
            font=("Consolas", 9), height=5,
            state="disabled", bd=0, padx=6, pady=4, wrap="word",
        )
        self._sig_text.pack(fill="x", padx=8, pady=6)

        # ┌ Panel de análisis IA ──────────────────────────────────────────────┐
        ai_lf = tk.LabelFrame(left, text=" 🤖 ANÁLISIS IA ",
                              bg=BG_PANEL, fg=C_ORANGE,
                              font=("Consolas", 9, "bold"), bd=1, relief="solid")
        ai_lf.pack(fill="both", expand=True, pady=(0, 0))

        self._ai_text = tk.Text(
            ai_lf, bg=BG_WIDGET, fg=FG_TEXT,
            font=("Consolas", 8), height=7,
            state="disabled", bd=0, padx=6, pady=4, wrap="word",
        )
        self._ai_text.tag_configure("green",  foreground=C_GREEN)
        self._ai_text.tag_configure("red",    foreground=C_RED)
        self._ai_text.tag_configure("yellow", foreground=C_YELLOW)
        self._ai_text.tag_configure("blue",   foreground=C_BLUE)
        self._ai_text.tag_configure("muted",  foreground=FG_MUTED)
        self._ai_text.pack(fill="both", expand=True, padx=8, pady=6)
        self._ai_rsi = 50.0
        self._ai_atr = 0.0
        self._ai_trend = "—"

        # ── Panel derecho: log ───────────────────────────────────────────────
        right = tk.Frame(main, bg=BG_DARK)
        right.pack(side="right", fill="both", expand=True)

        log_lf = tk.LabelFrame(right, text=" ▤ LOGS DEL SISTEMA ",
                               bg=BG_PANEL, fg=FG_MUTED,
                               font=("Consolas", 9, "bold"), bd=1, relief="solid")
        log_lf.pack(fill="both", expand=True)

        log_tb = tk.Frame(log_lf, bg=BG_PANEL, height=28)
        log_tb.pack(fill="x", padx=8, pady=(4, 0))
        log_tb.pack_propagate(False)

        tk.Button(
            log_tb, text="× Limpiar",
            bg=C_RED, fg="white",
            font=("Consolas", 8, "bold"), bd=0,
            padx=8, pady=2, cursor="hand2", relief="flat",
            command=self._clear_log,
        ).pack(side="right")

        self._log_widget = tk.Text(
            log_lf,
            bg=BG_WIDGET, fg=C_GREEN,
            font=("Consolas", 9),
            state="disabled", wrap="word", bd=0, padx=6, pady=6,
            height=25,
        )
        vsb = ttk.Scrollbar(log_lf, command=self._log_widget.yview)
        self._log_widget.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self._log_widget.pack(fill="both", expand=True, padx=(8, 0), pady=(2, 8))

        for tag, color in [
            ("ok",    C_GREEN),  ("err",   C_RED),
            ("warn",  C_YELLOW), ("info",  C_BLUE),
            ("dim",   FG_MUTED), ("trade", C_ORANGE),
        ]:
            self._log_widget.tag_configure(tag, foreground=color)

    def _clear_log(self):
        self._log_widget.config(state="normal")
        self._log_widget.delete("1.0", "end")
        self._log_widget.config(state="disabled")

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 2 — Posiciones
    # ══════════════════════════════════════════════════════════════════════════

    def _build_tab_positions(self):
        tab = tk.Frame(self._nb, bg=BG_DARK)
        self._nb.add(tab, text="  Posiciones  ")

        tb = tk.Frame(tab, bg=BG_PANEL, height=40)
        tb.pack(fill="x", padx=8, pady=(8, 0))
        tb.pack_propagate(False)

        tk.Button(
            tb, text="↻  Actualizar",
            bg=C_BLUE, fg="white",
            font=("Consolas", 9, "bold"), bd=0,
            padx=12, pady=4, cursor="hand2", relief="flat",
            command=self._refresh_positions,
        ).pack(side="left", padx=8, pady=6)

        tk.Button(
            tb, text="✕  Cerrar seleccionada",
            bg=C_RED, fg="white",
            font=("Consolas", 9, "bold"), bd=0,
            padx=12, pady=4, cursor="hand2", relief="flat",
            command=self._close_selected_position,
        ).pack(side="left", padx=4, pady=6)

        self._pos_count_lbl = tk.Label(
            tb, text="0 posiciones abiertas",
            bg=BG_PANEL, fg=FG_MUTED, font=("Consolas", 9),
        )
        self._pos_count_lbl.pack(side="right", padx=12)

        cols = ("symbol", "side", "qty", "entry", "mark", "upnl", "lev", "margin", "liq")
        self._pos_tree = ttk.Treeview(tab, columns=cols, show="headings")
        self._style_treeview(self._pos_tree)

        hdrs = {
            "symbol": "Símbolo", "side": "Lado",   "qty": "Cantidad",
            "entry":  "Entrada", "mark": "Precio", "upnl": "PnL no real.",
            "lev":    "Apalancam.", "margin": "Margen", "liq": "Liquidación",
        }
        wids = {"symbol": 110, "side": 60, "qty": 90, "entry": 110, "mark": 110,
                "upnl": 100, "lev": 80, "margin": 90, "liq": 110}

        for c in cols:
            self._pos_tree.heading(c, text=hdrs[c])
            self._pos_tree.column(c,  width=wids[c], anchor="center")

        vsb = ttk.Scrollbar(tab, orient="vertical",   command=self._pos_tree.yview)
        hsb = ttk.Scrollbar(tab, orient="horizontal", command=self._pos_tree.xview)
        self._pos_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        hsb.pack(side="bottom", fill="x", padx=8)
        vsb.pack(side="right",  fill="y", pady=(4, 0))
        self._pos_tree.pack(fill="both", expand=True, padx=(8, 0), pady=4)

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 3 — Estadísticas
    # ══════════════════════════════════════════════════════════════════════════

    def _build_tab_stats(self):
        tab = tk.Frame(self._nb, bg=BG_DARK)
        self._nb.add(tab, text="  Estadísticas  ")

        metrics = tk.LabelFrame(
            tab, text=" RENDIMIENTO ",
            bg=BG_PANEL, fg=C_BLUE,
            font=("Consolas", 9, "bold"), bd=1, relief="solid",
        )
        metrics.pack(fill="x", padx=8, pady=8)
        g = tk.Frame(metrics, bg=BG_PANEL)
        g.pack(fill="x", padx=12, pady=8)

        self._sv = {}
        for i, (key, lbl) in enumerate([
            ("total_trades", "Total trades:"),
            ("wins",         "Ganancias:"),
            ("losses",       "Pérdidas:"),
            ("win_rate",     "Win rate:"),
            ("total_pnl",    "PnL total (USDT):"),
            ("best_trade",   "Mejor trade (USDT):"),
            ("worst_trade",  "Peor trade (USDT):"),
            ("streak",       "Racha actual:"),
        ]):
            self._sv[key] = _info_row(g, i, lbl)

        if HAS_MPL:
            chart_f = tk.LabelFrame(
                tab, text=" CURVA DE EQUIDAD ",
                bg=BG_PANEL, fg=C_GREEN,
                font=("Consolas", 9, "bold"), bd=1, relief="solid",
            )
            chart_f.pack(fill="both", expand=True, padx=8, pady=(0, 8))
            self._fig    = Figure(figsize=(6, 3), dpi=90, facecolor=BG_PANEL)
            self._ax     = self._fig.add_subplot(111, facecolor=BG_DARK)
            self._canvas = FigureCanvasTkAgg(self._fig, master=chart_f)
            self._canvas.get_tk_widget().pack(fill="both", expand=True)
            self._draw_empty_chart()

        self._update_stats_tab()

    def _draw_empty_chart(self):
        if not HAS_MPL:
            return
        self._ax.clear()
        self._ax.set_facecolor(BG_DARK)
        self._ax.tick_params(colors=FG_MUTED, labelsize=7)
        for spine in self._ax.spines.values():
            spine.set_color(BG_WIDGET)
        self._ax.set_xlabel("Trade #", color=FG_MUTED, fontsize=8)
        self._ax.set_ylabel("PnL acumulado (USDT)", color=FG_MUTED, fontsize=8)
        self._ax.set_title("Sin datos aún", color=FG_MUTED, fontsize=9)
        self._fig.tight_layout()
        self._canvas.draw()

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 4 — Historial
    # ══════════════════════════════════════════════════════════════════════════

    def _build_tab_history(self):
        tab = tk.Frame(self._nb, bg=BG_DARK)
        self._nb.add(tab, text="  Historial  ")

        tb = tk.Frame(tab, bg=BG_PANEL, height=40)
        tb.pack(fill="x", padx=8, pady=(8, 0))
        tb.pack_propagate(False)

        tk.Button(
            tb, text="↻  Actualizar",
            bg=C_BLUE, fg="white",
            font=("Consolas", 9, "bold"), bd=0,
            padx=12, pady=4, cursor="hand2", relief="flat",
            command=self._load_history_tab,
        ).pack(side="left", padx=8, pady=6)

        tk.Button(
            tb, text="🗑  Limpiar",
            bg=BG_WIDGET, fg=FG_MUTED,
            font=("Consolas", 9, "bold"), bd=0,
            padx=12, pady=4, cursor="hand2", relief="flat",
            command=self._clear_history,
        ).pack(side="left", padx=4, pady=6)

        cols = ("ts", "symbol", "dir", "qty", "entry", "exit", "pnl", "result", "strategy")
        self._hist_tree = ttk.Treeview(tab, columns=cols, show="headings")
        self._style_treeview(self._hist_tree)
        self._hist_tree.tag_configure("WIN",  background="#0d2b1a", foreground=C_GREEN)
        self._hist_tree.tag_configure("LOSS", background="#2b0d17", foreground=C_RED)
        self._hist_tree.tag_configure("OPEN", background="#1a1a0d", foreground=C_YELLOW)

        hdrs = {
            "ts": "Fecha/Hora", "symbol": "Símbolo", "dir": "Dirección",
            "qty": "Cantidad",  "entry":  "Entrada",  "exit": "Salida",
            "pnl": "PnL USDT", "result": "Resultado", "strategy": "Estrategia",
        }
        wids = {"ts": 140, "symbol": 100, "dir": 70, "qty": 80,
                "entry": 100, "exit": 100, "pnl": 90, "result": 80, "strategy": 130}

        for c in cols:
            self._hist_tree.heading(c, text=hdrs[c])
            self._hist_tree.column(c, width=wids[c], anchor="center")

        vsb = ttk.Scrollbar(tab, orient="vertical",   command=self._hist_tree.yview)
        hsb = ttk.Scrollbar(tab, orient="horizontal", command=self._hist_tree.xview)
        self._hist_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        hsb.pack(side="bottom", fill="x", padx=8)
        vsb.pack(side="right",  fill="y", pady=(4, 0))
        self._hist_tree.pack(fill="both", expand=True, padx=(8, 0), pady=4)

        self._load_history_tab()

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 5 — Configuración
    # ══════════════════════════════════════════════════════════════════════════

    def _build_tab_learning(self):
        """Sistema de aprendizaje — analiza el historial para mostrar insights."""
        tab = tk.Frame(self._nb, bg=BG_DARK)
        self._nb.add(tab, text="  Aprendizaje  ")

        # Toolbar
        tb = tk.Frame(tab, bg=BG_PANEL, height=36)
        tb.pack(fill="x", padx=8, pady=(8, 0))
        tb.pack_propagate(False)
        tk.Label(tb, text="⚙  Sistema de Aprendizaje Adaptativo",
                 bg=BG_PANEL, fg=C_BLUE, font=("Consolas", 9, "bold")).pack(side="left", padx=10, pady=8)
        tk.Button(
            tb, text="↻  Analizar",
            bg=C_BLUE, fg="white",
            font=("Consolas", 9, "bold"), bd=0,
            padx=12, pady=4, cursor="hand2", relief="flat",
            command=self._run_learning_analysis,
        ).pack(side="right", padx=8, pady=6)

        # Contenido en dos columnas
        main = tk.Frame(tab, bg=BG_DARK)
        main.pack(fill="both", expand=True, padx=8, pady=6)

        left = tk.Frame(main, bg=BG_DARK)
        right = tk.Frame(main, bg=BG_DARK)
        left.pack(side="left", fill="both", expand=True, padx=(0, 4))
        right.pack(side="right", fill="both", expand=True, padx=(4, 0))

        # ── Panel de rendimiento por señal ────────────────────────────────────
        sig_f = tk.LabelFrame(left, text=" RENDIMIENTO POR SEÑAL ",
                              bg=BG_PANEL, fg=C_ORANGE,
                              font=("Consolas", 9, "bold"), bd=1, relief="solid")
        sig_f.pack(fill="x", pady=(0, 6))

        sg = tk.Frame(sig_f, bg=BG_PANEL)
        sg.pack(fill="x", padx=12, pady=8)
        self._lv = {}
        for i, (key, lbl) in enumerate([
            ("buy_trades",    "Trades LONG:"),
            ("buy_wr",        "Win Rate LONG:"),
            ("buy_pnl",       "PnL LONG (USDT):"),
            ("sell_trades",   "Trades SHORT:"),
            ("sell_wr",       "Win Rate SHORT:"),
            ("sell_pnl",      "PnL SHORT (USDT):"),
        ]):
            self._lv[key] = _info_row(sg, i, lbl)

        # ── Panel de calidad de señal ─────────────────────────────────────────
        qa_f = tk.LabelFrame(left, text=" CALIDAD Y ADAPTACIÓN ",
                             bg=BG_PANEL, fg=C_GREEN,
                             font=("Consolas", 9, "bold"), bd=1, relief="solid")
        qa_f.pack(fill="x", pady=(0, 6))

        qg = tk.Frame(qa_f, bg=BG_PANEL)
        qg.pack(fill="x", padx=12, pady=8)
        for i, (key, lbl) in enumerate([
            ("confidence",    "Confianza actual:"),
            ("best_hour",     "Mejor hora del día:"),
            ("worst_hour",    "Peor hora del día:"),
            ("avg_duration",  "Duración media trade:"),
            ("recommend",     "Recomendación:"),
        ]):
            self._lv[key] = _info_row(qg, i, lbl)

        # ── Últimos 10 trades ────────────────────────────────────────────────
        rec_f = tk.LabelFrame(right, text=" ÚLTIMOS 10 TRADES ",
                              bg=BG_PANEL, fg=C_BLUE,
                              font=("Consolas", 9, "bold"), bd=1, relief="solid")
        rec_f.pack(fill="x", pady=(0, 6))

        cols = ("ts", "dir", "pnl", "result")
        self._learn_tree = ttk.Treeview(rec_f, columns=cols, show="headings", height=10)
        self._style_treeview(self._learn_tree)
        self._learn_tree.tag_configure("WIN",  foreground=C_GREEN)
        self._learn_tree.tag_configure("LOSS", foreground=C_RED)

        for c, h, w in [
            ("ts", "Hora", 120), ("dir", "Dirección", 80),
            ("pnl", "PnL USDT", 90), ("result", "Resultado", 80),
        ]:
            self._learn_tree.heading(c, text=h)
            self._learn_tree.column(c, width=w, anchor="center")

        self._learn_tree.pack(fill="x", padx=8, pady=6)

        # ── Recomendaciones textuales ─────────────────────────────────────────
        adv_f = tk.LabelFrame(right, text=" ANÁLISIS Y CONSEJOS ",
                              bg=BG_PANEL, fg=C_PURPLE,
                              font=("Consolas", 9, "bold"), bd=1, relief="solid")
        adv_f.pack(fill="both", expand=True, pady=(0, 0))

        self._adv_text = tk.Text(
            adv_f, bg=BG_DARK, fg=FG_TEXT,
            font=("Consolas", 9), state="disabled",
            bd=0, padx=8, pady=6, wrap="word",
        )
        self._adv_text.pack(fill="both", expand=True, padx=8, pady=6)

        self._run_learning_analysis()

    def _run_learning_analysis(self):
        """Analiza el historial y actualiza el panel de aprendizaje."""
        history = []
        if os.path.exists(BINGX_HISTORY):
            try:
                with open(BINGX_HISTORY, "r", encoding="utf-8") as f:
                    history = json.load(f)
            except Exception:
                pass

        if not isinstance(history, list):
            history = []

        closed = [t for t in history if t.get("result") in ("WIN", "LOSS")]

        # Análisis por señal
        buy  = [t for t in closed if t.get("direction") == "LONG"]
        sell = [t for t in closed if t.get("direction") == "SHORT"]

        def _stats(lst):
            if not lst:
                return 0, 0.0, 0.0
            wins    = sum(1 for t in lst if t.get("result") == "WIN")
            wr      = wins / len(lst) * 100
            pnl_sum = sum(float(t.get("pnl", 0)) for t in lst)
            return len(lst), wr, pnl_sum

        bn, bwr, bpnl = _stats(buy)
        sn, swr, spnl = _stats(sell)

        self._lv["buy_trades"].set(str(bn))
        self._lv["buy_wr"].set(f"{bwr:.1f}%")
        self._lv["buy_pnl"].set(f"{bpnl:+.4f}")
        self._lv["sell_trades"].set(str(sn))
        self._lv["sell_wr"].set(f"{swr:.1f}%")
        self._lv["sell_pnl"].set(f"{spnl:+.4f}")

        # Calidad y adaptación
        total_wr = self.stats.get("win_rate", 0)
        if total_wr >= 60:
            conf, recommend = "Alta (>60%)", "Mantener configuración actual"
        elif total_wr >= 45:
            conf, recommend = "Media (45-60%)", "Ajustar umbrales RSI"
        else:
            conf, recommend = "Baja (<45%)", "Revisar timeframe y ATR mult"

        self._lv["confidence"].set(conf)
        self._lv["recommend"].set(recommend)

        # Mejor/peor hora
        if closed:
            from collections import defaultdict
            hours = defaultdict(list)
            for t in closed:
                try:
                    h = datetime.strptime(t.get("timestamp", ""), "%Y-%m-%d %H:%M:%S").hour
                    hours[h].append(1 if t.get("result") == "WIN" else 0)
                except Exception:
                    pass
            if hours:
                best  = max(hours, key=lambda h: sum(hours[h]) / len(hours[h]))
                worst = min(hours, key=lambda h: sum(hours[h]) / len(hours[h]))
                self._lv["best_hour"].set(f"{best:02d}:00h")
                self._lv["worst_hour"].set(f"{worst:02d}:00h")
        else:
            self._lv["best_hour"].set("—")
            self._lv["worst_hour"].set("—")

        self._lv["avg_duration"].set("—")

        # Últimos 10 trades
        for row in self._learn_tree.get_children():
            self._learn_tree.delete(row)

        for t in list(reversed(history))[:10]:
            result = t.get("result", "—")
            pnl    = t.get("pnl", 0)
            ts_raw = t.get("timestamp", "—")
            try:
                ts = datetime.strptime(ts_raw, "%Y-%m-%d %H:%M:%S").strftime("%H:%M:%S")
            except Exception:
                ts = ts_raw
            self._learn_tree.insert("", "end", values=(
                ts,
                t.get("direction", "—"),
                f"{float(pnl):+.4f}" if isinstance(pnl, (int, float)) else "—",
                result,
            ), tags=(result,))

        # Consejos
        lines = ["=== Análisis Automático ===\n"]
        if not closed:
            lines.append("Sin trades cerrados aún. Inicia el bot para generar datos.")
        else:
            total = len(closed)
            wins  = sum(1 for t in closed if t.get("result") == "WIN")
            wr    = wins / total * 100
            lines.append(f"Total trades cerrados: {total}")
            lines.append(f"Win rate general: {wr:.1f}%\n")

            if bn > 0 and sn > 0:
                if bwr > swr + 10:
                    lines.append("💡 Las señales LONG tienen mejor rendimiento.")
                    lines.append("   Considera aumentar el umbral RSI bajista.")
                elif swr > bwr + 10:
                    lines.append("💡 Las señales SHORT tienen mejor rendimiento.")
                    lines.append("   Considera aumentar el umbral RSI alcista.")
                else:
                    lines.append("✔ LONG y SHORT tienen rendimiento similar.")

            if total_wr < 40:
                lines.append("\n⚠ Win rate bajo. Sugerencias:")
                lines.append("  - Aumentar ATR mult SL (reducir SL demasiado ajustado)")
                lines.append("  - Probar timeframe mayor (1h en vez de 15m)")
                lines.append("  - Aumentar umbral de RSI en zonas extremas")
            elif total_wr > 65:
                lines.append("\n✔ Excelente win rate. El sistema está bien calibrado.")

        advice = "\n".join(lines)
        self._adv_text.config(state="normal")
        self._adv_text.delete("1.0", "end")
        self._adv_text.insert("end", advice)
        self._adv_text.config(state="disabled")

    def _build_tab_config(self):
        tab = tk.Frame(self._nb, bg=BG_DARK)
        self._nb.add(tab, text="  Configuración  ")

        canvas = tk.Canvas(tab, bg=BG_DARK, highlightthickness=0)
        vsb    = ttk.Scrollbar(tab, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        inner  = tk.Frame(canvas, bg=BG_DARK)
        win_id = canvas.create_window((0, 0), window=inner, anchor="nw")

        def _resize(e):
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfig(win_id, width=canvas.winfo_width())

        inner.bind("<Configure>", _resize)
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(win_id, width=e.width))

        self._cfg_vars = {}

        def section(title, color=C_BLUE):
            f = tk.LabelFrame(
                inner, text=f" {title} ",
                bg=BG_PANEL, fg=color,
                font=("Consolas", 9, "bold"), bd=1, relief="solid",
            )
            f.pack(fill="x", padx=12, pady=(8, 0))
            return f

        def field(parent, row, label, key, tip=""):
            tk.Label(
                parent, text=label,
                bg=BG_PANEL, fg=FG_MUTED, font=("Consolas", 9), anchor="w",
            ).grid(row=row, column=0, sticky="w", padx=12, pady=4)
            var = tk.StringVar(value=str(self.cfg.get(key, "")))
            self._cfg_vars[key] = var
            tk.Entry(
                parent, textvariable=var,
                bg=BG_ENTRY, fg=FG_TEXT, insertbackground=FG_TEXT,
                font=("Consolas", 9), bd=0, relief="flat",
            ).grid(row=row, column=1, sticky="ew", padx=12, pady=4)
            if tip:
                tk.Label(
                    parent, text=tip,
                    bg=BG_PANEL, fg=FG_MUTED, font=("Consolas", 7), anchor="w",
                ).grid(row=row, column=2, sticky="w", padx=4)
            parent.columnconfigure(1, weight=1)

        def combo_field(parent, row, label, key, opts):
            tk.Label(
                parent, text=label,
                bg=BG_PANEL, fg=FG_MUTED, font=("Consolas", 9), anchor="w",
            ).grid(row=row, column=0, sticky="w", padx=12, pady=4)
            var = tk.StringVar(value=str(self.cfg.get(key, opts[0])))
            self._cfg_vars[key] = var
            cb = ttk.Combobox(parent, textvariable=var, values=opts,
                              state="readonly", width=14)
            cb.grid(row=row, column=1, sticky="w", padx=12, pady=4)
            parent.columnconfigure(1, weight=1)

        # Nota informativa
        tk.Label(
            inner,
            text="Los parámetros de API, símbolo, apalancamiento y riesgo se configuran\n"
                 "en Configuración del Sistema (botón ⚙ en el menú principal).",
            bg=BG_DARK, fg=FG_MUTED, font=("Consolas", 8, "italic"),
        ).pack(padx=16, pady=(10, 2), anchor="w")

        # Estrategia
        est_f = section("ESTRATEGIA  (EMA + RSI + ATR)", C_BLUE)
        combo_field(est_f, 0, "Timeframe:",         "timeframe",     ["1m","5m","15m","30m","1h","4h","1d"])
        field(est_f, 1, "EMA periodo corto:",        "ema_short",     "default 9")
        field(est_f, 2, "EMA periodo largo:",        "ema_long",      "default 21")
        field(est_f, 3, "Periodo RSI:",              "rsi_period",    "default 14")
        field(est_f, 4, "RSI sobrecomprado:",        "rsi_overbought","default 70")
        field(est_f, 5, "RSI sobrevendido:",         "rsi_oversold",  "default 30")

        # Gestión de SL/TP
        sl_f = section("STOP LOSS / TAKE PROFIT  (ATR)", C_ORANGE)
        field(sl_f, 0, "Mult. SL (× ATR):",  "atr_sl_mult",   "default 1.5")
        field(sl_f, 1, "Mult. TP (× ATR):",  "atr_tp_mult",   "default 3.0")

        # Operación del bot
        op_f = section("OPERACIÓN DEL BOT", C_GREEN)
        field(op_f, 0, "Cooldown (seg):",              "cooldown",         "10–600")
        field(op_f, 1, "Confianza mínima (0-100):",    "min_confidence",   "0–100")

        # Botones
        save_f = tk.Frame(inner, bg=BG_DARK)
        save_f.pack(fill="x", padx=12, pady=12)

        self._cfg_status = tk.StringVar()
        tk.Label(
            save_f, textvariable=self._cfg_status,
            bg=BG_DARK, fg=C_GREEN, font=("Consolas", 9),
        ).pack(side="right", padx=12)

        tk.Button(
            save_f, text="💾  Guardar estrategia",
            bg=C_BLUE, fg="white",
            font=("Consolas", 10, "bold"), bd=0,
            padx=20, pady=8, cursor="hand2", relief="flat",
            command=self._save_config,
        ).pack(side="right")

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 6 — Sistema
    # ══════════════════════════════════════════════════════════════════════════

    def _build_tab_system(self):
        tab = tk.Frame(self._nb, bg=BG_DARK)
        self._nb.add(tab, text="  Sistema  ")

        sys_f = tk.LabelFrame(
            tab, text=" INFORMACIÓN ",
            bg=BG_PANEL, fg=C_BLUE,
            font=("Consolas", 9, "bold"), bd=1, relief="solid",
        )
        sys_f.pack(fill="x", padx=8, pady=8)
        g = tk.Frame(sys_f, bg=BG_PANEL)
        g.pack(fill="x", padx=12, pady=8)

        for i, (lbl, val) in enumerate([
            ("Módulo:",   "bingx_gui.py"),
            ("Versión:",  self.VERSION),
            ("Python:",   sys.version.split()[0]),
            ("Platform:", "BingX Perpetual Futures"),
            ("Config:",   BINGX_CFG),
        ]):
            _info_row(g, i, lbl, val)

        files_f = tk.LabelFrame(
            tab, text=" ARCHIVOS DE DATOS ",
            bg=BG_PANEL, fg=C_ORANGE,
            font=("Consolas", 9, "bold"), bd=1, relief="solid",
        )
        files_f.pack(fill="x", padx=8, pady=(0, 8))
        fg = tk.Frame(files_f, bg=BG_PANEL)
        fg.pack(fill="x", padx=12, pady=8)

        for i, (lbl, path) in enumerate([
            ("Config:",        BINGX_CFG),
            ("Estadísticas:",  BINGX_STATS),
            ("Historial:",     BINGX_HISTORY),
            ("Cliente API:",   os.path.join(_DIR, "bingx_client.py")),
        ]):
            exists = os.path.exists(path)
            _info_row(fg, i, lbl,
                      f"{'✔' if exists else '✘'}  {os.path.basename(path)}",
                      value_fg=C_GREEN if exists else C_RED)

        api_f = tk.LabelFrame(
            tab, text=" DIAGNÓSTICO API ",
            bg=BG_PANEL, fg=C_PURPLE,
            font=("Consolas", 9, "bold"), bd=1, relief="solid",
        )
        api_f.pack(fill="x", padx=8, pady=(0, 8))

        tk.Button(
            api_f, text="▶  Probar conexión API",
            bg=C_BLUE, fg="white",
            font=("Consolas", 9, "bold"), bd=0,
            padx=14, pady=6, cursor="hand2", relief="flat",
            command=self._test_connection,
        ).pack(padx=12, pady=(10, 4), anchor="w")

        self._diag_text = tk.Text(
            api_f,
            bg=BG_DARK, fg=FG_TEXT,
            font=("Consolas", 8),
            height=12, state="disabled", bd=0, padx=4, pady=4,
        )
        self._diag_text.pack(fill="x", padx=12, pady=(0, 10))

    # ──────────────────────────────────────────
    # Utilidades de estilo
    # ──────────────────────────────────────────

    def _style_treeview(self, tree):
        s = ttk.Style()
        s.configure("Dark.Treeview",
                     background=BG_DARK, foreground=FG_TEXT,
                     fieldbackground=BG_DARK, rowheight=22, font=("Consolas", 8))
        s.configure("Dark.Treeview.Heading",
                     background=BG_WIDGET, foreground=C_BLUE,
                     font=("Consolas", 8, "bold"))
        s.map("Dark.Treeview", background=[("selected", BG_WIDGET)])
        tree.configure(style="Dark.Treeview")

    # ──────────────────────────────────────────
    # Reloj
    # ──────────────────────────────────────────

    def _start_clock(self):
        def _tick():
            self._clock_lbl.config(text=datetime.now().strftime("%H:%M:%S"))
            self.after(1000, _tick)
        _tick()

    # ──────────────────────────────────────────
    # Auto-actualización periódica
    # ──────────────────────────────────────────

    def _start_auto_update(self):
        def _loop():
            if self._conn_status == "CONNECTED" and self._client:
                threading.Thread(target=self._fetch_and_update_all, daemon=True).start()
            self.after(10_000, _loop)
        self.after(10_000, _loop)

    def _fetch_and_update_all(self):
        try:
            bal = self._client.get_balance()
            self.after(0, lambda b=bal: self._apply_balance(b))
        except Exception:
            pass

        try:
            pos = self._client.get_positions()
            self.after(0, lambda p=pos: self._apply_positions(p))
        except Exception:
            pass

        try:
            sym   = self.cfg.get("default_symbol", "BTC-USDT")
            tkr   = self._client.get_ticker(sym)
            price = float(tkr.get("lastPrice", tkr.get("price", 0)))
            chg   = float(tkr.get("priceChangePercent", 0))
            vol   = float(tkr.get("quoteVolume", tkr.get("volume", 0)))
            fr    = self._client.get_funding_rate(sym)
            self.after(0, lambda: self._apply_market(sym, price, chg, vol, fr))
        except Exception:
            pass

    # ──────────────────────────────────────────
    # Conexión API
    # ──────────────────────────────────────────

    def _connect_api(self):
        key    = self.cfg.get("api_key",    "").strip()
        secret = self.cfg.get("api_secret", "").strip()
        if not key or not secret:
            self._set_conn_status("ERROR")
            self._log("Sin credenciales. Ve a Configuración → guarda tu API Key y Secret, luego haz clic en Conectar.", "err")
            return
        self._set_conn_status("CONNECTING")
        self._log("Conectando con BingX Perpetual Futures...", "info")
        threading.Thread(target=self._do_connect, args=(key, secret), daemon=True).start()

    def _do_connect(self, key, secret):
        try:
            from bingx_client import BingXClient
            client = BingXClient(key, secret)

            # 1. Balance (verifica autenticación)
            bal = client.get_balance()
            # 2. UID
            uid = client.get_uid()
            # 3. Datos de mercado
            sym = self.cfg.get("default_symbol", "BTC-USDT")
            try:
                tkr   = client.get_ticker(sym)
                price = float(tkr.get("lastPrice", tkr.get("price", 0)))
                chg   = float(tkr.get("priceChangePercent", 0))
                vol   = float(tkr.get("quoteVolume", tkr.get("volume", 0)))
                fr    = client.get_funding_rate(sym)
            except Exception:
                price, chg, vol, fr = 0.0, 0.0, 0.0, 0.0
            # 4. Posiciones
            try:
                positions = client.get_positions()
            except Exception:
                positions = []

            def _apply():
                self._client    = client
                self._uid       = uid
                self._positions = positions
                self._set_conn_status("CONNECTED")
                self._apply_balance(bal)
                self._apply_positions(positions)
                self._apply_market(sym, price, chg, vol, fr)
                self._v_uid.set(f"UID: {uid}")
                self._update_bot_info()
                self._write_status(connected=True, running=False)
                bal_str = bal.get("balance", "?")
                self._log(
                    f"✔  Conectado | UID: {uid} | Balance: {bal_str} USDT | "
                    f"{len(positions)} posición(es) abierta(s)",
                    "ok",
                )

            self.after(0, _apply)

        except Exception as e:
            def _err(err=e):
                self._set_conn_status("ERROR")
                self._log(f"Error de conexión: {err}", "err")
            self.after(0, _err)

    def _set_conn_status(self, status: str):
        self._conn_status = status
        cfg = {
            "CONNECTED":    (C_GREEN,  "Conectado"),
            "CONNECTING":   (C_YELLOW, "Conectando..."),
            "ERROR":        (C_RED,    "Error de conexión"),
            "DISCONNECTED": (C_RED,    "Desconectado"),
        }
        color, text = cfg.get(status, (C_RED, status))

        self._conn_dot.config(fg=color)
        self._conn_label.config(text=text, fg=color)
        self._big_dot.config(fg=color)
        self._big_status.config(text=status, fg=color)

        if status == "CONNECTED":
            self._v_conn_t.set(datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
            self._start_btn.config(state="normal", bg=C_GREEN, fg=BG_DARK)
        else:
            self._start_btn.config(state="disabled", bg=BG_WIDGET, fg=FG_MUTED)
            if status in ("DISCONNECTED", "ERROR"):
                self._write_status(connected=False, running=False)

    def _apply_balance(self, bal: dict):
        def _f(key):
            return f"{float(bal.get(key, 0)):,.4f}"

        upnl = float(bal.get("unrealizedProfit", 0))
        self._v_bal.set(_f("balance")    + " USDT")
        self._v_equity.set(_f("equity")  + " USDT")
        self._v_avail.set(_f("availableMargin")  + " USDT")
        self._v_margin.set(_f("usedMargin")      + " USDT")
        self._v_upnl.set(f"{upnl:+,.4f} USDT")
        self._balance_data = bal
        # Escribe balance al archivo de estado compartido
        self._write_status(balance=float(bal.get("balance", 0)))

    def _apply_market(self, sym, price, chg, vol, fr):
        self._v_symbol.set(sym)
        self._v_price.set(f"${price:,.4f}")
        self._v_change.set(f"{'+' if chg >= 0 else ''}{chg:.2f}%")
        self._v_vol24.set(f"${vol:,.0f}")
        self._v_funding.set(f"{fr * 100:.4f}%")

    # ──────────────────────────────────────────
    # Posiciones
    # ──────────────────────────────────────────

    def _refresh_positions(self):
        if not self._client:
            messagebox.showwarning("Sin conexión", "Conéctate primero a la API.")
            return
        threading.Thread(target=self._fetch_positions_thread, daemon=True).start()

    def _fetch_positions_thread(self):
        try:
            pos = self._client.get_positions()
            self.after(0, lambda p=pos: self._apply_positions(p))
        except Exception as e:
            self._log_safe(f"Error obteniendo posiciones: {e}", "err")

    def _apply_positions(self, positions: list):
        self._positions = positions
        for row in self._pos_tree.get_children():
            self._pos_tree.delete(row)

        for p in positions:
            qty  = float(p.get("positionAmt", 0))
            if qty == 0:
                continue
            upnl = float(p.get("unrealizedProfit", 0))
            side = p.get("positionSide", "—")
            self._pos_tree.insert("", "end", values=(
                p.get("symbol", "—"),
                side,
                f"{abs(qty):.4f}",
                f"{float(p.get('avgPrice', 0)):,.4f}",
                f"{float(p.get('markPrice', 0)):,.4f}",
                f"{upnl:+,.4f}",
                f"{p.get('leverage', '—')}x",
                f"{float(p.get('margin', 0)):,.4f}",
                f"{float(p.get('liquidationPrice', 0)):,.4f}",
            ))

        n = len(positions)
        self._pos_count_lbl.config(
            text=f"{n} posición{'es' if n != 1 else ''} abierta{'s' if n != 1 else ''}"
        )

    def _close_selected_position(self):
        sel = self._pos_tree.selection()
        if not sel:
            messagebox.showinfo("Selecciona", "Selecciona una posición.")
            return
        vals  = self._pos_tree.item(sel[0])["values"]
        sym   = vals[0]
        side  = vals[1]
        qty   = float(vals[2])

        if not messagebox.askyesno(
            "Confirmar cierre",
            f"¿Cerrar {side} {qty} {sym} a mercado?\nEsta acción es irreversible.",
        ):
            return

        def _do():
            try:
                self._client.close_position(sym, side, qty)
                self._log_safe(f"Posición cerrada: {side} {qty} {sym}", "ok")
                self.after(1500, self._refresh_positions)
            except Exception as e:
                self._log_safe(f"Error cerrando posición: {e}", "err")

        threading.Thread(target=_do, daemon=True).start()

    # ──────────────────────────────────────────
    # Historial
    # ──────────────────────────────────────────

    def _load_history_tab(self):
        history = []
        if os.path.exists(BINGX_HISTORY):
            try:
                with open(BINGX_HISTORY, "r", encoding="utf-8") as f:
                    history = json.load(f)
                if not isinstance(history, list):
                    history = []
            except Exception:
                pass

        for row in self._hist_tree.get_children():
            self._hist_tree.delete(row)

        for t in reversed(history):
            result = t.get("result", "—")
            pnl    = t.get("pnl", 0)
            pnl_s  = f"{pnl:+.4f}" if isinstance(pnl, (int, float)) else str(pnl)
            self._hist_tree.insert("", "end", values=(
                t.get("timestamp", "—"),
                t.get("symbol",    "—"),
                t.get("direction", "—"),
                t.get("size",      "—"),
                t.get("entry",     "—"),
                t.get("exit",      "—"),
                pnl_s,
                result,
                t.get("strategy",  "—"),
            ), tags=(result,))

    def _clear_history(self):
        if not messagebox.askyesno("Limpiar historial", "¿Borrar todo el historial y estadísticas?"):
            return
        _save_json(BINGX_HISTORY, [])
        _save_json(BINGX_STATS,   dict(STATS_DEFAULTS))
        self.stats = dict(STATS_DEFAULTS)
        self._load_history_tab()
        self._update_stats_tab()
        self._log("Historial y estadísticas limpiados.", "warn")

    # ──────────────────────────────────────────
    # Estadísticas
    # ──────────────────────────────────────────

    def _update_stats_tab(self):
        s = self.stats
        self._sv["total_trades"].set(str(s.get("total_trades", 0)))
        self._sv["wins"].set(str(s.get("wins", 0)))
        self._sv["losses"].set(str(s.get("losses", 0)))
        self._sv["win_rate"].set(f"{s.get('win_rate', 0):.1f}%")
        self._sv["total_pnl"].set(f"{s.get('total_pnl', 0):+.4f} USDT")
        self._sv["best_trade"].set(f"{s.get('best_trade', 0):+.4f} USDT")
        self._sv["worst_trade"].set(f"{s.get('worst_trade', 0):+.4f} USDT")
        self._sv["streak"].set(f"{s.get('current_streak', 0)} {s.get('streak_type', '—')}")
        # Actualizar también el panel rápido del Dashboard
        self._sv_trades.set(str(s.get("total_trades", 0)))
        self._sv_wins.set(str(s.get("wins", 0)))
        self._sv_losses.set(str(s.get("losses", 0)))
        self._sv_wr.set(f"{s.get('win_rate', 0):.1f}%")
        self._update_chart()

    def _update_chart(self):
        if not HAS_MPL:
            return
        history = []
        if os.path.exists(BINGX_HISTORY):
            try:
                with open(BINGX_HISTORY, "r", encoding="utf-8") as f:
                    history = json.load(f)
            except Exception:
                pass

        if not isinstance(history, list) or not history:
            self._draw_empty_chart()
            return

        pnls = [float(t.get("pnl", 0)) for t in history if t.get("result") != "OPEN"]
        if not pnls:
            self._draw_empty_chart()
            return

        cum = []
        acc = 0.0
        for p in pnls:
            acc += p
            cum.append(acc)

        self._ax.clear()
        self._ax.set_facecolor(BG_DARK)
        color = C_GREEN if cum[-1] >= 0 else C_RED
        self._ax.plot(range(1, len(cum) + 1), cum, color=color, linewidth=1.5)
        self._ax.fill_between(range(1, len(cum) + 1), cum, alpha=0.15, color=color)
        self._ax.axhline(0, color=FG_MUTED, linewidth=0.5, linestyle="--")
        self._ax.set_xlabel("Trade #", color=FG_MUTED, fontsize=8)
        self._ax.set_ylabel("PnL acumulado (USDT)", color=FG_MUTED, fontsize=8)
        self._ax.tick_params(colors=FG_MUTED, labelsize=7)
        for spine in self._ax.spines.values():
            spine.set_color(BG_WIDGET)
        self._fig.tight_layout()
        self._canvas.draw()

    # ──────────────────────────────────────────
    # Configuración
    # ──────────────────────────────────────────

    def _save_config(self):
        try:
            new_cfg = dict(self.cfg)
            int_keys   = {"default_leverage", "max_positions", "min_confidence",
                          "cooldown", "max_daily_trades", "max_losses",
                          "ema_short", "ema_long", "rsi_period",
                          "rsi_overbought", "rsi_oversold"}
            float_keys = {"risk_percent", "atr_sl_mult", "atr_tp_mult"}
            for key, var in self._cfg_vars.items():
                val = var.get().strip()
                if key in int_keys:
                    new_cfg[key] = int(val)
                elif key in float_keys:
                    new_cfg[key] = float(val)
                else:
                    new_cfg[key] = val
            new_cfg.pop("demo_mode", None)  # eliminar modo demo si existe
            _save_json(BINGX_CFG, new_cfg)
            self.cfg = new_cfg
            self._cfg_status.set("✔ Guardado")
            self.after(3000, lambda: self._cfg_status.set(""))
            self._log("Configuración guardada.", "ok")
        except Exception as e:
            self._cfg_status.set(f"✘ Error: {e}")
            self._log(f"Error guardando config: {e}", "err")

    def _save_and_reconnect(self):
        self._save_config()
        self.after(300, self._connect_api)

    # ──────────────────────────────────────────
    # Bot: controles
    # ──────────────────────────────────────────

    def _update_bot_info(self):
        self._v_sym_bot.set(self.cfg.get("default_symbol",   "BTC-USDT"))
        self._v_lev_bot.set(f"{self.cfg.get('default_leverage', 10)}x")
        self._v_risk_bot.set(f"{self.cfg.get('risk_percent', 1.0)}%")
        self._v_trades_d.set(str(self._daily_trades))

    def _start_bot(self):
        if self._conn_status != "CONNECTED":
            messagebox.showwarning("Sin conexión", "Conéctate a la API antes de iniciar el bot.")
            return
        if self.bot_state == "RUNNING":
            return

        self.bot_state      = "RUNNING"
        self._daily_trades  = 0
        self._consec_losses = 0

        self._bot_dot.config(fg=C_GREEN)
        self._bot_lbl.config(text="ACTIVO", fg=C_GREEN)
        self._start_btn.config(state="disabled", bg=BG_WIDGET, fg=FG_MUTED)
        self._stop_btn.config(state="normal",   bg=C_RED,     fg="white")

        self._bot_thread = threading.Thread(target=self._bot_loop, daemon=True)
        self._bot_thread.start()
        self._log("Bot iniciado — Estrategia: EMA9/EMA21 + RSI14 + ATR14", "ok")
        self._write_status(running=True)

    def _stop_bot(self):
        if self.bot_state == "STOPPED":
            return
        self.bot_state = "STOPPED"
        self._bot_dot.config(fg=C_RED)
        self._bot_lbl.config(text="DETENIDO", fg=C_RED)
        self._start_btn.config(state="normal",  bg=C_GREEN,   fg=BG_DARK)
        self._stop_btn.config(state="disabled", bg=BG_WIDGET, fg=FG_MUTED)
        self._log("Bot detenido.", "warn")
        self._write_status(running=False)

    # ──────────────────────────────────────────
    # Estado compartido (bingx_status.json)
    # ──────────────────────────────────────────

    def _write_status(self, running=None, connected=None,
                      balance=None, daily_pnl=None):
        """Escribe bingx_status.json para que home_screen pueda leer el estado."""
        try:
            data = {}
            if os.path.exists(BINGX_STATUS):
                try:
                    with open(BINGX_STATUS, "r", encoding="utf-8") as f:
                        data = json.load(f)
                except Exception:
                    data = {}
            if running is not None:
                data["running"] = running
            if connected is not None:
                data["connected"] = connected
            if balance is not None:
                data["balance"] = balance
            if daily_pnl is not None:
                data["daily_pnl"] = daily_pnl
            _save_json(BINGX_STATUS, data)
        except Exception:
            pass

    # ──────────────────────────────────────────
    # Bot: loop principal
    # ──────────────────────────────────────────

    def _bot_loop(self):
        from bingx_client import generate_signal, calc_quantity
        self._log_safe("Hilo del bot activo.", "dim")

        while self.bot_state == "RUNNING":
            try:
                self._bot_cycle(generate_signal, calc_quantity)
            except Exception as e:
                self._log_safe(f"Error en ciclo: {e}", "err")

            cooldown = max(10, int(self.cfg.get("cooldown", 60)))
            for _ in range(cooldown):
                if self.bot_state != "RUNNING":
                    return
                time.sleep(1)

        self._log_safe("Hilo del bot finalizado.", "dim")

    def _bot_cycle(self, gen_signal, calc_qty):
        cfg    = self.cfg
        sym    = cfg.get("default_symbol",   "BTC-USDT")
        lev    = int(cfg.get("default_leverage", 10))
        mtp    = cfg.get("margin_type",      "ISOLATED")
        rsk    = float(cfg.get("risk_percent", 1.0))
        max_d  = int(cfg.get("max_daily_trades", 20))
        max_l  = int(cfg.get("max_losses",       3))
        max_p  = int(cfg.get("max_positions",    3))
        ts     = datetime.now().strftime("%H:%M:%S")

        # Límites diarios
        if self._daily_trades >= max_d:
            self._log_safe(f"[{ts}] Límite diario alcanzado ({max_d} trades).", "warn")
            return
        if self._consec_losses >= max_l:
            self._log_safe(f"[{ts}] Máx. pérdidas consecutivas ({max_l}). Deteniendo bot.", "err")
            self.after(0, self._stop_bot)
            return

        # Posiciones actuales
        try:
            positions = self._client.get_positions(sym)
            active    = [p for p in positions if float(p.get("positionAmt", 0)) != 0]
            if len(active) >= max_p:
                self._log_safe(f"[{ts}] Máx. posiciones abiertas ({max_p}).", "dim")
                return
            if any(p.get("symbol") == sym for p in active):
                self._log_safe(f"[{ts}] Ya existe posición en {sym}.", "dim")
                return
        except Exception as e:
            self._log_safe(f"[{ts}] Error posiciones: {e}", "warn")
            return

        # Balance
        try:
            bal   = self._client.get_balance()
            avail = float(bal.get("availableMargin", 0))
            self.after(0, lambda b=bal: self._apply_balance(b))
        except Exception as e:
            self._log_safe(f"[{ts}] Error balance: {e}", "warn")
            return

        if avail < 5:
            self._log_safe(f"[{ts}] Margen insuficiente ({avail:.2f} USDT).", "warn")
            return

        # Velas
        tf = cfg.get("timeframe", "15m")
        try:
            klines = self._client.get_klines(sym, interval=tf, limit=150)
            if len(klines) < 30:
                self._log_safe(f"[{ts}] Pocas velas ({len(klines)}).", "dim")
                return
        except Exception as e:
            self._log_safe(f"[{ts}] Error velas: {e}", "warn")
            return

        # Señal
        signal, rsi, atr = gen_signal(klines)
        last = klines[-1]
        price = float(last.get("close", last.get("c", 0)))

        # Actualizar panel IA con análisis de mercado (siempre, con o sin señal)
        self._ai_rsi   = rsi
        self._ai_atr   = atr
        self.after(0, lambda r=rsi, a=atr, s=signal, p=price, sy=sym:
                   self._update_ai_panel(r, a, s, p, sy))

        self._log_safe(
            f"[{ts}] {sym} | Precio: {price:.4f} | RSI: {rsi:.1f} | "
            f"ATR: {atr:.4f} | Señal: {signal or 'NINGUNA'}",
            "info",
        )

        if signal is None:
            return

        # SL / TP usando multiplicadores de config
        sl_mult = float(cfg.get("atr_sl_mult", 1.5))
        tp_mult = float(cfg.get("atr_tp_mult", 3.0))
        if signal == "BUY":
            sl, tp, side, pside = price - atr * sl_mult, price + atr * tp_mult, "BUY",  "LONG"
        else:
            sl, tp, side, pside = price + atr * sl_mult, price - atr * tp_mult, "SELL", "SHORT"

        qty = calc_qty(avail, rsk, price, sl, lev)
        if qty <= 0:
            self._log_safe(f"[{ts}] Cantidad inválida ({qty}).", "warn")
            return

        self._log_safe(
            f"[{ts}] SEÑAL {signal} {sym} | Qty: {qty} | SL: {sl:.4f} | TP: {tp:.4f}",
            "trade",
        )

        # Configurar leverage/margen
        try:
            self._client.set_margin_type(sym, "ISOLATED" if mtp == "ISOLATED" else "CROSSED")
            self._client.set_leverage(sym, lev)
        except Exception as e:
            self._log_safe(f"[{ts}] Advertencia leverage/margen: {e}", "warn")

        # Ejecutar orden
        try:
            order    = self._client.place_market_order(
                symbol=sym, side=side, position_side=pside,
                quantity=qty, stop_loss=sl, take_profit=tp,
            )
            order_id = order.get("orderId", "—")
            self._log_safe(f"[{ts}] ✔ Orden ejecutada — ID: {order_id}", "ok")

            self._daily_trades += 1
            self.after(0, lambda: self._v_trades_d.set(str(self._daily_trades)))
            sig_txt = f"{signal} {sym} @ {price:.4f}"
            self.after(0, lambda s=sig_txt: self._v_signal.set(s))
            sig_detail = (
                f"Señal:  {signal} {sym}\n"
                f"Precio: ${price:.4f}\n"
                f"RSI:    {rsi:.1f}   ATR: {atr:.4f}\n"
                f"SL:     ${sl:.4f}   TP: ${tp:.4f}\n"
                f"Qty:    {qty}   Lev: {lev}x\n"
                f"Hora:   {ts}"
            )
            def _update_sig_text(txt=sig_detail):
                self._sig_text.config(state="normal")
                self._sig_text.delete("1.0", "end")
                self._sig_text.insert("end", txt)
                self._sig_text.config(state="disabled")
            self.after(0, _update_sig_text)

            # Guardar en historial local
            self._append_history({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "symbol":    sym,
                "direction": pside,
                "size":      qty,
                "entry":     price,
                "exit":      0,
                "pnl":       0,
                "result":    "OPEN",
                "strategy":  "EMA9/21+RSI14",
                "order_id":  str(order_id),
            })
            self.after(0, self._load_history_tab)
        except Exception as e:
            self._log_safe(f"[{ts}] Error ejecutando orden: {e}", "err")

    # ──────────────────────────────────────────
    # Panel de análisis IA
    # ──────────────────────────────────────────

    def _update_ai_panel(self, rsi: float, atr: float, signal, price: float, symbol: str):
        """Actualiza el panel de análisis IA con el contexto del mercado actual."""
        try:
            w = self._ai_text
            w.config(state="normal")
            w.delete("1.0", "end")

            # Tendencia según EMA (aproximada por señal)
            if signal == "BUY":
                trend_txt, trend_tag = "▲ ALCISTA", "green"
            elif signal == "SELL":
                trend_txt, trend_tag = "▼ BAJISTA", "red"
            else:
                trend_txt, trend_tag = "→ LATERAL", "yellow"

            w.insert("end", f"{'─'*36}\n", "muted")
            w.insert("end", f"  Precio:  ", "muted")
            w.insert("end", f"${price:.4f}  ", "blue")
            w.insert("end", f"Símbolo: {symbol}\n", "muted")

            w.insert("end", f"  RSI:     ", "muted")
            rsi_tag = "red" if rsi > 65 else ("green" if rsi < 35 else "yellow")
            w.insert("end", f"{rsi:.1f}  ", rsi_tag)
            if rsi > 70:
                w.insert("end", "⚠ SOBRECOMPRA\n", "red")
            elif rsi < 30:
                w.insert("end", "⚠ SOBREVENTA\n", "green")
            elif rsi > 60:
                w.insert("end", "↑ Zona alta\n", "yellow")
            elif rsi < 40:
                w.insert("end", "↓ Zona baja\n", "yellow")
            else:
                w.insert("end", "→ Neutro\n", "muted")

            w.insert("end", f"  ATR:     ", "muted")
            w.insert("end", f"{atr:.4f}  volatilidad\n", "blue")

            w.insert("end", f"  Tendencia: ", "muted")
            w.insert("end", f"{trend_txt}\n", trend_tag)

            w.insert("end", f"{'─'*36}\n", "muted")

            # Recomendación IA
            w.insert("end", "  💡 IA: ", "yellow")
            if signal == "BUY":
                w.insert("end", "Señal de entrada LONG detectada.\n", "green")
                w.insert("end", "  Condiciones favorables para compra.\n", "muted")
            elif signal == "SELL":
                w.insert("end", "Señal de entrada SHORT detectada.\n", "red")
                w.insert("end", "  Condiciones favorables para venta.\n", "muted")
            elif rsi > 65:
                w.insert("end", "Mercado sobrecomprado.\n", "yellow")
                w.insert("end", "  Espera retroceso RSI < 60.\n", "muted")
            elif rsi < 35:
                w.insert("end", "Mercado sobrevendido.\n", "yellow")
                w.insert("end", "  Posible rebote próximo.\n", "muted")
            else:
                w.insert("end", "Sin señal. Esperando confluencia\n", "muted")
                w.insert("end", "  de indicadores EMA + RSI.\n", "muted")

            # Estado de pérdidas consecutivas
            if self._consec_losses >= 2:
                w.insert("end", f"\n  ⚠ {self._consec_losses} pérd. consec. — ", "red")
                w.insert("end", "Considera reducir riesgo.\n", "yellow")

            w.config(state="disabled")
        except Exception:
            pass

    # ──────────────────────────────────────────
    # Historial local
    # ──────────────────────────────────────────

    def _append_history(self, record: dict):
        history = []
        if os.path.exists(BINGX_HISTORY):
            try:
                with open(BINGX_HISTORY, "r", encoding="utf-8") as f:
                    history = json.load(f)
                if not isinstance(history, list):
                    history = []
            except Exception:
                pass
        history.append(record)
        _save_json(BINGX_HISTORY, history)

    def _update_stats_after_close(self, pnl: float):
        s = self.stats
        result = "WIN" if pnl >= 0 else "LOSS"
        s["total_trades"] += 1
        s["total_pnl"]    += pnl
        if result == "WIN":
            s["wins"] += 1
            self._consec_losses = 0
            s["best_trade"]  = max(s.get("best_trade", 0.0), pnl)
            if s.get("streak_type") == "WIN":
                s["current_streak"] = s.get("current_streak", 0) + 1
            else:
                s["current_streak"] = 1
            s["streak_type"] = "WIN"
        else:
            s["losses"] += 1
            self._consec_losses += 1
            s["worst_trade"] = min(s.get("worst_trade", 0.0), pnl)
            if s.get("streak_type") == "LOSS":
                s["current_streak"] = s.get("current_streak", 0) + 1
            else:
                s["current_streak"] = 1
            s["streak_type"] = "LOSS"

        s["win_rate"] = (s["wins"] / s["total_trades"] * 100) if s["total_trades"] > 0 else 0
        self.stats = s
        _save_json(BINGX_STATS, s)
        self.after(0, self._update_stats_tab)

    # ──────────────────────────────────────────
    # Diagnóstico
    # ──────────────────────────────────────────

    def _test_connection(self):
        key    = self.cfg.get("api_key",    "").strip()
        secret = self.cfg.get("api_secret", "").strip()

        self._diag_text.config(state="normal")
        self._diag_text.delete("1.0", "end")
        self._diag_text.insert("end", "Probando conexión...\n")
        self._diag_text.config(state="disabled")

        def _run():
            lines = [
                f"Timestamp: {datetime.now().isoformat()}",
                f"API Key:   {'*' * 8 + key[-4:] if len(key) > 4 else '—'}",
                f"Secret:    {'*** presente' if secret else 'NO CONFIGURADO'}",
                "",
            ]
            if not key or not secret:
                lines.append("✘ Sin credenciales. Ve a Configuración.")
            else:
                try:
                    from bingx_client import BingXClient
                    c   = BingXClient(key, secret)
                    bal = c.get_balance()
                    uid = c.get_uid()
                    pos = c.get_positions()
                    lines += [
                        "✔ Conexión exitosa",
                        f"  UID:               {uid}",
                        f"  Balance:           {bal.get('balance','?')} USDT",
                        f"  Equity:            {bal.get('equity','?')} USDT",
                        f"  Margen disponible: {bal.get('availableMargin','?')} USDT",
                        f"  PnL no realizado:  {bal.get('unrealizedProfit','?')} USDT",
                        f"  Posiciones abiertas: {len(pos)}",
                    ]
                except Exception as e:
                    lines.append(f"✘ Error: {e}")

            text = "\n".join(lines)

            def _show():
                self._diag_text.config(state="normal")
                self._diag_text.delete("1.0", "end")
                self._diag_text.insert("end", text)
                self._diag_text.config(state="disabled")

            self.after(0, _show)

        threading.Thread(target=_run, daemon=True).start()

    # ──────────────────────────────────────────
    # Logging thread-safe
    # ──────────────────────────────────────────

    def _log(self, msg: str, tag: str = ""):
        self._log_widget.config(state="normal")
        ts = datetime.now().strftime("%H:%M:%S")
        self._log_widget.insert("end", f"[{ts}] {msg}\n", tag or "")
        self._log_widget.see("end")
        self._log_widget.config(state="disabled")

    def _log_safe(self, msg: str, tag: str = ""):
        self.after(0, lambda m=msg, t=tag: self._log(m, t))

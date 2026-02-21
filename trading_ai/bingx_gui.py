"""
bingx_gui.py — Panel completo de BingX Perpetual Futures (REAL, sin demo)

Tabs:
  1. Dashboard  — Estado de conexión + datos de cuenta + controles del bot
  2. Posiciones — Posiciones abiertas en tiempo real desde la API
  3. Estadísticas — Métricas acumuladas de rendimiento
  4. Historial   — Historial de trades locales
  5. Config      — API Key, parámetros de trading y bot
  6. Sistema     — Info técnica y diagnóstico
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
# Rutas de archivos
# ──────────────────────────────────────────────────────────────────────────────
_DIR          = os.path.dirname(os.path.abspath(__file__))
BINGX_CFG     = os.path.join(_DIR, "bingx_config.json")
BINGX_STATS   = os.path.join(_DIR, "bingx_stats.json")
BINGX_HISTORY = os.path.join(_DIR, "bingx_history.json")

BINGX_DEFAULTS = {
    "api_key":          "",
    "api_secret":       "",
    "default_symbol":   "BTC-USDT",
    "default_leverage": 10,
    "margin_type":      "ISOLATED",
    "risk_percent":     1.0,
    "max_positions":    3,
    "min_confidence":   30,
    "cooldown":         60,
    "max_daily_trades": 20,
    "max_losses":       3,
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
        self._build_tab_config()
        self._build_tab_system()

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 1 — Dashboard
    # ══════════════════════════════════════════════════════════════════════════

    def _build_tab_dashboard(self):
        tab = tk.Frame(self._nb, bg=BG_DARK)
        self._nb.add(tab, text="  Dashboard  ")

        left  = tk.Frame(tab, bg=BG_DARK)
        right = tk.Frame(tab, bg=BG_DARK)
        left.pack(side="left",  fill="both", expand=True, padx=(8, 4), pady=8)
        right.pack(side="right", fill="both", expand=True, padx=(4, 8), pady=8)

        # ── Panel cuenta ─────────────────────────────────────────────────────
        acc = tk.LabelFrame(
            left, text=" CUENTA ",
            bg=BG_PANEL, fg=C_BLUE,
            font=("Consolas", 9, "bold"), bd=1, relief="solid",
        )
        acc.pack(fill="x", pady=(0, 6))

        conn_row = tk.Frame(acc, bg=BG_PANEL)
        conn_row.pack(fill="x", padx=12, pady=(10, 4))

        self._big_dot    = tk.Label(conn_row, text="●", bg=BG_PANEL, fg=C_RED,  font=("Consolas", 18))
        self._big_dot.pack(side="left")
        self._big_status = tk.Label(conn_row, text="DESCONECTADO", bg=BG_PANEL, fg=C_RED, font=("Consolas", 11, "bold"))
        self._big_status.pack(side="left", padx=8)

        self._reconnect_btn = tk.Button(
            conn_row, text="Conectar",
            bg=C_BLUE, fg="white",
            font=("Consolas", 9, "bold"), bd=0,
            padx=12, pady=4, cursor="hand2", relief="flat",
            command=self._connect_api,
        )
        self._reconnect_btn.pack(side="right", padx=4)

        grid = tk.Frame(acc, bg=BG_PANEL)
        grid.pack(fill="x", padx=12, pady=(4, 10))

        self._v_uid    = _info_row(grid, 0, "UID:")
        self._v_bal    = _info_row(grid, 1, "Balance:",          value_fg=C_GREEN)
        self._v_equity = _info_row(grid, 2, "Equity:")
        self._v_avail  = _info_row(grid, 3, "Margen disponible:")
        self._v_upnl   = _info_row(grid, 4, "PnL no realizado:", value_fg=C_YELLOW)
        self._v_margin = _info_row(grid, 5, "Margen usado:")
        self._v_conn_t = _info_row(grid, 6, "Conectado a las:")

        # ── Panel mercado ─────────────────────────────────────────────────────
        mkt = tk.LabelFrame(
            left, text=" MERCADO ",
            bg=BG_PANEL, fg=C_ORANGE,
            font=("Consolas", 9, "bold"), bd=1, relief="solid",
        )
        mkt.pack(fill="x", pady=(0, 6))

        mg = tk.Frame(mkt, bg=BG_PANEL)
        mg.pack(fill="x", padx=12, pady=8)
        self._v_symbol  = _info_row(mg, 0, "Símbolo:")
        self._v_price   = _info_row(mg, 1, "Precio:",        value_fg=C_BLUE)
        self._v_change  = _info_row(mg, 2, "Cambio 24h:")
        self._v_vol24   = _info_row(mg, 3, "Volumen 24h:")
        self._v_funding = _info_row(mg, 4, "Financiamiento:")

        # ── Panel bot ─────────────────────────────────────────────────────────
        bot_frame = tk.LabelFrame(
            right, text=" BOT ",
            bg=BG_PANEL, fg=C_GREEN,
            font=("Consolas", 9, "bold"), bd=1, relief="solid",
        )
        bot_frame.pack(fill="x", pady=(0, 6))

        sr = tk.Frame(bot_frame, bg=BG_PANEL)
        sr.pack(fill="x", padx=12, pady=(10, 4))
        self._bot_dot = tk.Label(sr, text="●", bg=BG_PANEL, fg=C_RED, font=("Consolas", 18))
        self._bot_dot.pack(side="left")
        self._bot_lbl = tk.Label(sr, text="DETENIDO", bg=BG_PANEL, fg=C_RED, font=("Consolas", 11, "bold"))
        self._bot_lbl.pack(side="left", padx=8)

        br = tk.Frame(bot_frame, bg=BG_PANEL)
        br.pack(fill="x", padx=12, pady=(4, 10))

        self._start_btn = tk.Button(
            br, text="▶  INICIAR BOT",
            bg=BG_WIDGET, fg=FG_MUTED,
            font=("Consolas", 10, "bold"), bd=0,
            padx=16, pady=8, cursor="hand2", relief="flat",
            command=self._start_bot, state="disabled",
        )
        self._start_btn.pack(side="left", padx=(0, 8))

        self._stop_btn = tk.Button(
            br, text="◼  DETENER",
            bg=BG_WIDGET, fg=FG_MUTED,
            font=("Consolas", 10, "bold"), bd=0,
            padx=16, pady=8, cursor="hand2", relief="flat",
            command=self._stop_bot, state="disabled",
        )
        self._stop_btn.pack(side="left")

        binfo = tk.Frame(bot_frame, bg=BG_PANEL)
        binfo.pack(fill="x", padx=12, pady=(0, 10))
        self._v_sym_bot  = _info_row(binfo, 0, "Símbolo:")
        self._v_lev_bot  = _info_row(binfo, 1, "Apalancamiento:")
        self._v_risk_bot = _info_row(binfo, 2, "Riesgo/trade:")
        self._v_signal   = _info_row(binfo, 3, "Última señal:", value_fg=C_YELLOW)
        self._v_trades_d = _info_row(binfo, 4, "Trades hoy:")

        # ── Log ───────────────────────────────────────────────────────────────
        log_frame = tk.LabelFrame(
            right, text=" LOG ",
            bg=BG_PANEL, fg=FG_MUTED,
            font=("Consolas", 9, "bold"), bd=1, relief="solid",
        )
        log_frame.pack(fill="both", expand=True, pady=(0, 6))

        self._log_widget = tk.Text(
            log_frame,
            bg=BG_DARK, fg=FG_TEXT,
            font=("Consolas", 8),
            state="disabled", wrap="word", bd=0, padx=4, pady=4,
        )
        vsb = ttk.Scrollbar(log_frame, command=self._log_widget.yview)
        self._log_widget.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self._log_widget.pack(fill="both", expand=True)

        for tag, color in [
            ("ok",    C_GREEN),  ("err",   C_RED),
            ("warn",  C_YELLOW), ("info",  C_BLUE),
            ("dim",   FG_MUTED), ("trade", C_ORANGE),
        ]:
            self._log_widget.tag_configure(tag, foreground=color)

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

        def field(parent, row, label, key, show="", tip=""):
            tk.Label(
                parent, text=label,
                bg=BG_PANEL, fg=FG_MUTED, font=("Consolas", 9), anchor="w",
            ).grid(row=row, column=0, sticky="w", padx=12, pady=4)
            var = tk.StringVar(value=str(self.cfg.get(key, "")))
            self._cfg_vars[key] = var
            tk.Entry(
                parent, textvariable=var, show=show,
                bg=BG_ENTRY, fg=FG_TEXT, insertbackground=FG_TEXT,
                font=("Consolas", 9), bd=0, relief="flat",
            ).grid(row=row, column=1, sticky="ew", padx=12, pady=4)
            if tip:
                tk.Label(
                    parent, text=tip,
                    bg=BG_PANEL, fg=FG_MUTED, font=("Consolas", 7), anchor="w",
                ).grid(row=row, column=2, sticky="w", padx=4)
            parent.columnconfigure(1, weight=1)

        # API
        api_f = section("CREDENCIALES API BINGX")
        field(api_f, 0, "API Key:",    "api_key")
        field(api_f, 1, "API Secret:", "api_secret", show="*")
        tk.Label(
            api_f,
            text="Genera tu API Key: BingX → Perfil → Gestión de API",
            bg=BG_PANEL, fg=FG_MUTED, font=("Consolas", 8, "italic"),
        ).grid(row=2, columnspan=3, sticky="w", padx=12, pady=(0, 8))

        # Trading
        trd_f = section("PARÁMETROS DE TRADING")
        field(trd_f, 0, "Símbolo:",           "default_symbol",   tip="ej: BTC-USDT, ETH-USDT")
        field(trd_f, 1, "Apalancamiento:",     "default_leverage", tip="1–125")
        field(trd_f, 2, "Tipo de margen:",     "margin_type",      tip="ISOLATED | CROSSED")
        field(trd_f, 3, "Riesgo por trade %:", "risk_percent",     tip="0.1–10.0")

        # Bot
        bot_f = section("PARÁMETROS DEL BOT")
        field(bot_f, 0, "Confianza mínima %:", "min_confidence",   tip="0–100")
        field(bot_f, 1, "Cooldown (seg):",      "cooldown",         tip="10–600")
        field(bot_f, 2, "Max trades/día:",       "max_daily_trades", tip="1–100")
        field(bot_f, 3, "Max pérdidas cons.:",   "max_losses",       tip="1–20")
        field(bot_f, 4, "Max posiciones sim.:",  "max_positions",    tip="1–10")

        # Botones
        save_f = tk.Frame(inner, bg=BG_DARK)
        save_f.pack(fill="x", padx=12, pady=12)

        self._cfg_status = tk.StringVar()
        tk.Label(
            save_f, textvariable=self._cfg_status,
            bg=BG_DARK, fg=C_GREEN, font=("Consolas", 9),
        ).pack(side="right", padx=12)

        tk.Button(
            save_f, text="Guardar y reconectar",
            bg=C_GREEN, fg=BG_DARK,
            font=("Consolas", 10, "bold"), bd=0,
            padx=20, pady=8, cursor="hand2", relief="flat",
            command=self._save_and_reconnect,
        ).pack(side="right", padx=8)

        tk.Button(
            save_f, text="💾  Guardar",
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
                self._v_uid.set(uid)
                self._update_bot_info()
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
                          "cooldown", "max_daily_trades", "max_losses"}
            float_keys = {"risk_percent"}
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

    def _stop_bot(self):
        if self.bot_state == "STOPPED":
            return
        self.bot_state = "STOPPED"
        self._bot_dot.config(fg=C_RED)
        self._bot_lbl.config(text="DETENIDO", fg=C_RED)
        self._start_btn.config(state="normal",  bg=C_GREEN,   fg=BG_DARK)
        self._stop_btn.config(state="disabled", bg=BG_WIDGET, fg=FG_MUTED)
        self._log("Bot detenido.", "warn")

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
        try:
            klines = self._client.get_klines(sym, interval="15m", limit=150)
            if len(klines) < 30:
                self._log_safe(f"[{ts}] Pocas velas ({len(klines)}).", "dim")
                return
        except Exception as e:
            self._log_safe(f"[{ts}] Error velas: {e}", "warn")
            return

        # Señal
        signal, rsi, atr = gen_signal(klines)
        price = float(klines[-1].get("c", 0))

        self._log_safe(
            f"[{ts}] {sym} | Precio: {price:.4f} | RSI: {rsi:.1f} | "
            f"ATR: {atr:.4f} | Señal: {signal or 'NINGUNA'}",
            "info",
        )

        if signal is None:
            return

        # SL / TP (1.5x / 3x ATR)
        if signal == "BUY":
            sl, tp, side, pside = price - atr * 1.5, price + atr * 3.0, "BUY",  "LONG"
        else:
            sl, tp, side, pside = price + atr * 1.5, price - atr * 3.0, "SELL", "SHORT"

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
            self.after(0, lambda: self._v_signal.set(f"{signal} {sym} @ {price:.4f}"))

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

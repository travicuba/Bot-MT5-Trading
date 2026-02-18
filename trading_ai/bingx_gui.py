"""
bingx_gui.py - Panel de Trading de Futuros BingX

Pestañas:
  1. Dashboard   – Vista en tiempo real, controles, estado del bot
  2. Posiciones  – Posiciones abiertas en BingX
  3. Estadísticas – Análisis independiente (no mezcla con MT5)
  4. Historial   – Historial de trades de BingX
  5. Configuración – Parámetros del bot y API
  6. Sistema     – Estado de conexión y archivos

El módulo está preparado para conectarse a la API de BingX Futures
(futuros perpetuos). Mientras la API key no esté configurada, opera
en modo simulación/demo con datos ficticios.
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import json
import os
import sys
import threading
import time
from datetime import datetime, timedelta
from collections import defaultdict

# ──────────────────────────────────────────────
# Paleta de colores
# ──────────────────────────────────────────────
BG_DARK    = "#0a0e27"
BG_PANEL   = "#151b3d"
BG_WIDGET  = "#1e2749"
FG_TEXT    = "#e0e6ff"
FG_MUTED   = "#8b9dc3"
C_BLUE     = "#4895ef"
C_GREEN    = "#06ffa5"
C_RED      = "#ff006e"
C_YELLOW   = "#ffbe0b"
C_ORANGE   = "#ff9a00"

_BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
BINGX_CFG_FILE = os.path.join(_BASE_DIR, "bingx_config.json")
BINGX_STATS_FILE = os.path.join(_BASE_DIR, "bingx_stats.json")
BINGX_HISTORY_FILE = os.path.join(_BASE_DIR, "bingx_history.json")
BINGX_LOG_DIR  = os.path.join(_BASE_DIR, "logs")

BINGX_DEFAULTS = {
    "api_key":          "",
    "api_secret":       "",
    "demo_mode":        True,
    "default_symbol":   "BTC-USDT",
    "default_leverage": 5,
    "margin_type":      "ISOLATED",
    "risk_percent":     1.0,
    "max_positions":    3,
    "min_confidence":   30,
    "cooldown":         60,
    "max_daily_trades": 20,
    "max_losses":       3,
}

VERSION = "3.0.0"

# Matplotlib opcional
try:
    import matplotlib
    matplotlib.use("TkAgg")
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    MATPLOTLIB_OK = True
except Exception:
    MATPLOTLIB_OK = False


def _load_cfg():
    if os.path.exists(BINGX_CFG_FILE):
        try:
            with open(BINGX_CFG_FILE) as f:
                d = json.load(f)
            for k, v in BINGX_DEFAULTS.items():
                d.setdefault(k, v)
            return d
        except Exception:
            pass
    return dict(BINGX_DEFAULTS)


def _load_stats():
    default = {
        "total_trades": 0, "wins": 0, "losses": 0,
        "total_pnl": 0.0, "win_rate": 0.0,
        "best_trade": 0.0, "worst_trade": 0.0,
        "current_streak": 0, "streak_type": "—",
    }
    if os.path.exists(BINGX_STATS_FILE):
        try:
            with open(BINGX_STATS_FILE) as f:
                d = json.load(f)
            for k, v in default.items():
                d.setdefault(k, v)
            return d
        except Exception:
            pass
    return default


def _load_history():
    if os.path.exists(BINGX_HISTORY_FILE):
        try:
            with open(BINGX_HISTORY_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return []


class BingXPanel(tk.Frame):
    """Panel completo de trading de futuros BingX."""

    def __init__(self, parent, root, on_home):
        super().__init__(parent, bg=BG_DARK)
        self.root    = root     # ventana Tk real (para after/update)
        self.on_home = on_home

        self.cfg     = _load_cfg()
        self.stats   = _load_stats()
        self.history = _load_history()

        self.bot_state   = "STOPPED"
        self.bot_thread  = None
        self._positions  = []  # posiciones abiertas simuladas

        # Stdout capture
        self._log_buffer = []

        self._setup_styles()
        self._build_nav_bar()
        self._build_notebook()
        self._auto_update()

    # ──────────────────────────────────────────
    # Estilos
    # ──────────────────────────────────────────

    def _setup_styles(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("TNotebook", background=BG_DARK, borderwidth=0)
        style.configure("TNotebook.Tab",
                        background=BG_PANEL, foreground=FG_TEXT,
                        padding=[16, 8], font=("Segoe UI", 10, "bold"))
        style.map("TNotebook.Tab",
                  background=[("selected", BG_WIDGET)],
                  foreground=[("selected", C_ORANGE)])
        style.configure("Dark.TFrame", background=BG_DARK)
        style.configure("Panel.TFrame", background=BG_PANEL)

    # ──────────────────────────────────────────
    # Barra de navegación superior
    # ──────────────────────────────────────────

    def _build_nav_bar(self):
        nav = tk.Frame(self, bg="#07091e", height=50)
        nav.pack(fill=tk.X)
        nav.pack_propagate(False)

        tk.Frame(nav, bg=C_ORANGE, height=2).place(relx=0, rely=1.0, anchor="sw", relwidth=1)

        back_btn = tk.Button(
            nav, text="◀  Menú Principal",
            command=self._go_home,
            bg=BG_WIDGET, fg=FG_TEXT,
            font=("Segoe UI", 10, "bold"),
            relief=tk.FLAT, cursor="hand2",
            padx=14, pady=6, bd=0,
            activebackground=C_ORANGE,
            activeforeground="white",
        )
        back_btn.pack(side=tk.LEFT, padx=12, pady=8)

        tk.Label(
            nav,
            text="🔮  BingX Futures — Panel de Trading",
            bg="#07091e", fg=C_ORANGE,
            font=("Segoe UI", 13, "bold"),
        ).pack(side=tk.LEFT, padx=14)

        # Demo badge
        self.demo_badge = tk.Label(
            nav,
            text="  DEMO  " if self.cfg.get("demo_mode", True) else "  REAL  ",
            bg=C_YELLOW if self.cfg.get("demo_mode", True) else C_GREEN,
            fg="#0a0e27",
            font=("Segoe UI", 9, "bold"),
        )
        self.demo_badge.pack(side=tk.LEFT, padx=6)

        # Reloj
        self.nav_clock = tk.Label(nav, text="", bg="#07091e", fg=FG_MUTED, font=("Consolas", 10))
        self.nav_clock.pack(side=tk.RIGHT, padx=16)
        self._tick_clock()

    def _tick_clock(self):
        if self.nav_clock.winfo_exists():
            self.nav_clock.configure(text=datetime.now().strftime("%Y-%m-%d   %H:%M:%S"))
            self.after(1000, self._tick_clock)

    def _go_home(self):
        """
        Regresar al menú principal.
        El panel queda oculto pero no destruido: el bot BingX continúa
        ejecutándose en segundo plano y al volver el estado se conserva.
        """
        self.on_home()

    # ──────────────────────────────────────────
    # Notebook
    # ──────────────────────────────────────────

    def _build_notebook(self):
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)

        self._tab_dashboard()
        self._tab_positions()
        self._tab_statistics()
        self._tab_history()
        self._tab_config()
        self._tab_system()

    # ══════════════════════════════════════════
    # TAB 1: DASHBOARD
    # ══════════════════════════════════════════

    def _tab_dashboard(self):
        tab = ttk.Frame(self.notebook, style="Dark.TFrame")
        self.notebook.add(tab, text="  ▣ Dashboard  ")

        # ── Header de control ──────────────────
        header = tk.Frame(tab, bg=BG_PANEL, height=110)
        header.pack(fill=tk.X, padx=10, pady=8)
        header.pack_propagate(False)

        # Estado
        st_frame = tk.Frame(header, bg=BG_PANEL)
        st_frame.pack(side=tk.LEFT, padx=20, pady=12)
        tk.Label(st_frame, text="Estado del Bot", bg=BG_PANEL, fg=FG_TEXT,
                 font=("Segoe UI", 9)).pack()
        self.status_canvas = tk.Canvas(st_frame, width=56, height=56, bg=BG_PANEL,
                                       highlightthickness=0)
        self.status_canvas.pack(pady=4)
        self.status_oval = self.status_canvas.create_oval(8, 8, 48, 48, fill="#555", outline="")
        self.status_lbl = tk.Label(st_frame, text="DETENIDO", bg=BG_PANEL, fg=C_RED,
                                   font=("Segoe UI", 10, "bold"))
        self.status_lbl.pack()

        # Botones de control
        btn_frame = tk.Frame(header, bg=BG_PANEL)
        btn_frame.pack(side=tk.LEFT, padx=24, pady=12)

        self.start_btn = tk.Button(
            btn_frame, text="► INICIAR",
            command=self._start_bot,
            bg=C_GREEN, fg="#0a0e27",
            font=("Segoe UI", 11, "bold"),
            width=12, height=2, relief=tk.FLAT, cursor="hand2",
        )
        self.start_btn.pack(side=tk.LEFT, padx=5)

        self.stop_btn = tk.Button(
            btn_frame, text="■ DETENER",
            command=self._stop_bot,
            bg=C_RED, fg="white",
            font=("Segoe UI", 11, "bold"),
            width=12, height=2, relief=tk.FLAT, cursor="hand2",
            state=tk.DISABLED,
        )
        self.stop_btn.pack(side=tk.LEFT, padx=5)

        # Info de cuenta (simulada)
        acc_frame = tk.Frame(header, bg=BG_PANEL)
        acc_frame.pack(side=tk.RIGHT, padx=20, pady=12)

        self.balance_lbl = tk.Label(acc_frame, text="Balance: —", bg=BG_PANEL, fg=FG_TEXT,
                                    font=("Segoe UI", 10))
        self.balance_lbl.pack(anchor="e")
        self.pnl_lbl = tk.Label(acc_frame, text="PnL hoy: —", bg=BG_PANEL, fg=FG_TEXT,
                                 font=("Segoe UI", 10))
        self.pnl_lbl.pack(anchor="e")
        self.symbol_lbl = tk.Label(acc_frame, text=f"Símbolo: {self.cfg.get('default_symbol','BTC-USDT')}",
                                   bg=BG_PANEL, fg=C_ORANGE, font=("Segoe UI", 10, "bold"))
        self.symbol_lbl.pack(anchor="e")

        # ── Cuerpo ────────────────────────────
        body = tk.Frame(tab, bg=BG_DARK)
        body.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 8))

        # Columna izquierda
        left = tk.Frame(body, bg=BG_DARK, width=420)
        left.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 6))
        left.pack_propagate(False)

        # Columna derecha
        right = tk.Frame(body, bg=BG_DARK)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._panel_quick_stats(left)
        self._panel_market_info(left)
        self._panel_last_signal(right)
        self._panel_logs(right)

    def _panel_quick_stats(self, parent):
        frame = tk.LabelFrame(parent, text="  ESTADÍSTICAS RÁPIDAS  ",
                              bg=BG_PANEL, fg=C_ORANGE,
                              font=("Segoe UI", 10, "bold"), relief=tk.FLAT)
        frame.pack(fill=tk.X, pady=(0, 6))

        grid = tk.Frame(frame, bg=BG_PANEL)
        grid.pack(fill=tk.X, padx=10, pady=8)

        def _stat(row, col, label, attr, color=C_BLUE):
            f = tk.Frame(grid, bg=BG_WIDGET, padx=12, pady=8)
            f.grid(row=row, column=col, padx=4, pady=4, sticky="nsew")
            tk.Label(f, text=label, bg=BG_WIDGET, fg=FG_MUTED,
                     font=("Segoe UI", 8)).pack()
            lbl = tk.Label(f, text="0", bg=BG_WIDGET, fg=color,
                           font=("Segoe UI", 16, "bold"))
            lbl.pack()
            return lbl

        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)
        grid.columnconfigure(2, weight=1)
        grid.columnconfigure(3, weight=1)

        self.bx_lbl_total  = _stat(0, 0, "Trades",    "total_trades", FG_TEXT)
        self.bx_lbl_wins   = _stat(0, 1, "Victorias", "wins",          C_GREEN)
        self.bx_lbl_losses = _stat(0, 2, "Pérdidas",  "losses",        C_RED)
        self.bx_lbl_wr     = _stat(0, 3, "Win Rate",  "win_rate",      C_ORANGE)

    def _panel_market_info(self, parent):
        frame = tk.LabelFrame(parent, text="  MERCADO BingX  ",
                              bg=BG_PANEL, fg=C_ORANGE,
                              font=("Segoe UI", 10, "bold"), relief=tk.FLAT)
        frame.pack(fill=tk.BOTH, expand=True, pady=(0, 0))

        self.market_text = scrolledtext.ScrolledText(
            frame, height=8, bg=BG_WIDGET, fg=FG_TEXT,
            font=("Consolas", 9), relief=tk.FLAT, wrap=tk.WORD,
            state=tk.DISABLED,
        )
        self.market_text.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

    def _panel_last_signal(self, parent):
        frame = tk.LabelFrame(parent, text="  ÚLTIMA SEÑAL  ",
                              bg=BG_PANEL, fg=C_ORANGE,
                              font=("Segoe UI", 10, "bold"), relief=tk.FLAT)
        frame.pack(fill=tk.X, pady=(0, 6))

        self.signal_text = scrolledtext.ScrolledText(
            frame, height=6, bg=BG_WIDGET, fg=FG_TEXT,
            font=("Consolas", 9), relief=tk.FLAT, wrap=tk.WORD,
            state=tk.DISABLED,
        )
        self.signal_text.pack(fill=tk.X, padx=6, pady=6)

    def _panel_logs(self, parent):
        frame = tk.LabelFrame(parent, text="  LOG DEL BOT  ",
                              bg=BG_PANEL, fg=C_ORANGE,
                              font=("Segoe UI", 10, "bold"), relief=tk.FLAT)
        frame.pack(fill=tk.BOTH, expand=True)

        # Barra de botones de log
        bar = tk.Frame(frame, bg=BG_PANEL)
        bar.pack(fill=tk.X, padx=6, pady=(4, 0))
        tk.Button(bar, text="Limpiar", command=self._clear_log,
                  bg=BG_WIDGET, fg=FG_TEXT, relief=tk.FLAT, cursor="hand2",
                  font=("Segoe UI", 8), padx=8, pady=3).pack(side=tk.RIGHT)

        self.log_text = scrolledtext.ScrolledText(
            frame, bg=BG_WIDGET, fg=FG_TEXT,
            font=("Consolas", 9), relief=tk.FLAT, wrap=tk.WORD,
            state=tk.DISABLED,
        )
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        self.log_text.tag_configure("ok",    foreground=C_GREEN)
        self.log_text.tag_configure("error", foreground=C_RED)
        self.log_text.tag_configure("warn",  foreground=C_YELLOW)
        self.log_text.tag_configure("info",  foreground=C_BLUE)
        self.log_text.tag_configure("dim",   foreground=FG_MUTED)

    def _clear_log(self):
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.configure(state=tk.DISABLED)

    # ══════════════════════════════════════════
    # TAB 2: POSICIONES
    # ══════════════════════════════════════════

    def _tab_positions(self):
        tab = ttk.Frame(self.notebook, style="Dark.TFrame")
        self.notebook.add(tab, text="  ⬡ Posiciones  ")

        header = tk.Frame(tab, bg=BG_PANEL)
        header.pack(fill=tk.X, padx=10, pady=8)
        tk.Label(header, text="POSICIONES ABIERTAS — BingX Futures",
                 bg=BG_PANEL, fg=C_ORANGE, font=("Segoe UI", 15, "bold")).pack(side=tk.LEFT, padx=16, pady=10)

        refresh_btn = tk.Button(header, text="↻ Actualizar",
                                command=self._refresh_positions,
                                bg=C_ORANGE, fg="white", relief=tk.FLAT, cursor="hand2",
                                font=("Segoe UI", 10, "bold"), padx=10, pady=5)
        refresh_btn.pack(side=tk.RIGHT, padx=16, pady=10)

        # Tabla
        frame = tk.Frame(tab, bg=BG_PANEL)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 8))

        cols = ("Símbolo", "Lado", "Tamaño", "Entrada", "Precio Act.", "PnL No Real.", "Lev.", "Margen")
        self.pos_tree = ttk.Treeview(frame, columns=cols, show="headings", height=16)

        for col in cols:
            self.pos_tree.heading(col, text=col)
            self.pos_tree.column(col, width=110, anchor="center")

        style = ttk.Style()
        style.configure("Treeview", background=BG_WIDGET, foreground=FG_TEXT,
                        fieldbackground=BG_WIDGET, rowheight=26,
                        font=("Consolas", 9))
        style.configure("Treeview.Heading", background=BG_PANEL, foreground=C_ORANGE,
                        font=("Segoe UI", 9, "bold"))
        style.map("Treeview", background=[("selected", "#2a3560")])

        sb = ttk.Scrollbar(frame, orient="vertical", command=self.pos_tree.yview)
        self.pos_tree.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.pos_tree.pack(fill=tk.BOTH, expand=True)

        # Resumen
        self.pos_summary_lbl = tk.Label(tab, text="Sin posiciones abiertas",
                                        bg=BG_DARK, fg=FG_MUTED, font=("Segoe UI", 10))
        self.pos_summary_lbl.pack(pady=6)

    def _refresh_positions(self):
        # En modo demo/sin API, muestra mensaje
        for row in self.pos_tree.get_children():
            self.pos_tree.delete(row)

        api_key = self.cfg.get("api_key", "")
        if not api_key:
            self.pos_summary_lbl.configure(
                text="⚠  Configura tu API Key en Configuración → BingX para ver posiciones reales.",
                fg=C_YELLOW,
            )
            return

        # Placeholder: aquí iría la llamada real a la API de BingX
        self.pos_summary_lbl.configure(
            text="Posiciones cargadas en tiempo real (API conectada)",
            fg=C_GREEN,
        )

    # ══════════════════════════════════════════
    # TAB 3: ESTADÍSTICAS
    # ══════════════════════════════════════════

    def _tab_statistics(self):
        tab = ttk.Frame(self.notebook, style="Dark.TFrame")
        self.notebook.add(tab, text="  📊 Estadísticas  ")

        header = tk.Frame(tab, bg=BG_PANEL)
        header.pack(fill=tk.X, padx=10, pady=8)
        tk.Label(header, text="ESTADÍSTICAS — BingX Futures (independientes de MT5)",
                 bg=BG_PANEL, fg=C_ORANGE, font=("Segoe UI", 14, "bold")).pack(side=tk.LEFT, padx=16, pady=10)

        body = tk.Frame(tab, bg=BG_DARK)
        body.pack(fill=tk.BOTH, expand=True, padx=10)

        # Panel izquierdo: métricas
        left = tk.Frame(body, bg=BG_DARK, width=380)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 6))
        left.pack_propagate(False)

        # Panel derecho: gráfico
        right = tk.Frame(body, bg=BG_DARK)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._stats_metrics_panel(left)
        self._stats_chart_panel(right)

    def _stats_metrics_panel(self, parent):
        frame = tk.LabelFrame(parent, text="  MÉTRICAS DETALLADAS  ",
                              bg=BG_PANEL, fg=C_ORANGE,
                              font=("Segoe UI", 10, "bold"), relief=tk.FLAT)
        frame.pack(fill=tk.BOTH, expand=True, pady=4)

        metrics = [
            ("Total Trades",          "bx_st_total",  FG_TEXT),
            ("Victorias",             "bx_st_wins",   C_GREEN),
            ("Pérdidas",              "bx_st_losses", C_RED),
            ("Win Rate",              "bx_st_wr",     C_ORANGE),
            ("PnL Total (USDT)",      "bx_st_pnl",    C_BLUE),
            ("Mejor Trade (USDT)",    "bx_st_best",   C_GREEN),
            ("Peor Trade (USDT)",     "bx_st_worst",  C_RED),
            ("Racha actual",          "bx_st_streak", C_YELLOW),
        ]
        self._stat_lbls = {}
        for i, (label, attr, color) in enumerate(metrics):
            row = tk.Frame(frame, bg=BG_WIDGET)
            row.pack(fill=tk.X, padx=8, pady=3)
            tk.Label(row, text=label, bg=BG_WIDGET, fg=FG_MUTED,
                     font=("Segoe UI", 10), width=22, anchor="w").pack(side=tk.LEFT, padx=10, pady=6)
            lbl = tk.Label(row, text="—", bg=BG_WIDGET, fg=color,
                           font=("Segoe UI", 12, "bold"))
            lbl.pack(side=tk.RIGHT, padx=10)
            self._stat_lbls[attr] = lbl

    def _stats_chart_panel(self, parent):
        frame = tk.LabelFrame(parent, text="  GRÁFICOS DE RENDIMIENTO  ",
                              bg=BG_PANEL, fg=C_ORANGE,
                              font=("Segoe UI", 10, "bold"), relief=tk.FLAT)
        frame.pack(fill=tk.BOTH, expand=True, pady=4)

        if MATPLOTLIB_OK:
            self.bx_fig = Figure(figsize=(7, 5), facecolor=BG_PANEL)
            self.bx_canvas_mpl = FigureCanvasTkAgg(self.bx_fig, master=frame)
            self.bx_canvas_mpl.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
            self._draw_placeholder_chart()
        else:
            tk.Label(frame, text="Instala matplotlib para ver gráficos\n(pip install matplotlib)",
                     bg=BG_PANEL, fg=FG_MUTED, font=("Segoe UI", 11)).pack(expand=True)

    def _draw_placeholder_chart(self):
        if not MATPLOTLIB_OK:
            return
        self.bx_fig.clear()
        ax = self.bx_fig.add_subplot(111, facecolor=BG_WIDGET)
        ax.set_title("Curva de Equity BingX", color=FG_TEXT, fontsize=11)
        ax.set_xlabel("Trade #", color=FG_MUTED, fontsize=9)
        ax.set_ylabel("PnL Acumulado (USDT)", color=FG_MUTED, fontsize=9)
        ax.tick_params(colors=FG_MUTED)
        ax.grid(True, alpha=0.15, color=C_BLUE)
        ax.spines["bottom"].set_color(FG_MUTED)
        ax.spines["left"].set_color(FG_MUTED)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

        history = _load_history()
        if history:
            pnl_acc = []
            total = 0.0
            for t in history:
                total += t.get("pnl", 0.0)
                pnl_acc.append(total)
            color_line = C_GREEN if total >= 0 else C_RED
            ax.plot(range(1, len(pnl_acc) + 1), pnl_acc, color=color_line, linewidth=2)
            ax.fill_between(range(1, len(pnl_acc) + 1), pnl_acc, alpha=0.15, color=color_line)
        else:
            ax.text(0.5, 0.5, "Sin datos de trading aún",
                    ha="center", va="center", transform=ax.transAxes,
                    color=FG_MUTED, fontsize=12)

        self.bx_fig.tight_layout()
        self.bx_canvas_mpl.draw()

    # ══════════════════════════════════════════
    # TAB 4: HISTORIAL
    # ══════════════════════════════════════════

    def _tab_history(self):
        tab = ttk.Frame(self.notebook, style="Dark.TFrame")
        self.notebook.add(tab, text="  📋 Historial  ")

        header = tk.Frame(tab, bg=BG_PANEL)
        header.pack(fill=tk.X, padx=10, pady=8)
        tk.Label(header, text="HISTORIAL DE TRADES — BingX",
                 bg=BG_PANEL, fg=C_ORANGE, font=("Segoe UI", 14, "bold")).pack(side=tk.LEFT, padx=16, pady=10)

        refresh_btn = tk.Button(header, text="↻ Actualizar",
                                command=self._refresh_history,
                                bg=C_ORANGE, fg="white", relief=tk.FLAT, cursor="hand2",
                                font=("Segoe UI", 10, "bold"), padx=10, pady=5)
        refresh_btn.pack(side=tk.RIGHT, padx=16, pady=10)

        frame = tk.Frame(tab, bg=BG_PANEL)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 8))

        cols = ("Fecha/Hora", "Símbolo", "Dirección", "Tamaño", "Entrada", "Salida", "PnL (USDT)", "Resultado", "Estrategia")
        self.hist_tree = ttk.Treeview(frame, columns=cols, show="headings", height=20)

        widths = [140, 100, 80, 80, 90, 90, 110, 90, 140]
        for col, w in zip(cols, widths):
            self.hist_tree.heading(col, text=col)
            self.hist_tree.column(col, width=w, anchor="center")

        style = ttk.Style()
        style.configure("Treeview", background=BG_WIDGET, foreground=FG_TEXT,
                        fieldbackground=BG_WIDGET, rowheight=24, font=("Consolas", 9))
        style.configure("Treeview.Heading", background=BG_PANEL, foreground=C_ORANGE,
                        font=("Segoe UI", 9, "bold"))

        self.hist_tree.tag_configure("win",  background="#0d2a1a", foreground=C_GREEN)
        self.hist_tree.tag_configure("loss", background="#2a0d14", foreground=C_RED)

        xsb = ttk.Scrollbar(frame, orient="horizontal", command=self.hist_tree.xview)
        ysb = ttk.Scrollbar(frame, orient="vertical",   command=self.hist_tree.yview)
        self.hist_tree.configure(xscrollcommand=xsb.set, yscrollcommand=ysb.set)
        xsb.pack(side=tk.BOTTOM, fill=tk.X)
        ysb.pack(side=tk.RIGHT,  fill=tk.Y)
        self.hist_tree.pack(fill=tk.BOTH, expand=True)

        self._refresh_history()

    def _refresh_history(self):
        for row in self.hist_tree.get_children():
            self.hist_tree.delete(row)

        self.history = _load_history()
        for t in reversed(self.history):
            tag = "win" if t.get("result") == "WIN" else "loss"
            pnl = t.get("pnl", 0.0)
            pnl_str = f"+{pnl:.2f}" if pnl >= 0 else f"{pnl:.2f}"
            self.hist_tree.insert("", tk.END, tags=(tag,), values=(
                t.get("timestamp", "—"),
                t.get("symbol", "—"),
                t.get("direction", "—"),
                t.get("size", "—"),
                t.get("entry", "—"),
                t.get("exit", "—"),
                pnl_str,
                t.get("result", "—"),
                t.get("strategy", "—"),
            ))

    # ══════════════════════════════════════════
    # TAB 5: CONFIGURACIÓN
    # ══════════════════════════════════════════

    def _tab_config(self):
        tab = ttk.Frame(self.notebook, style="Dark.TFrame")
        self.notebook.add(tab, text="  ⚙ Configuración  ")

        canvas = tk.Canvas(tab, bg=BG_DARK, highlightthickness=0)
        sb = ttk.Scrollbar(tab, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(fill=tk.BOTH, expand=True)

        sf = tk.Frame(canvas, bg=BG_DARK)
        win_id = canvas.create_window(0, 0, anchor="nw", window=sf)

        def _on_cfg(_e):
            canvas.configure(scrollregion=canvas.bbox("all"))
        def _on_cv(e):
            canvas.itemconfig(win_id, width=e.width)

        sf.bind("<Configure>", _on_cfg)
        canvas.bind("<Configure>", _on_cv)

        self._cfg_vars = {}

        # API
        self._cfg_section(sf, "🔑 API BingX")
        for key, label, show in [("api_key", "API Key", True), ("api_secret", "API Secret", False)]:
            v = tk.StringVar(value=self.cfg.get(key, ""))
            self._cfg_vars[key] = v
            self._cfg_entry(sf, label, v, show_char="*" if not show else None)

        demo_v = tk.BooleanVar(value=self.cfg.get("demo_mode", True))
        self._cfg_vars["demo_mode"] = demo_v
        self._cfg_check(sf, "Modo Demo (Paper Trading)", demo_v)

        # Trading
        self._cfg_section(sf, "📈 Trading")
        for key, label, hint in [
            ("default_symbol",   "Símbolo",              "BTC-USDT, ETH-USDT..."),
            ("default_leverage", "Apalancamiento (1-125)","1 – 125"),
            ("risk_percent",     "Riesgo por trade (%)", "0.1 – 10.0"),
            ("max_positions",    "Máx. posiciones",      "1 – 10"),
        ]:
            v = tk.StringVar(value=str(self.cfg.get(key, "")))
            self._cfg_vars[key] = v
            self._cfg_entry(sf, label, v, hint=hint)

        margin_v = tk.StringVar(value=self.cfg.get("margin_type", "ISOLATED"))
        self._cfg_vars["margin_type"] = margin_v
        self._cfg_combo(sf, "Tipo de margen", margin_v, ["ISOLATED", "CROSS"])

        # Bot
        self._cfg_section(sf, "🤖 Parámetros del Bot")
        for key, label, hint in [
            ("min_confidence",   "Confianza mínima",         "0 – 100"),
            ("cooldown",         "Cooldown (seg)",            "10 – 600"),
            ("max_daily_trades", "Máx. trades diarios",      "1 – 100"),
            ("max_losses",       "Máx. pérdidas consecutivas","1 – 20"),
        ]:
            v = tk.StringVar(value=str(self.cfg.get(key, "")))
            self._cfg_vars[key] = v
            self._cfg_entry(sf, label, v, hint=hint)

        # Botón guardar
        tk.Button(
            sf, text="💾  Guardar Configuración BingX",
            command=self._save_bingx_cfg,
            bg=C_ORANGE, fg="white",
            font=("Segoe UI", 11, "bold"),
            relief=tk.FLAT, cursor="hand2",
            padx=16, pady=8, bd=0,
        ).pack(padx=16, pady=16, anchor="w")

        self.cfg_status_lbl = tk.Label(sf, text="", bg=BG_DARK, fg=C_GREEN, font=("Segoe UI", 10))
        self.cfg_status_lbl.pack(anchor="w", padx=16)

    def _cfg_section(self, parent, title):
        frame = tk.Frame(parent, bg=BG_PANEL)
        frame.pack(fill=tk.X, padx=10, pady=(12, 0))
        tk.Label(frame, text=title, bg=BG_PANEL, fg=C_ORANGE,
                 font=("Segoe UI", 11, "bold")).pack(side=tk.LEFT, padx=14, pady=7)
        tk.Frame(frame, bg=C_ORANGE, height=1).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)

    def _cfg_entry(self, parent, label, var, hint="", show_char=None):
        row = tk.Frame(parent, bg=BG_DARK)
        row.pack(fill=tk.X, padx=10, pady=3)
        tk.Label(row, text=label, bg=BG_DARK, fg=FG_TEXT,
                 font=("Segoe UI", 10), width=28, anchor="w").pack(side=tk.LEFT, padx=(16, 6))
        tk.Entry(row, textvariable=var, bg=BG_WIDGET, fg=FG_TEXT,
                 font=("Consolas", 10), relief=tk.FLAT, bd=0,
                 insertbackground=FG_TEXT, width=30,
                 show=show_char or "").pack(side=tk.LEFT, ipady=5, padx=(0, 8))
        if hint:
            tk.Label(row, text=hint, bg=BG_DARK, fg=FG_MUTED,
                     font=("Segoe UI", 8)).pack(side=tk.LEFT)

    def _cfg_check(self, parent, label, var):
        row = tk.Frame(parent, bg=BG_DARK)
        row.pack(fill=tk.X, padx=10, pady=3)
        tk.Checkbutton(row, text=label, variable=var,
                       bg=BG_DARK, fg=FG_TEXT, selectcolor=BG_WIDGET,
                       activebackground=BG_DARK, activeforeground=FG_TEXT,
                       font=("Segoe UI", 10), cursor="hand2").pack(side=tk.LEFT, padx=16)

    def _cfg_combo(self, parent, label, var, options):
        row = tk.Frame(parent, bg=BG_DARK)
        row.pack(fill=tk.X, padx=10, pady=3)
        tk.Label(row, text=label, bg=BG_DARK, fg=FG_TEXT,
                 font=("Segoe UI", 10), width=28, anchor="w").pack(side=tk.LEFT, padx=(16, 6))
        ttk.Combobox(row, textvariable=var, values=options, state="readonly",
                     width=16).pack(side=tk.LEFT, ipady=4)

    def _save_bingx_cfg(self):
        int_keys = {"default_leverage", "min_confidence", "cooldown",
                    "max_daily_trades", "max_losses", "max_positions"}
        float_keys = {"risk_percent"}
        errors = []
        for key, v in self._cfg_vars.items():
            raw = v.get()
            if isinstance(v, tk.BooleanVar):
                self.cfg[key] = v.get()
            elif key in int_keys:
                try:
                    self.cfg[key] = int(raw)
                except ValueError:
                    errors.append(f"{key}: '{raw}' no es un número entero")
            elif key in float_keys:
                try:
                    self.cfg[key] = float(raw)
                except ValueError:
                    errors.append(f"{key}: '{raw}' no es un número decimal")
            else:
                self.cfg[key] = str(raw)

        if errors:
            messagebox.showerror("Errores", "\n".join(errors))
            return

        try:
            with open(BINGX_CFG_FILE, "w") as f:
                json.dump(self.cfg, f, indent=4)
            # Actualizar badge
            demo = self.cfg.get("demo_mode", True)
            self.demo_badge.configure(
                text="  DEMO  " if demo else "  REAL  ",
                bg=C_YELLOW if demo else C_GREEN,
            )
            self.cfg_status_lbl.configure(
                text=f"✔ Guardado — {datetime.now().strftime('%H:%M:%S')}",
                fg=C_GREEN,
            )
            self.after(4000, lambda: self.cfg_status_lbl.configure(text=""))
        except Exception as e:
            messagebox.showerror("Error al guardar", str(e))

    # ══════════════════════════════════════════
    # TAB 6: SISTEMA
    # ══════════════════════════════════════════

    def _tab_system(self):
        tab = ttk.Frame(self.notebook, style="Dark.TFrame")
        self.notebook.add(tab, text="  ℹ Sistema  ")

        header = tk.Frame(tab, bg=BG_PANEL)
        header.pack(fill=tk.X, padx=10, pady=8)
        tk.Label(header, text="INFORMACIÓN DEL SISTEMA — BingX",
                 bg=BG_PANEL, fg=C_ORANGE, font=("Segoe UI", 14, "bold")).pack(side=tk.LEFT, padx=16, pady=10)

        body = tk.Frame(tab, bg=BG_DARK)
        body.pack(fill=tk.BOTH, expand=True, padx=10)

        left = tk.Frame(body, bg=BG_DARK, width=440)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 6))
        left.pack_propagate(False)

        right = tk.Frame(body, bg=BG_DARK)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Info panel
        info_frame = tk.LabelFrame(left, text="  INFORMACIÓN GENERAL  ",
                                   bg=BG_PANEL, fg=C_ORANGE,
                                   font=("Segoe UI", 10, "bold"), relief=tk.FLAT)
        info_frame.pack(fill=tk.X, pady=4)

        py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        rows = [
            ("Módulo",          "bingx_gui.py"),
            ("Versión",         VERSION),
            ("Plataforma",      "BingX Futures (Perpetuos)"),
            ("Python",          py_ver),
            ("Directorio",      _BASE_DIR),
            ("Config API",      "Configurada" if self.cfg.get("api_key") else "Sin API Key"),
            ("Modo",            "Demo" if self.cfg.get("demo_mode", True) else "Real"),
            ("Símbolo",         self.cfg.get("default_symbol", "—")),
            ("Apalancamiento",  f"{self.cfg.get('default_leverage', 1)}x"),
        ]
        for label, val in rows:
            row = tk.Frame(info_frame, bg=BG_WIDGET)
            row.pack(fill=tk.X, padx=8, pady=2)
            tk.Label(row, text=label + ":", bg=BG_WIDGET, fg=FG_MUTED,
                     font=("Segoe UI", 9), width=18, anchor="w").pack(side=tk.LEFT, padx=8, pady=5)
            color = C_GREEN if val not in ("Sin API Key", "Demo", "—") else (C_YELLOW if val == "Demo" else C_RED)
            tk.Label(row, text=val, bg=BG_WIDGET, fg=color,
                     font=("Consolas", 9)).pack(side=tk.LEFT, padx=6)

        # Files
        files_frame = tk.LabelFrame(left, text="  ARCHIVOS DE DATOS  ",
                                    bg=BG_PANEL, fg=C_ORANGE,
                                    font=("Segoe UI", 10, "bold"), relief=tk.FLAT)
        files_frame.pack(fill=tk.X, pady=(6, 0))

        file_rows = [
            ("bingx_config.json",  BINGX_CFG_FILE),
            ("bingx_stats.json",   BINGX_STATS_FILE),
            ("bingx_history.json", BINGX_HISTORY_FILE),
        ]
        for name, path in file_rows:
            exists = os.path.exists(path)
            row = tk.Frame(files_frame, bg=BG_WIDGET)
            row.pack(fill=tk.X, padx=8, pady=2)
            tk.Label(row, text=name, bg=BG_WIDGET, fg=FG_TEXT,
                     font=("Consolas", 9), width=22, anchor="w").pack(side=tk.LEFT, padx=8, pady=5)
            tk.Label(row, text="✔ existe" if exists else "✗ no existe",
                     bg=BG_WIDGET, fg=C_GREEN if exists else C_RED,
                     font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=6)

        # API Status
        api_frame = tk.LabelFrame(right, text="  ESTADO DE LA API  ",
                                  bg=BG_PANEL, fg=C_ORANGE,
                                  font=("Segoe UI", 10, "bold"), relief=tk.FLAT)
        api_frame.pack(fill=tk.BOTH, expand=True, pady=4)

        self.api_status_text = scrolledtext.ScrolledText(
            api_frame, bg=BG_WIDGET, fg=FG_TEXT,
            font=("Consolas", 9), relief=tk.FLAT, wrap=tk.WORD,
            state=tk.DISABLED,
        )
        self.api_status_text.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        tk.Button(
            api_frame, text="↻ Probar Conexión API",
            command=self._test_api,
            bg=C_ORANGE, fg="white", relief=tk.FLAT, cursor="hand2",
            font=("Segoe UI", 10, "bold"), padx=10, pady=5,
        ).pack(pady=8)

        self._update_api_status("Haz clic en 'Probar Conexión API' para verificar el estado.")

    def _test_api(self):
        api_key    = self.cfg.get("api_key", "")
        api_secret = self.cfg.get("api_secret", "")

        if not api_key or not api_secret:
            self._update_api_status(
                "⚠ No hay API Key configurada.\n\n"
                "Ve a la pestaña Configuración e introduce tu API Key y Secret de BingX.\n"
                "Puedes generar las claves desde:\n"
                "  BingX → Perfil → Gestión de API\n",
                color=C_YELLOW,
            )
            return

        self._update_api_status("🔄 Probando conexión con BingX...", color=C_BLUE)
        # Placeholder: aquí iría la llamada real a la API
        self.after(1500, lambda: self._update_api_status(
            "✔ API Key detectada.\n\n"
            "La integración completa con la API de BingX se activará en la próxima versión.\n"
            "Por ahora el sistema opera en modo simulación.\n\n"
            f"API Key: {api_key[:8]}{'*' * (len(api_key) - 8 if len(api_key) > 8 else 0)}\n"
            f"Modo: {'Demo' if self.cfg.get('demo_mode', True) else 'Real'}\n"
            f"Símbolo: {self.cfg.get('default_symbol', 'BTC-USDT')}\n",
            color=C_GREEN,
        ))

    def _update_api_status(self, text, color=FG_TEXT):
        self.api_status_text.configure(state=tk.NORMAL)
        self.api_status_text.delete(1.0, tk.END)
        self.api_status_text.insert(tk.END, text)
        self.api_status_text.configure(fg=color, state=tk.DISABLED)

    # ──────────────────────────────────────────
    # Lógica del bot (ciclo simulado)
    # ──────────────────────────────────────────

    def _start_bot(self):
        if self.bot_state == "RUNNING":
            return

        self.bot_state = "RUNNING"
        self.start_btn.configure(state=tk.DISABLED)
        self.stop_btn.configure(state=tk.NORMAL)
        self.status_canvas.itemconfig(self.status_oval, fill=C_GREEN)
        self.status_lbl.configure(text="ACTIVO", fg=C_GREEN)

        self._log(f"[{datetime.now().strftime('%H:%M:%S')}] Bot BingX iniciado", "ok")
        self._log(f"  Modo: {'Demo' if self.cfg.get('demo_mode', True) else 'REAL'}", "info")
        self._log(f"  Símbolo: {self.cfg.get('default_symbol', 'BTC-USDT')}", "info")
        self._log(f"  Apalancamiento: {self.cfg.get('default_leverage', 5)}x", "info")

        if not self.cfg.get("api_key"):
            self._log("  ⚠ Sin API Key — funcionando en modo simulación", "warn")

        self.bot_thread = threading.Thread(target=self._bot_loop, daemon=True)
        self.bot_thread.start()

    def _stop_bot(self):
        self.bot_state = "STOPPED"
        self.start_btn.configure(state=tk.NORMAL)
        self.stop_btn.configure(state=tk.DISABLED)
        self.status_canvas.itemconfig(self.status_oval, fill=C_RED)
        self.status_lbl.configure(text="DETENIDO", fg=C_RED)
        self._log(f"[{datetime.now().strftime('%H:%M:%S')}] Bot BingX detenido", "warn")

    def _bot_loop(self):
        """Ciclo principal del bot (placeholder hasta integración real de la API)."""
        cycle = 0
        while self.bot_state == "RUNNING":
            cycle += 1
            ts = datetime.now().strftime("%H:%M:%S")
            self._log(f"[{ts}] Ciclo #{cycle} — analizando mercado...", "dim")
            time.sleep(self.cfg.get("cooldown", 60))

    # ──────────────────────────────────────────
    # Log
    # ──────────────────────────────────────────

    def _log(self, msg, tag="dim"):
        def _insert():
            if not self.log_text.winfo_exists():
                return
            self.log_text.configure(state=tk.NORMAL)
            self.log_text.insert(tk.END, msg + "\n", tag)
            self.log_text.see(tk.END)
            self.log_text.configure(state=tk.DISABLED)
        self.after(0, _insert)

    # ──────────────────────────────────────────
    # Auto-actualización
    # ──────────────────────────────────────────

    def _auto_update(self):
        """Auto-actualización con guarda contra widgets destruidos."""
        try:
            if not self.winfo_exists():
                return
        except Exception:
            return

        try:
            self.stats = _load_stats()
            self._update_stat_labels()

            wr = (self.stats["wins"] / self.stats["total_trades"] * 100) \
                if self.stats["total_trades"] > 0 else 0.0
            self.bx_lbl_total.configure(text=str(self.stats["total_trades"]))
            self.bx_lbl_wins.configure(text=str(self.stats["wins"]))
            self.bx_lbl_losses.configure(text=str(self.stats["losses"]))
            self.bx_lbl_wr.configure(text=f"{wr:.1f}%")

            self._update_market_text()
        except Exception:
            pass

        # Reprogramar solo si el frame sigue existiendo
        try:
            if self.winfo_exists():
                self.after(5000, self._auto_update)
        except Exception:
            pass

    def _update_stat_labels(self):
        s = self.stats
        total = s.get("total_trades", 0)
        wr    = (s.get("wins", 0) / total * 100) if total > 0 else 0.0
        pnl   = s.get("total_pnl", 0.0)

        updates = {
            "bx_st_total":  (str(total),                   FG_TEXT),
            "bx_st_wins":   (str(s.get("wins", 0)),        C_GREEN),
            "bx_st_losses": (str(s.get("losses", 0)),      C_RED),
            "bx_st_wr":     (f"{wr:.1f}%",                 C_ORANGE),
            "bx_st_pnl":    (f"{pnl:+.2f}",               C_GREEN if pnl >= 0 else C_RED),
            "bx_st_best":   (f"+{s.get('best_trade',0):.2f}", C_GREEN),
            "bx_st_worst":  (f"{s.get('worst_trade',0):.2f}", C_RED),
            "bx_st_streak": (
                f"{s.get('current_streak',0)} {s.get('streak_type','—')}",
                C_GREEN if s.get("streak_type") == "WIN" else C_RED,
            ),
        }
        for attr, (text, color) in updates.items():
            if hasattr(self, "_stat_lbls") and attr in self._stat_lbls:
                self._stat_lbls[attr].configure(text=text, fg=color)

    def _update_market_text(self):
        try:
            ts   = datetime.now().strftime("%H:%M:%S")
            sym  = self.cfg.get("default_symbol", "BTC-USDT")
            lev  = self.cfg.get("default_leverage", 5)
            demo = self.cfg.get("demo_mode", True)

            content = (
                f"  Hora:          {ts}\n"
                f"  Símbolo:       {sym}\n"
                f"  Apalancamiento:{lev}x\n"
                f"  Modo:          {'Demo (Simulación)' if demo else 'REAL'}\n"
                f"  Bot:           {self.bot_state}\n"
            )
            if not self.cfg.get("api_key"):
                content += "\n  ⚠ Configura tu API Key para datos en tiempo real"

            self.market_text.configure(state=tk.NORMAL)
            self.market_text.delete(1.0, tk.END)
            self.market_text.insert(tk.END, content)
            self.market_text.configure(state=tk.DISABLED)
        except Exception:
            pass

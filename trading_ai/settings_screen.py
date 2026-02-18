"""
settings_screen.py - Pantalla de Configuración del Sistema de Trading Unificado

Pestañas:
  1. General         – Preferencias globales de la aplicación
  2. MetaTrader 5    – Rutas, parámetros del bot MT5
  3. BingX Futures   – API Key/Secret, símbolo, apalancamiento
  4. Telegram        – Token y chat_id del bot (preparado para integración futura)
  5. Acerca de       – Información del sistema y licencia
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import json
import os
import sys
from datetime import datetime

# ──────────────────────────────────────────────
# Colores (idénticos al resto del sistema)
# ──────────────────────────────────────────────
BG_DARK   = "#0a0e27"
BG_PANEL  = "#151b3d"
BG_WIDGET = "#1e2749"
FG_TEXT   = "#e0e6ff"
FG_MUTED  = "#8b9dc3"
C_BLUE    = "#4895ef"
C_GREEN   = "#06ffa5"
C_RED     = "#ff006e"
C_YELLOW  = "#ffbe0b"
C_ORANGE  = "#ff9a00"

VERSION = "3.0.0"
AUTHOR  = "Daniel Hernández"

_BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
MT5_CFG_FILE   = os.path.join(_BASE_DIR, "bot_config.json")
BINGX_CFG_FILE = os.path.join(_BASE_DIR, "bingx_config.json")
APP_CFG_FILE   = os.path.join(_BASE_DIR, "app_config.json")

# Configuración BingX por defecto
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
    "telegram_token":   "",
    "telegram_chat_id": "",
}

# Configuración de la app por defecto
APP_DEFAULTS = {
    "start_on_home":      True,
    "remember_last_panel": False,
    "last_panel":         "home",
    "telegram_token":     "",
    "telegram_chat_id":   "",
}


def _load_json(path, defaults):
    try:
        if os.path.exists(path):
            with open(path, "r") as f:
                data = json.load(f)
            for k, v in defaults.items():
                data.setdefault(k, v)
            return data
    except Exception:
        pass
    return dict(defaults)


def _save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=4)


class SettingsScreen(tk.Frame):
    """Pantalla de configuración con pestañas por sección."""

    def __init__(self, parent, root, on_back, mode=None):
        super().__init__(parent, bg=BG_DARK)
        self.root    = root
        self.on_back = on_back
        self.mode    = mode   # None=all, 'mt5', 'bingx'

        # Cargar configuraciones
        self.mt5_cfg   = _load_json(MT5_CFG_FILE,   {})
        self.bingx_cfg = _load_json(BINGX_CFG_FILE, BINGX_DEFAULTS)
        self.app_cfg   = _load_json(APP_CFG_FILE,   APP_DEFAULTS)

        self._vars_bingx = {}
        self._vars_app   = {}
        self._vars_mt5   = {}

        self._build()

    # ──────────────────────────────────────────
    # Construcción principal
    # ──────────────────────────────────────────

    def _build(self):
        self._build_top_bar()
        self._setup_styles()
        self._build_notebook()
        self._build_bottom_bar()

    def _build_top_bar(self):
        bar = tk.Frame(self, bg=BG_PANEL, height=58)
        bar.pack(fill=tk.X)
        bar.pack_propagate(False)
        tk.Frame(bar, bg=C_BLUE, height=2).place(relx=0, rely=1.0, anchor="sw", relwidth=1)

        # Botón volver
        back_btn = tk.Button(
            bar, text="◀  Menú Principal",
            command=self.on_back,
            bg=BG_WIDGET, fg=FG_TEXT,
            font=("Segoe UI", 10, "bold"),
            relief=tk.FLAT, cursor="hand2",
            padx=14, pady=6, bd=0,
            activebackground=C_BLUE,
            activeforeground="white",
        )
        back_btn.pack(side=tk.LEFT, padx=16, pady=10)

        tk.Label(
            bar, text="⚙  Configuración del Sistema",
            bg=BG_PANEL, fg=C_BLUE,
            font=("Segoe UI", 14, "bold"),
        ).pack(side=tk.LEFT, padx=14)

        # Reloj
        self.clock = tk.Label(bar, text="", bg=BG_PANEL, fg=FG_MUTED, font=("Consolas", 10))
        self.clock.pack(side=tk.RIGHT, padx=20)
        self._tick_clock()

    def _tick_clock(self):
        self.clock.configure(text=datetime.now().strftime("%Y-%m-%d   %H:%M:%S"))
        self.after(1000, self._tick_clock)

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TNotebook", background=BG_DARK, borderwidth=0)
        style.configure("TNotebook.Tab",
                        background=BG_PANEL, foreground=FG_TEXT,
                        padding=[18, 8], font=("Segoe UI", 11, "bold"))
        style.map("TNotebook.Tab",
                  background=[("selected", BG_WIDGET)],
                  foreground=[("selected", C_BLUE)])
        style.configure("Dark.TFrame", background=BG_DARK)

    def _build_notebook(self):
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=8)

        if self.mode is None or self.mode == "general":
            self._tab_general()

        if self.mode is None or self.mode == "mt5":
            self._tab_mt5()

        if self.mode is None or self.mode == "bingx":
            self._tab_bingx()

        if self.mode is None:
            self._tab_telegram()
            self._tab_about()

    def _build_bottom_bar(self):
        bar = tk.Frame(self, bg=BG_PANEL, height=52)
        bar.pack(fill=tk.X, side=tk.BOTTOM)
        bar.pack_propagate(False)
        tk.Frame(bar, bg=C_BLUE, height=1).pack(fill=tk.X)

        inner = tk.Frame(bar, bg=BG_PANEL)
        inner.pack(fill=tk.BOTH, expand=True, padx=16)

        self.status_lbl = tk.Label(
            inner, text="", bg=BG_PANEL, fg=C_GREEN, font=("Segoe UI", 10),
        )
        self.status_lbl.pack(side=tk.LEFT, pady=14)

        # Botón guardar todo
        save_btn = tk.Button(
            inner, text="💾  Guardar Todo",
            command=self._save_all,
            bg=C_GREEN, fg="#0a0e27",
            font=("Segoe UI", 11, "bold"),
            relief=tk.FLAT, cursor="hand2",
            padx=16, pady=6, bd=0,
            activebackground="#04d48e",
        )
        save_btn.pack(side=tk.RIGHT, pady=10, padx=8)

        cancel_btn = tk.Button(
            inner, text="✕  Cancelar",
            command=self.on_back,
            bg=BG_WIDGET, fg=FG_TEXT,
            font=("Segoe UI", 10, "bold"),
            relief=tk.FLAT, cursor="hand2",
            padx=12, pady=6, bd=0,
        )
        cancel_btn.pack(side=tk.RIGHT, pady=10, padx=4)

    # ──────────────────────────────────────────
    # Tab: General
    # ──────────────────────────────────────────

    def _tab_general(self):
        tab = ttk.Frame(self.notebook, style="Dark.TFrame")
        self.notebook.add(tab, text="  ◈ General  ")

        canvas = tk.Canvas(tab, bg=BG_DARK, highlightthickness=0)
        canvas.pack(fill=tk.BOTH, expand=True)

        frame = tk.Frame(canvas, bg=BG_DARK)
        canvas.create_window(0, 0, anchor="nw", window=frame)

        self._section_title(frame, "Preferencias Generales")

        # start_on_home
        v = tk.BooleanVar(value=self.app_cfg.get("start_on_home", True))
        self._vars_app["start_on_home"] = v
        self._checkbox_row(frame, "Iniciar siempre en el Menú Principal", v)

        # remember_last_panel
        v2 = tk.BooleanVar(value=self.app_cfg.get("remember_last_panel", False))
        self._vars_app["remember_last_panel"] = v2
        self._checkbox_row(frame, "Recordar último panel abierto", v2)

        self._section_title(frame, "Información del Sistema")
        info_rows = [
            ("Versión del sistema", VERSION),
            ("Desarrollador",       AUTHOR),
            ("Python",              f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"),
            ("Directorio base",     _BASE_DIR),
        ]
        for label, val in info_rows:
            self._info_row(frame, label, val)

    # ──────────────────────────────────────────
    # Tab: MetaTrader 5
    # ──────────────────────────────────────────

    def _tab_mt5(self):
        tab = ttk.Frame(self.notebook, style="Dark.TFrame")
        self.notebook.add(tab, text="  📈 MetaTrader 5  ")

        self._section_title(tab, "Parámetros del Bot MT5")
        self._note(tab, "Estos valores corresponden a bot_config.json y controlan el comportamiento del bot MT5.")

        fields = [
            ("min_confidence",        "Confianza mínima (0-100)",          "int",   0,   100),
            ("cooldown",              "Cooldown entre ciclos (seg)",        "int",   5,   300),
            ("max_daily_trades",      "Máx. trades diarios",               "int",   1,   200),
            ("max_losses",            "Máx. pérdidas consecutivas",        "int",   1,   20),
            ("lot_size",              "Tamaño de lote",                    "float", 0.01,10.0),
            ("max_concurrent_trades", "Máx. trades simultáneos",           "int",   1,   10),
            ("min_signal_interval",   "Intervalo mínimo señal (seg)",      "int",   10,  600),
        ]

        for key, label, ftype, mn, mx in fields:
            val = self.mt5_cfg.get(key, mn)
            v = tk.StringVar(value=str(val))
            self._vars_mt5[key] = (v, ftype)
            self._entry_row(tab, label, v, f"{mn} – {mx}")

        bool_fields = [
            ("avoid_repeat_strategy", "Evitar estrategia repetida"),
            ("auto_optimize",         "Auto-optimización con ML"),
        ]
        for key, label in bool_fields:
            v = tk.BooleanVar(value=bool(self.mt5_cfg.get(key, True)))
            self._vars_mt5[key] = (v, "bool")
            self._checkbox_row(tab, label, v)

        self._section_title(tab, "Horario de Trading")
        for key, label in [("start_hour", "Hora de inicio"), ("end_hour", "Hora de fin")]:
            v = tk.StringVar(value=str(self.mt5_cfg.get(key, "00:00")))
            self._vars_mt5[key] = (v, "str")
            self._entry_row(tab, label, v, "HH:MM")

    # ──────────────────────────────────────────
    # Tab: BingX Futures
    # ──────────────────────────────────────────

    def _tab_bingx(self):
        tab = ttk.Frame(self.notebook, style="Dark.TFrame")
        self.notebook.add(tab, text="  🔮 BingX Futures  ")

        scroll_canvas = tk.Canvas(tab, bg=BG_DARK, highlightthickness=0)
        scrollbar = ttk.Scrollbar(tab, orient="vertical", command=scroll_canvas.yview)
        scroll_canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_canvas.pack(fill=tk.BOTH, expand=True)

        sf = tk.Frame(scroll_canvas, bg=BG_DARK)
        win_id = scroll_canvas.create_window(0, 0, anchor="nw", window=sf)

        def _on_frame_configure(_e):
            scroll_canvas.configure(scrollregion=scroll_canvas.bbox("all"))

        def _on_canvas_configure(e):
            scroll_canvas.itemconfig(win_id, width=e.width)

        sf.bind("<Configure>", _on_frame_configure)
        scroll_canvas.bind("<Configure>", _on_canvas_configure)

        # ── Sección: API ──
        self._section_title(sf, "🔑 Credenciales de API BingX")
        self._note(sf, "Genera tu API Key en: BingX → Perfil → Gestión de API")

        for key, label, show in [
            ("api_key",    "API Key",    True),
            ("api_secret", "API Secret", False),
        ]:
            v = tk.StringVar(value=self.bingx_cfg.get(key, ""))
            self._vars_bingx[key] = v
            self._entry_row(sf, label, v, "Introduce tu clave", show_char="*" if not show else None)

        demo_v = tk.BooleanVar(value=self.bingx_cfg.get("demo_mode", True))
        self._vars_bingx["demo_mode"] = demo_v
        self._checkbox_row(sf, "Modo Demo (Paper Trading — sin dinero real)", demo_v)

        # ── Sección: Trading ──
        self._section_title(sf, "⚙ Parámetros de Trading")

        sym_v = tk.StringVar(value=self.bingx_cfg.get("default_symbol", "BTC-USDT"))
        self._vars_bingx["default_symbol"] = sym_v
        self._entry_row(sf, "Símbolo por defecto", sym_v, "Ej: BTC-USDT, ETH-USDT")

        lev_v = tk.StringVar(value=str(self.bingx_cfg.get("default_leverage", 5)))
        self._vars_bingx["default_leverage"] = lev_v
        self._entry_row(sf, "Apalancamiento (1-125x)", lev_v, "1 – 125")

        margin_opts = ["ISOLATED", "CROSS"]
        margin_v = tk.StringVar(value=self.bingx_cfg.get("margin_type", "ISOLATED"))
        self._vars_bingx["margin_type"] = margin_v
        self._combo_row(sf, "Tipo de margen", margin_v, margin_opts)

        risk_v = tk.StringVar(value=str(self.bingx_cfg.get("risk_percent", 1.0)))
        self._vars_bingx["risk_percent"] = risk_v
        self._entry_row(sf, "Riesgo por trade (%)", risk_v, "0.1 – 10.0")

        # ── Sección: Bot ──
        self._section_title(sf, "🤖 Parámetros del Bot BingX")

        int_fields_bx = [
            ("min_confidence",   "Confianza mínima (0-100)",     "0 – 100"),
            ("cooldown",         "Cooldown (seg)",                "10 – 600"),
            ("max_daily_trades", "Máx. trades diarios",          "1 – 100"),
            ("max_losses",       "Máx. pérdidas consecutivas",   "1 – 20"),
            ("max_positions",    "Máx. posiciones simultáneas",  "1 – 10"),
        ]
        for key, label, hint in int_fields_bx:
            v = tk.StringVar(value=str(self.bingx_cfg.get(key, 3)))
            self._vars_bingx[key] = v
            self._entry_row(sf, label, v, hint)

    # ──────────────────────────────────────────
    # Tab: Telegram
    # ──────────────────────────────────────────

    def _tab_telegram(self):
        tab = ttk.Frame(self.notebook, style="Dark.TFrame")
        self.notebook.add(tab, text="  ✈ Telegram  ")

        self._section_title(tab, "Bot de Telegram (próximamente)")
        self._note(tab, (
            "Configura el bot de Telegram para recibir notificaciones de trades, "
            "alertas de riesgo y reportes de rendimiento directamente en tu teléfono.\n\n"
            "Pasos para obtener el Token:\n"
            "  1. Abre Telegram y busca @BotFather\n"
            "  2. Envía /newbot y sigue las instrucciones\n"
            "  3. Copia el token que te entrega BotFather\n\n"
            "Para obtener tu Chat ID:\n"
            "  1. Envía un mensaje a tu bot\n"
            "  2. Visita: https://api.telegram.org/bot<TOKEN>/getUpdates\n"
            "  3. Copia el valor de 'chat' → 'id'"
        ))

        tg_token_v = tk.StringVar(value=self.app_cfg.get("telegram_token", ""))
        self._vars_app["telegram_token"] = tg_token_v
        self._entry_row(tab, "Token del Bot", tg_token_v, "123456:ABCdef...")

        tg_chat_v = tk.StringVar(value=self.app_cfg.get("telegram_chat_id", ""))
        self._vars_app["telegram_chat_id"] = tg_chat_v
        self._entry_row(tab, "Chat ID", tg_chat_v, "Tu ID numérico de Telegram")

        # Botón de prueba (placeholder)
        test_btn = tk.Button(
            tab, text="✈  Enviar mensaje de prueba",
            command=self._test_telegram,
            bg=C_BLUE, fg="white",
            font=("Segoe UI", 10, "bold"),
            relief=tk.FLAT, cursor="hand2",
            padx=14, pady=7, bd=0,
        )
        test_btn.pack(anchor="w", padx=26, pady=10)

    def _test_telegram(self):
        messagebox.showinfo(
            "Telegram",
            "La integración de Telegram estará disponible en la próxima versión.\n\n"
            "Guarda el token y el chat ID para cuando se active la funcionalidad.",
        )

    # ──────────────────────────────────────────
    # Tab: Acerca de
    # ──────────────────────────────────────────

    def _tab_about(self):
        tab = ttk.Frame(self.notebook, style="Dark.TFrame")
        self.notebook.add(tab, text="  ℹ Acerca de  ")

        frame = tk.Frame(tab, bg=BG_DARK)
        frame.pack(expand=True)

        tk.Label(frame, text="⬡", bg=BG_DARK, fg=C_BLUE,
                 font=("Segoe UI", 60)).pack(pady=(30, 6))

        tk.Label(frame, text="Trading AI Bot", bg=BG_DARK, fg=FG_TEXT,
                 font=("Segoe UI", 28, "bold")).pack()

        tk.Label(frame, text=f"Versión {VERSION}", bg=BG_DARK, fg=C_GREEN,
                 font=("Segoe UI", 14)).pack(pady=4)

        tk.Frame(frame, bg=C_BLUE, height=1, width=400).pack(pady=14)

        rows = [
            ("Desarrollado por",  AUTHOR),
            ("Plataformas",       "MetaTrader 5  |  BingX Futures"),
            ("Tecnologías",       "Python  •  Tkinter  •  Machine Learning"),
            ("Módulos IA",        "Decisión contextual, aprendizaje adaptativo, backtesting"),
        ]
        for label, val in rows:
            r = tk.Frame(frame, bg=BG_DARK)
            r.pack(pady=3)
            tk.Label(r, text=f"{label}:", bg=BG_DARK, fg=FG_MUTED,
                     font=("Segoe UI", 11), width=20, anchor="e").pack(side=tk.LEFT)
            tk.Label(r, text=val, bg=BG_DARK, fg=FG_TEXT,
                     font=("Segoe UI", 11)).pack(side=tk.LEFT, padx=10)

        tk.Frame(frame, bg=C_BLUE, height=1, width=400).pack(pady=14)

        tk.Label(
            frame,
            text="Sistema de trading algorítmico con inteligencia artificial,\n"
                 "diseñado para operar de forma autónoma con gestión de riesgo inteligente.",
            bg=BG_DARK, fg=FG_MUTED, font=("Segoe UI", 10),
            justify=tk.CENTER,
        ).pack(pady=6)

    # ──────────────────────────────────────────
    # Guardar
    # ──────────────────────────────────────────

    def _save_all(self):
        try:
            errors = []

            # Guardar MT5
            for key, val_tuple in self._vars_mt5.items():
                v, ftype = val_tuple
                raw = v.get() if not isinstance(v, tk.BooleanVar) else v.get()
                if ftype == "int":
                    try:
                        self.mt5_cfg[key] = int(raw)
                    except ValueError:
                        errors.append(f"MT5 → {key}: valor inválido '{raw}'")
                elif ftype == "float":
                    try:
                        self.mt5_cfg[key] = float(raw)
                    except ValueError:
                        errors.append(f"MT5 → {key}: valor inválido '{raw}'")
                elif ftype == "bool":
                    self.mt5_cfg[key] = bool(raw)
                else:
                    self.mt5_cfg[key] = str(raw)

            if not errors:
                _save_json(MT5_CFG_FILE, self.mt5_cfg)

            # Guardar BingX
            for key, v in self._vars_bingx.items():
                raw = v.get()
                if isinstance(v, tk.BooleanVar):
                    self.bingx_cfg[key] = bool(raw)
                elif key in ("default_leverage", "min_confidence", "cooldown",
                             "max_daily_trades", "max_losses", "max_positions"):
                    try:
                        self.bingx_cfg[key] = int(raw)
                    except ValueError:
                        errors.append(f"BingX → {key}: valor inválido '{raw}'")
                elif key == "risk_percent":
                    try:
                        self.bingx_cfg[key] = float(raw)
                    except ValueError:
                        errors.append(f"BingX → {key}: valor inválido '{raw}'")
                else:
                    self.bingx_cfg[key] = str(raw)

            if not errors:
                _save_json(BINGX_CFG_FILE, self.bingx_cfg)

            # Guardar App
            for key, v in self._vars_app.items():
                if isinstance(v, tk.BooleanVar):
                    self.app_cfg[key] = v.get()
                else:
                    self.app_cfg[key] = v.get()

            if not errors:
                _save_json(APP_CFG_FILE, self.app_cfg)

            if errors:
                messagebox.showerror("Errores de validación", "\n".join(errors))
            else:
                self.status_lbl.configure(
                    text=f"✔  Configuración guardada — {datetime.now().strftime('%H:%M:%S')}",
                    fg=C_GREEN,
                )
                self.after(4000, lambda: self.status_lbl.configure(text=""))

        except Exception as e:
            messagebox.showerror("Error al guardar", str(e))

    # ──────────────────────────────────────────
    # Widgets auxiliares
    # ──────────────────────────────────────────

    def _section_title(self, parent, text):
        frame = tk.Frame(parent, bg=BG_PANEL)
        frame.pack(fill=tk.X, padx=10, pady=(14, 0))
        tk.Label(frame, text=text, bg=BG_PANEL, fg=C_BLUE,
                 font=("Segoe UI", 12, "bold")).pack(side=tk.LEFT, padx=14, pady=8)
        tk.Frame(frame, bg=C_BLUE, height=1).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)

    def _note(self, parent, text):
        tk.Label(
            parent, text=text,
            bg=BG_DARK, fg=FG_MUTED,
            font=("Segoe UI", 9),
            justify=tk.LEFT, wraplength=900,
        ).pack(anchor="w", padx=26, pady=(4, 8))

    def _entry_row(self, parent, label, var, hint="", show_char=None):
        row = tk.Frame(parent, bg=BG_DARK)
        row.pack(fill=tk.X, padx=10, pady=3)

        tk.Label(row, text=label, bg=BG_DARK, fg=FG_TEXT,
                 font=("Segoe UI", 10), width=32, anchor="w").pack(side=tk.LEFT, padx=(16, 6))

        entry = tk.Entry(
            row, textvariable=var,
            bg=BG_WIDGET, fg=FG_TEXT,
            font=("Consolas", 10),
            relief=tk.FLAT, bd=0,
            insertbackground=FG_TEXT,
            width=36,
            show=show_char or "",
        )
        entry.pack(side=tk.LEFT, ipady=5, padx=(0, 8))

        if hint:
            tk.Label(row, text=hint, bg=BG_DARK, fg=FG_MUTED,
                     font=("Segoe UI", 8)).pack(side=tk.LEFT)

    def _checkbox_row(self, parent, label, var):
        row = tk.Frame(parent, bg=BG_DARK)
        row.pack(fill=tk.X, padx=10, pady=3)
        cb = tk.Checkbutton(
            row, text=label,
            variable=var,
            bg=BG_DARK, fg=FG_TEXT,
            selectcolor=BG_WIDGET,
            activebackground=BG_DARK,
            activeforeground=FG_TEXT,
            font=("Segoe UI", 10),
            cursor="hand2",
        )
        cb.pack(side=tk.LEFT, padx=16)

    def _combo_row(self, parent, label, var, options):
        row = tk.Frame(parent, bg=BG_DARK)
        row.pack(fill=tk.X, padx=10, pady=3)

        tk.Label(row, text=label, bg=BG_DARK, fg=FG_TEXT,
                 font=("Segoe UI", 10), width=32, anchor="w").pack(side=tk.LEFT, padx=(16, 6))

        style = ttk.Style()
        style.configure("Dark.TCombobox",
                         fieldbackground=BG_WIDGET, background=BG_PANEL,
                         foreground=FG_TEXT, arrowcolor=C_BLUE)

        cb = ttk.Combobox(row, textvariable=var, values=options,
                          state="readonly", width=18, style="Dark.TCombobox")
        cb.pack(side=tk.LEFT, ipady=4)

    def _info_row(self, parent, label, val):
        row = tk.Frame(parent, bg=BG_DARK)
        row.pack(fill=tk.X, padx=10, pady=2)
        tk.Label(row, text=label + ":", bg=BG_DARK, fg=FG_MUTED,
                 font=("Segoe UI", 10), width=28, anchor="w").pack(side=tk.LEFT, padx=(16, 6))
        tk.Label(row, text=val, bg=BG_DARK, fg=FG_TEXT,
                 font=("Consolas", 10)).pack(side=tk.LEFT)

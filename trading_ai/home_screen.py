"""
home_screen.py - Pantalla de inicio del Sistema de Trading Unificado

Características:
  - Logo animado del bot
  - Tarjetas de acceso a MT5 y BingX Futures
  - Botón de configuración general
  - Footer con información del sistema, versión y autor
  - Reloj en tiempo real
  - Indicadores de estado de cada plataforma
"""

import tkinter as tk
from tkinter import ttk
from datetime import datetime
import sys
import os
import json
import math

# ──────────────────────────────────────────────
# Paleta de colores (igual que bot_gui_professional)
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

VERSION      = "3.0.0"
AUTHOR       = "Daniel Hernández"
SYSTEM_NAME  = "Trading AI System"

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MT5_STATUS_FILE  = "/home/travieso/.wine/drive_c/Program Files/MetaTrader 5/MQL5/Files/bot_status.json"
BINGX_CFG_FILE   = os.path.join(_BASE_DIR, "bingx_config.json")


class HomeScreen(tk.Frame):
    """Pantalla principal de inicio / menú principal."""

    def __init__(self, parent, on_mt5, on_bingx, on_settings):
        super().__init__(parent, bg=BG_DARK)
        self.on_mt5      = on_mt5
        self.on_bingx    = on_bingx
        self.on_settings = on_settings

        self._build()
        self._start_clock()
        self._check_statuses()

    # ──────────────────────────────────────────
    # Construcción principal
    # ──────────────────────────────────────────

    def _build(self):
        # ── Barra superior ──────────────────────
        self._build_top_bar()

        # ── Zona central (expandible) ──────────
        center = tk.Frame(self, bg=BG_DARK)
        center.pack(fill=tk.BOTH, expand=True)

        # Espaciador superior
        tk.Frame(center, bg=BG_DARK).pack(expand=True, fill=tk.BOTH)

        # Bloque de contenido centrado
        content = tk.Frame(center, bg=BG_DARK)
        content.pack(anchor="center")

        self._build_logo(content)
        self._build_subtitle(content)
        self._build_platform_cards(content)
        self._build_status_row(content)

        # Espaciador inferior
        tk.Frame(center, bg=BG_DARK).pack(expand=True, fill=tk.BOTH)

        # ── Footer ──────────────────────────────
        self._build_footer()

    # ──────────────────────────────────────────
    # Barra superior
    # ──────────────────────────────────────────

    def _build_top_bar(self):
        bar = tk.Frame(self, bg=BG_PANEL, height=58)
        bar.pack(fill=tk.X)
        bar.pack_propagate(False)

        # Separador de color inferior
        tk.Frame(bar, bg=C_BLUE, height=2).place(relx=0, rely=1.0, anchor="sw", relwidth=1)

        # Nombre del sistema (izquierda)
        tk.Label(
            bar, text=f"⬡  {SYSTEM_NAME}",
            bg=BG_PANEL, fg=C_BLUE,
            font=("Segoe UI", 13, "bold"),
        ).pack(side=tk.LEFT, padx=22, pady=16)

        # Reloj (derecha)
        self.clock_label = tk.Label(
            bar, text="", bg=BG_PANEL, fg=FG_MUTED,
            font=("Consolas", 11),
        )
        self.clock_label.pack(side=tk.RIGHT, padx=22)

        # Botón configuración (derecha)
        cfg_btn = tk.Button(
            bar, text="⚙  Configuración",
            command=self.on_settings,
            bg=BG_WIDGET, fg=FG_TEXT,
            font=("Segoe UI", 10, "bold"),
            relief=tk.FLAT, cursor="hand2",
            padx=14, pady=6, bd=0,
            activebackground=C_BLUE,
            activeforeground="white",
        )
        cfg_btn.pack(side=tk.RIGHT, padx=12, pady=10)
        self._add_hover(cfg_btn, BG_WIDGET, "#2a3560")

    # ──────────────────────────────────────────
    # Logo
    # ──────────────────────────────────────────

    def _build_logo(self, parent):
        logo_frame = tk.Frame(parent, bg=BG_DARK)
        logo_frame.pack(pady=(12, 10))

        self.logo_canvas = tk.Canvas(
            logo_frame, width=170, height=170,
            bg=BG_DARK, highlightthickness=0,
        )
        self.logo_canvas.pack()

        # Hexágono exterior
        outer = self._hex_pts(85, 85, 78)
        self.logo_canvas.create_polygon(
            outer, fill=BG_PANEL, outline=C_BLUE, width=2,
        )
        # Hexágono interior
        inner = self._hex_pts(85, 85, 60)
        self.logo_canvas.create_polygon(
            inner, fill=BG_WIDGET, outline=C_BLUE, width=1,
        )
        # Texto "AI"
        self.logo_canvas.create_text(
            85, 78, text="AI",
            fill=C_BLUE, font=("Consolas", 34, "bold"),
        )
        # Texto "TRADE"
        self.logo_canvas.create_text(
            85, 111, text="TRADE",
            fill=FG_MUTED, font=("Consolas", 12, "bold"),
        )
        # Indicador pulsante (esquina superior derecha del hex)
        self._pulse_oval = self.logo_canvas.create_oval(
            143, 16, 158, 31, fill=C_GREEN, outline="",
        )
        self._pulse_idx = 0
        self._animate_pulse()

        # Título
        tk.Label(
            parent, text="Trading AI Bot",
            bg=BG_DARK, fg=FG_TEXT,
            font=("Segoe UI", 30, "bold"),
        ).pack(pady=(14, 3))

        tk.Label(
            parent,
            text=f"v{VERSION}  •  Multi-Estrategia  •  IA Adaptativa",
            bg=BG_DARK, fg=C_GREEN,
            font=("Segoe UI", 11),
        ).pack(pady=(0, 6))

    def _hex_pts(self, cx, cy, r):
        """Devuelve lista plana [x0,y0,x1,y1,...] de un hexágono."""
        pts = []
        for i in range(6):
            angle = math.pi / 3 * i - math.pi / 6
            pts.extend([cx + r * math.cos(angle), cy + r * math.sin(angle)])
        return pts

    def _animate_pulse(self):
        cols = [C_GREEN, "#04d48e", "#02aa70", "#04d48e"]
        self._pulse_idx = (self._pulse_idx + 1) % len(cols)
        self.logo_canvas.itemconfig(self._pulse_oval, fill=cols[self._pulse_idx])
        self.after(700, self._animate_pulse)

    # ──────────────────────────────────────────
    # Subtítulo
    # ──────────────────────────────────────────

    def _build_subtitle(self, parent):
        tk.Label(
            parent,
            text="Sistema Unificado de Trading Algorítmico con Inteligencia Artificial",
            bg=BG_DARK, fg=FG_MUTED,
            font=("Segoe UI", 12),
        ).pack(pady=(0, 28))

    # ──────────────────────────────────────────
    # Tarjetas de plataforma
    # ──────────────────────────────────────────

    def _build_platform_cards(self, parent):
        row = tk.Frame(parent, bg=BG_DARK)
        row.pack(pady=4)

        mt5_card = self._make_card(
            row,
            icon="📈",
            title="MetaTrader 5",
            subtitle="Trading Forex & CFDs",
            accent=C_BLUE,
            features=[
                "Múltiples estrategias con IA",
                "Aprendizaje automático adaptativo",
                "Backtesting integrado",
                "Señales en tiempo real",
            ],
            command=self.on_mt5,
            btn_label="Abrir MT5  ▶",
        )
        mt5_card.pack(side=tk.LEFT, padx=18)

        # Separador vertical
        sep = tk.Frame(row, bg=BG_PANEL, width=2)
        sep.pack(side=tk.LEFT, fill=tk.Y, padx=8, pady=10)

        bingx_card = self._make_card(
            row,
            icon="🔮",
            title="BingX Futures",
            subtitle="Trading de Futuros Cripto",
            accent=C_ORANGE,
            features=[
                "Futuros perpetuos de criptos",
                "Apalancamiento ajustable",
                "API BingX integrada",
                "Gestión de margen avanzada",
            ],
            command=self.on_bingx,
            btn_label="Abrir BingX  ▶",
        )
        bingx_card.pack(side=tk.LEFT, padx=18)

    def _make_card(self, parent, icon, title, subtitle, accent, features, command, btn_label):
        """Crea una tarjeta de plataforma con hover effect."""
        card = tk.Frame(parent, bg=BG_PANEL, width=340, height=340)
        card.pack_propagate(False)

        # Borde de color superior
        tk.Frame(card, bg=accent, height=4).pack(fill=tk.X)

        inner = tk.Frame(card, bg=BG_PANEL)
        inner.pack(fill=tk.BOTH, expand=True, padx=26, pady=18)

        lbl_icon = tk.Label(inner, text=icon, bg=BG_PANEL, font=("Segoe UI", 42))
        lbl_icon.pack(pady=(4, 6))

        lbl_title = tk.Label(inner, text=title, bg=BG_PANEL, fg=FG_TEXT,
                             font=("Segoe UI", 18, "bold"))
        lbl_title.pack()

        lbl_sub = tk.Label(inner, text=subtitle, bg=BG_PANEL, fg=FG_MUTED,
                           font=("Segoe UI", 10))
        lbl_sub.pack(pady=(2, 10))

        feat_frames = []
        for f in features:
            ff = tk.Frame(inner, bg=BG_PANEL)
            ff.pack(anchor="w", pady=1)
            dot = tk.Label(ff, text="▸", bg=BG_PANEL, fg=accent, font=("Segoe UI", 9))
            dot.pack(side=tk.LEFT)
            txt = tk.Label(ff, text=f"  {f}", bg=BG_PANEL, fg=FG_MUTED, font=("Segoe UI", 9))
            txt.pack(side=tk.LEFT)
            feat_frames.append((ff, dot, txt))

        btn = tk.Button(
            inner, text=btn_label,
            command=command,
            bg=accent, fg="white",
            font=("Segoe UI", 11, "bold"),
            relief=tk.FLAT, cursor="hand2",
            padx=16, pady=9, bd=0,
            activebackground=self._darken(accent),
            activeforeground="white",
        )
        btn.pack(pady=(14, 4), fill=tk.X)

        # Recolectar todos los widgets para el hover
        all_bg = [card, inner, lbl_icon, lbl_title, lbl_sub] + \
                 [w for ff, d, t in feat_frames for w in (ff, d, t)]

        def on_enter(_e):
            card.configure(bg=BG_WIDGET)
            for w in all_bg:
                try:
                    w.configure(bg=BG_WIDGET)
                except Exception:
                    pass

        def on_leave(_e):
            card.configure(bg=BG_PANEL)
            for w in all_bg:
                try:
                    w.configure(bg=BG_PANEL)
                except Exception:
                    pass

        card.bind("<Enter>", on_enter)
        inner.bind("<Enter>", on_enter)
        card.bind("<Leave>", on_leave)
        inner.bind("<Leave>", on_leave)

        return card

    # ──────────────────────────────────────────
    # Fila de estado
    # ──────────────────────────────────────────

    def _build_status_row(self, parent):
        row = tk.Frame(parent, bg=BG_DARK)
        row.pack(pady=(18, 0))

        # Indicador MT5
        mt5_pill = tk.Frame(row, bg=BG_PANEL, padx=12, pady=5)
        mt5_pill.pack(side=tk.LEFT, padx=8)
        self.mt5_status_canvas = tk.Canvas(
            mt5_pill, width=10, height=10, bg=BG_PANEL, highlightthickness=0,
        )
        self.mt5_status_canvas.pack(side=tk.LEFT)
        self.mt5_status_oval = self.mt5_status_canvas.create_oval(1, 1, 9, 9, fill="#555", outline="")
        self.mt5_status_lbl = tk.Label(mt5_pill, text="MT5: —", bg=BG_PANEL, fg=FG_MUTED,
                                       font=("Segoe UI", 9))
        self.mt5_status_lbl.pack(side=tk.LEFT, padx=(6, 0))

        # Indicador BingX
        bx_pill = tk.Frame(row, bg=BG_PANEL, padx=12, pady=5)
        bx_pill.pack(side=tk.LEFT, padx=8)
        self.bx_status_canvas = tk.Canvas(
            bx_pill, width=10, height=10, bg=BG_PANEL, highlightthickness=0,
        )
        self.bx_status_canvas.pack(side=tk.LEFT)
        self.bx_status_oval = self.bx_status_canvas.create_oval(1, 1, 9, 9, fill="#555", outline="")
        self.bx_status_lbl = tk.Label(bx_pill, text="BingX: sin API", bg=BG_PANEL, fg=FG_MUTED,
                                      font=("Segoe UI", 9))
        self.bx_status_lbl.pack(side=tk.LEFT, padx=(6, 0))

    # ──────────────────────────────────────────
    # Footer
    # ──────────────────────────────────────────

    def _build_footer(self):
        footer = tk.Frame(self, bg=BG_PANEL, height=52)
        footer.pack(fill=tk.X, side=tk.BOTTOM)
        footer.pack_propagate(False)

        # Línea superior del footer
        tk.Frame(footer, bg=C_BLUE, height=1).pack(fill=tk.X)

        inner = tk.Frame(footer, bg=BG_PANEL)
        inner.pack(fill=tk.BOTH, expand=True, padx=20)

        # Izquierda: nombre + versión + autor
        tk.Label(
            inner,
            text=f"⬡ {SYSTEM_NAME}  •  v{VERSION}  •  Desarrollado por {AUTHOR}",
            bg=BG_PANEL, fg=FG_MUTED, font=("Segoe UI", 9),
        ).pack(side=tk.LEFT, pady=16)

        # Centro: plataformas
        py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        tk.Label(
            inner,
            text="MetaTrader 5  •  BingX Futures  •  IA Multi-Estrategia  •  Aprendizaje Automático",
            bg=BG_PANEL, fg=FG_MUTED, font=("Segoe UI", 9),
        ).pack(side=tk.LEFT, expand=True, pady=16)

        # Derecha: Python
        tk.Label(
            inner,
            text=f"Python {py_ver}  •  Tkinter",
            bg=BG_PANEL, fg=FG_MUTED, font=("Segoe UI", 9),
        ).pack(side=tk.RIGHT, pady=16)

    # ──────────────────────────────────────────
    # Lógica de estado
    # ──────────────────────────────────────────

    def _check_statuses(self):
        """Revisar estado de MT5 y BingX periódicamente."""
        # MT5
        try:
            if os.path.exists(MT5_STATUS_FILE):
                with open(MT5_STATUS_FILE, "r") as f:
                    data = json.load(f)
                if data.get("running"):
                    mt5_color, mt5_txt = C_GREEN, "MT5: activo"
                else:
                    mt5_color, mt5_txt = C_YELLOW, "MT5: detenido"
            else:
                mt5_color, mt5_txt = "#555", "MT5: —"
        except Exception:
            mt5_color, mt5_txt = "#555", "MT5: —"

        self.mt5_status_canvas.itemconfig(self.mt5_status_oval, fill=mt5_color)
        self.mt5_status_lbl.configure(text=mt5_txt)

        # BingX
        try:
            if os.path.exists(BINGX_CFG_FILE):
                with open(BINGX_CFG_FILE, "r") as f:
                    data = json.load(f)
                has_api = bool(data.get("api_key") and data.get("api_secret"))
                demo    = data.get("demo_mode", True)
                if has_api and not demo:
                    bx_color, bx_txt = C_GREEN, "BingX: real"
                elif has_api and demo:
                    bx_color, bx_txt = C_YELLOW, "BingX: demo"
                else:
                    bx_color, bx_txt = C_ORANGE, "BingX: sin API"
            else:
                bx_color, bx_txt = "#555", "BingX: sin configurar"
        except Exception:
            bx_color, bx_txt = "#555", "BingX: —"

        self.bx_status_canvas.itemconfig(self.bx_status_oval, fill=bx_color)
        self.bx_status_lbl.configure(text=bx_txt)

        self.after(5000, self._check_statuses)

    # ──────────────────────────────────────────
    # Reloj
    # ──────────────────────────────────────────

    def _start_clock(self):
        self.clock_label.configure(text=datetime.now().strftime("%Y-%m-%d   %H:%M:%S"))
        self.after(1000, self._start_clock)

    # ──────────────────────────────────────────
    # Utilidades
    # ──────────────────────────────────────────

    @staticmethod
    def _darken(hex_color):
        """Oscurece un color hex en un 20%."""
        h = hex_color.lstrip("#")
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return "#{:02x}{:02x}{:02x}".format(
            max(0, int(r * 0.80)),
            max(0, int(g * 0.80)),
            max(0, int(b * 0.80)),
        )

    @staticmethod
    def _add_hover(widget, normal, hover):
        widget.bind("<Enter>", lambda _e: widget.configure(bg=hover))
        widget.bind("<Leave>", lambda _e: widget.configure(bg=normal))

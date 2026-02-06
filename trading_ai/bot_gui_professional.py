"""
bot_gui_professional.py - GUI Profesional Multi-Pestaña para Trading AI Bot

Pestañas:
1. Dashboard - Vista principal en tiempo real
2. Estadísticas - Análisis detallado por período
3. Historial - Tabla completa de trades
4. Configuración - Ajustes del bot
5. Sistema - Estado del sistema
"""

import threading
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from datetime import datetime, timedelta
import sys
import json
import os
from collections import defaultdict

import main

# Intentar importar matplotlib para gráficos
try:
    import matplotlib
    matplotlib.use('TkAgg')
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except:
    MATPLOTLIB_AVAILABLE = False
    print("⚠️ Matplotlib no disponible - Gráficos deshabilitados")


class TradingBotGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Trading AI - Professional Trading System")
        self.root.geometry("1600x1000")
        self.root.configure(bg="#0a0e27")
        
        # Variables de estado
        self.running_thread = None
        self.bot_state = "STOPPED"
        self.stats = {
            "total_trades": 0,
            "wins": 0,
            "losses": 0,
            "total_pips": 0.0,
            "win_rate": 0.0
        }
        
        # Configuración (se guardará en archivo)
        self.config = self.load_config()
        
        # Configurar estilos
        self.setup_styles()
        
        # Crear notebook (sistema de pestañas)
        self.create_notebook()
        
        # Crear las pestañas
        self.create_dashboard_tab()
        self.create_statistics_tab()
        self.create_history_tab()
        self.create_config_tab()
        self.create_system_tab()
        
        # Inicializar
        self.load_stats()
        self.update_all_displays()
        
        # Auto-actualización
        self.auto_update()
        
        # Redirigir prints
        sys.stdout = self
        sys.stderr = self
    
    def setup_styles(self):
        """Configurar estilos ttk con tema oscuro profesional"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Colores del tema
        bg_dark = "#0a0e27"
        bg_panel = "#151b3d"
        bg_widget = "#1e2749"
        fg_text = "#e0e6ff"
        accent_blue = "#4895ef"
        accent_green = "#06ffa5"
        accent_red = "#ff006e"
        accent_yellow = "#ffbe0b"
        
        # Notebook (pestañas)
        style.configure("TNotebook", background=bg_dark, borderwidth=0)
        style.configure("TNotebook.Tab", 
                       background=bg_panel,
                       foreground=fg_text,
                       padding=[20, 10],
                       font=("Segoe UI", 11, "bold"))
        style.map("TNotebook.Tab",
                 background=[("selected", bg_widget)],
                 foreground=[("selected", accent_blue)])
        
        # Frames
        style.configure("Dark.TFrame", background=bg_dark)
        style.configure("Panel.TFrame", background=bg_panel)
        style.configure("Widget.TFrame", background=bg_widget)
        
        # Labels
        style.configure("Title.TLabel",
                       background=bg_panel,
                       foreground=accent_blue,
                       font=("Segoe UI", 14, "bold"))
        
        style.configure("Subtitle.TLabel",
                       background=bg_panel,
                       foreground=fg_text,
                       font=("Segoe UI", 11))
        
        style.configure("Stat.TLabel",
                       background=bg_widget,
                       foreground=fg_text,
                       font=("Segoe UI", 10))
        
        style.configure("Value.TLabel",
                       background=bg_widget,
                       foreground=accent_blue,
                       font=("Segoe UI", 16, "bold"))
        
        # Botones
        style.configure("Accent.TButton",
                       font=("Segoe UI", 11, "bold"),
                       borderwidth=0,
                       relief="flat")
    
    def create_notebook(self):
        """Crear sistema de pestañas"""
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    # ==================== PESTAÑA 1: DASHBOARD ====================
    
    def create_dashboard_tab(self):
        """Dashboard principal - Vista en tiempo real"""
        tab = ttk.Frame(self.notebook, style="Dark.TFrame")
        self.notebook.add(tab, text="  📊 Dashboard  ")
        
        # Header con controles
        header = tk.Frame(tab, bg="#151b3d", height=120)
        header.pack(fill=tk.X, padx=10, pady=10)
        header.pack_propagate(False)
        
        # Estado del bot
        status_frame = tk.Frame(header, bg="#151b3d")
        status_frame.pack(side=tk.LEFT, padx=20, pady=15)
        
        tk.Label(status_frame, text="Estado del Bot", bg="#151b3d", fg="#e0e6ff",
                font=("Segoe UI", 10)).pack()
        
        self.status_indicator = tk.Canvas(status_frame, width=60, height=60,
                                         bg="#151b3d", highlightthickness=0)
        self.status_indicator.pack(pady=5)
        self.status_circle = self.status_indicator.create_oval(10, 10, 50, 50,
                                                               fill="#666", outline="")
        
        self.status_label = tk.Label(status_frame, text="DETENIDO", bg="#151b3d",
                                     fg="#ff006e", font=("Segoe UI", 11, "bold"))
        self.status_label.pack()
        
        # Botones de control
        btn_frame = tk.Frame(header, bg="#151b3d")
        btn_frame.pack(side=tk.LEFT, padx=30, pady=15)
        
        self.start_btn = tk.Button(btn_frame, text="▶ INICIAR", command=self.start_bot,
                                   bg="#06ffa5", fg="#0a0e27", font=("Segoe UI", 12, "bold"),
                                   width=12, height=2, relief=tk.FLAT, cursor="hand2",
                                   activebackground="#05dd8f")
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = tk.Button(btn_frame, text="■ DETENER", command=self.stop_bot,
                                  bg="#ff006e", fg="white", font=("Segoe UI", 12, "bold"),
                                  width=12, height=2, relief=tk.FLAT, cursor="hand2",
                                  state=tk.DISABLED, activebackground="#dd0060")
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        self.restart_btn = tk.Button(btn_frame, text="↻ REINICIAR", command=self.restart_bot,
                                     bg="#ffbe0b", fg="#0a0e27", font=("Segoe UI", 12, "bold"),
                                     width=12, height=2, relief=tk.FLAT, cursor="hand2",
                                     activebackground="#e0a800")
        self.restart_btn.pack(side=tk.LEFT, padx=5)
        
        # Título principal
        title_frame = tk.Frame(header, bg="#151b3d")
        title_frame.pack(side=tk.RIGHT, padx=20)
        
        tk.Label(title_frame, text="TRADING AI", bg="#151b3d", fg="#4895ef",
                font=("Segoe UI", 24, "bold")).pack()
        tk.Label(title_frame, text="Advanced Intelligence System", bg="#151b3d",
                fg="#8b9dc3", font=("Segoe UI", 11)).pack()
        
        # Contenido principal
        content = tk.Frame(tab, bg="#0a0e27")
        content.pack(fill=tk.BOTH, expand=True, padx=10)
        
        # Panel izquierdo (Stats + Info)
        left_panel = tk.Frame(content, bg="#0a0e27", width=450)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 5))
        left_panel.pack_propagate(False)
        
        # Panel derecho (Logs)
        right_panel = tk.Frame(content, bg="#0a0e27")
        right_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Crear paneles
        self.create_quick_stats_panel(left_panel)
        self.create_market_status_panel(left_panel)
        self.create_last_signal_panel(left_panel)
        self.create_logs_panel(right_panel)
    
    def create_quick_stats_panel(self, parent):
        """Panel de estadísticas rápidas"""
        frame = tk.LabelFrame(parent, text="  📈 ESTADÍSTICAS RÁPIDAS  ", bg="#151b3d",
                             fg="#4895ef", font=("Segoe UI", 12, "bold"),
                             relief=tk.FLAT, borderwidth=2)
        frame.pack(fill=tk.X, pady=5)
        
        # Grid de stats
        stats_container = tk.Frame(frame, bg="#151b3d")
        stats_container.pack(fill=tk.X, padx=15, pady=15)
        
        # Stats individuales
        stats = [
            ("Total Trades", "total_trades_dash", "#4895ef"),
            ("Ganadas", "wins_dash", "#06ffa5"),
            ("Perdidas", "losses_dash", "#ff006e"),
            ("Win Rate", "winrate_dash", "#ffbe0b")
        ]
        
        for i, (label, var, color) in enumerate(stats):
            stat_frame = tk.Frame(stats_container, bg="#1e2749", relief=tk.FLAT, borderwidth=1)
            stat_frame.grid(row=i//2, column=i%2, padx=5, pady=5, sticky="nsew")
            
            tk.Label(stat_frame, text=label, bg="#1e2749", fg="#8b9dc3",
                    font=("Segoe UI", 9)).pack(pady=(10, 0))
            
            label_widget = tk.Label(stat_frame, text="0", bg="#1e2749", fg=color,
                                   font=("Segoe UI", 20, "bold"))
            label_widget.pack(pady=(0, 10))
            
            setattr(self, var, label_widget)
        
        # Configurar grid
        stats_container.columnconfigure(0, weight=1)
        stats_container.columnconfigure(1, weight=1)
    
    def create_market_status_panel(self, parent):
        """Panel de estado del mercado"""
        frame = tk.LabelFrame(parent, text="  🌐 MERCADO ACTUAL  ", bg="#151b3d",
                             fg="#4895ef", font=("Segoe UI", 12, "bold"),
                             relief=tk.FLAT, borderwidth=2)
        frame.pack(fill=tk.X, pady=5)
        
        info_container = tk.Frame(frame, bg="#151b3d")
        info_container.pack(fill=tk.X, padx=15, pady=10)
        
        # Info del mercado
        market_info = [
            ("Símbolo:", "symbol_dash"),
            ("Tendencia:", "trend_dash"),
            ("Volatilidad:", "volatility_dash"),
            ("RSI:", "rsi_dash"),
            ("Régimen:", "regime_dash")
        ]
        
        for i, (label, var) in enumerate(market_info):
            row = tk.Frame(info_container, bg="#151b3d")
            row.pack(fill=tk.X, pady=3)
            
            tk.Label(row, text=label, bg="#151b3d", fg="#8b9dc3",
                    font=("Segoe UI", 10), width=12, anchor="w").pack(side=tk.LEFT)
            
            value_label = tk.Label(row, text="--", bg="#151b3d", fg="#e0e6ff",
                                  font=("Segoe UI", 10, "bold"), anchor="w")
            value_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
            
            setattr(self, var, value_label)
    
    def create_last_signal_panel(self, parent):
        """Panel de última señal"""
        frame = tk.LabelFrame(parent, text="  🎯 ÚLTIMA SEÑAL  ", bg="#151b3d",
                             fg="#4895ef", font=("Segoe UI", 12, "bold"),
                             relief=tk.FLAT, borderwidth=2)
        frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.signal_text_dash = scrolledtext.ScrolledText(
            frame, height=8, bg="#1e2749", fg="#e0e6ff",
            font=("Consolas", 9), relief=tk.FLAT, wrap=tk.WORD,
            insertbackground="#4895ef"
        )
        self.signal_text_dash.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    def create_logs_panel(self, parent):
        """Panel de logs con colores"""
        frame = tk.LabelFrame(parent, text="  📋 LOGS DEL SISTEMA  ", bg="#151b3d",
                             fg="#4895ef", font=("Segoe UI", 12, "bold"),
                             relief=tk.FLAT, borderwidth=2)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Toolbar
        toolbar = tk.Frame(frame, bg="#151b3d")
        toolbar.pack(fill=tk.X, padx=5, pady=5)
        
        tk.Button(toolbar, text="✗ Limpiar", command=self.clear_logs,
                 bg="#ff006e", fg="white", relief=tk.FLAT, cursor="hand2",
                 font=("Segoe UI", 9, "bold")).pack(side=tk.RIGHT, padx=2)
        
        # Logs
        self.log_box = scrolledtext.ScrolledText(
            frame, height=25, bg="#1e2749", fg="#06ffa5",
            font=("Consolas", 9), relief=tk.FLAT, wrap=tk.WORD,
            insertbackground="#4895ef"
        )
        self.log_box.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Tags de colores
        self.log_box.tag_config("ERROR", foreground="#ff006e")
        self.log_box.tag_config("WARNING", foreground="#ffbe0b")
        self.log_box.tag_config("SUCCESS", foreground="#06ffa5")
        self.log_box.tag_config("INFO", foreground="#4895ef")
        self.log_box.tag_config("TIMESTAMP", foreground="#6c7a96")
    
    # ==================== PESTAÑA 2: ESTADÍSTICAS ====================
    
    def create_statistics_tab(self):
        """Pestaña de estadísticas avanzadas"""
        tab = ttk.Frame(self.notebook, style="Dark.TFrame")
        self.notebook.add(tab, text="  📊 Estadísticas  ")
        
        # Header
        header = tk.Frame(tab, bg="#151b3d")
        header.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(header, text="ANÁLISIS DE PERFORMANCE", bg="#151b3d", fg="#4895ef",
                font=("Segoe UI", 18, "bold")).pack(side=tk.LEFT, padx=20)
        
        # Selector de período
        period_frame = tk.Frame(header, bg="#151b3d")
        period_frame.pack(side=tk.RIGHT, padx=20)
        
        tk.Label(period_frame, text="Período:", bg="#151b3d", fg="#e0e6ff",
                font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=5)
        
        self.period_var = tk.StringVar(value="Hoy")
        period_combo = ttk.Combobox(period_frame, textvariable=self.period_var,
                                    values=["Hoy", "Esta Semana", "Este Mes", "Total"],
                                    state="readonly", width=15)
        period_combo.pack(side=tk.LEFT, padx=5)
        period_combo.bind("<<ComboboxSelected>>", lambda e: self.update_statistics_tab())
        
        tk.Button(period_frame, text="↻ Actualizar", command=self.update_statistics_tab,
                 bg="#4895ef", fg="white", relief=tk.FLAT, cursor="hand2",
                 font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=5)
        
        # Contenido
        content = tk.Frame(tab, bg="#0a0e27")
        content.pack(fill=tk.BOTH, expand=True, padx=10)
        
        # Panel izquierdo - Stats numéricas
        left = tk.Frame(content, bg="#0a0e27", width=400)
        left.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 5))
        
        # Stats detalladas
        self.create_detailed_stats_panel(left)
        self.create_setup_performance_panel(left)
        
        # Panel derecho - Gráficos
        right = tk.Frame(content, bg="#0a0e27")
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        if MATPLOTLIB_AVAILABLE:
            self.create_charts_panel(right)
        else:
            tk.Label(right, text="Matplotlib no disponible\nInstalar: pip install matplotlib",
                    bg="#0a0e27", fg="#ff006e", font=("Segoe UI", 12)).pack(pady=50)
    
    def create_detailed_stats_panel(self, parent):
        """Panel de estadísticas detalladas"""
        frame = tk.LabelFrame(parent, text="  MÉTRICAS DETALLADAS  ", bg="#151b3d",
                             fg="#4895ef", font=("Segoe UI", 11, "bold"),
                             relief=tk.FLAT, borderwidth=2)
        frame.pack(fill=tk.X, pady=5)
        
        container = tk.Frame(frame, bg="#151b3d")
        container.pack(fill=tk.X, padx=10, pady=10)
        
        metrics = [
            ("Total Trades:", "stat_total"),
            ("Ganadas:", "stat_wins"),
            ("Perdidas:", "stat_losses"),
            ("Win Rate:", "stat_winrate"),
            ("Total Pips:", "stat_pips"),
            ("Avg Win:", "stat_avgwin"),
            ("Avg Loss:", "stat_avgloss"),
            ("Profit Factor:", "stat_pf"),
            ("Best Trade:", "stat_best"),
            ("Worst Trade:", "stat_worst"),
            ("Racha Actual:", "stat_streak")
        ]
        
        for label, var in metrics:
            row = tk.Frame(container, bg="#151b3d")
            row.pack(fill=tk.X, pady=2)
            
            tk.Label(row, text=label, bg="#151b3d", fg="#8b9dc3",
                    font=("Segoe UI", 9), width=15, anchor="w").pack(side=tk.LEFT)
            
            value_label = tk.Label(row, text="--", bg="#151b3d", fg="#e0e6ff",
                                  font=("Segoe UI", 10, "bold"), anchor="e")
            value_label.pack(side=tk.RIGHT)
            
            setattr(self, var, value_label)
    
    def create_setup_performance_panel(self, parent):
        """Panel de performance por setup"""
        frame = tk.LabelFrame(parent, text="  PERFORMANCE POR ESTRATEGIA  ", bg="#151b3d",
                             fg="#4895ef", font=("Segoe UI", 11, "bold"),
                             relief=tk.FLAT, borderwidth=2)
        frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Contenedor con scroll
        canvas = tk.Canvas(frame, bg="#151b3d", highlightthickness=0)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        self.setup_perf_container = tk.Frame(canvas, bg="#151b3d")
        
        self.setup_perf_container.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.setup_perf_container, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def create_charts_panel(self, parent):
        """Panel de gráficos"""
        frame = tk.LabelFrame(parent, text="  GRÁFICOS DE ANÁLISIS  ", bg="#151b3d",
                             fg="#4895ef", font=("Segoe UI", 11, "bold"),
                             relief=tk.FLAT, borderwidth=2)
        frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Crear figura de matplotlib
        self.fig = Figure(figsize=(8, 6), facecolor='#151b3d')
        self.canvas_chart = FigureCanvasTkAgg(self.fig, master=frame)
        self.canvas_chart.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Placeholder
        ax = self.fig.add_subplot(111, facecolor='#1e2749')
        ax.text(0.5, 0.5, 'Gráficos se cargarán con datos', 
               ha='center', va='center', color='#8b9dc3', fontsize=12)
        ax.set_xticks([])
        ax.set_yticks([])
        self.canvas_chart.draw()
    
    # ==================== PESTAÑA 3: HISTORIAL ====================
    
    def create_history_tab(self):
        """Pestaña de historial de trades"""
        tab = ttk.Frame(self.notebook, style="Dark.TFrame")
        self.notebook.add(tab, text="  📜 Historial  ")
        
        # Header
        header = tk.Frame(tab, bg="#151b3d")
        header.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(header, text="HISTORIAL DE TRADES", bg="#151b3d", fg="#4895ef",
                font=("Segoe UI", 18, "bold")).pack(side=tk.LEFT, padx=20)
        
        # Botones
        btn_frame = tk.Frame(header, bg="#151b3d")
        btn_frame.pack(side=tk.RIGHT, padx=20)
        
        tk.Button(btn_frame, text="↻ Actualizar", command=self.load_history,
                 bg="#4895ef", fg="white", relief=tk.FLAT, cursor="hand2",
                 font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=2)
        
        tk.Button(btn_frame, text="📥 Exportar CSV", command=self.export_history,
                 bg="#06ffa5", fg="#0a0e27", relief=tk.FLAT, cursor="hand2",
                 font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=2)
        
        # Filtros
        filter_frame = tk.Frame(tab, bg="#151b3d")
        filter_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(filter_frame, text="Filtrar:", bg="#151b3d", fg="#e0e6ff",
                font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=5)
        
        self.filter_var = tk.StringVar(value="Todos")
        filter_combo = ttk.Combobox(filter_frame, textvariable=self.filter_var,
                                    values=["Todos", "Solo Ganancias", "Solo Pérdidas"],
                                    state="readonly", width=15)
        filter_combo.pack(side=tk.LEFT, padx=5)
        filter_combo.bind("<<ComboboxSelected>>", lambda e: self.load_history())
        
        # Tabla de historial
        table_frame = tk.Frame(tab, bg="#0a0e27")
        table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Crear Treeview
        columns = ("Fecha", "Signal ID", "Setup", "Acción", "Resultado", "Pips")
        self.history_tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=20)
        
        # Configurar columnas
        for col in columns:
            self.history_tree.heading(col, text=col)
            self.history_tree.column(col, width=150, anchor="center")
        
        # Scrollbars
        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.history_tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=self.history_tree.xview)
        self.history_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        self.history_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)
        
        # Tags para colores
        self.history_tree.tag_configure("WIN", background="#1a3d2e", foreground="#06ffa5")
        self.history_tree.tag_configure("LOSS", background="#3d1a2e", foreground="#ff006e")
    
    # ==================== PESTAÑA 4: CONFIGURACIÓN ====================
    
    def create_config_tab(self):
        """Pestaña de configuración"""
        tab = ttk.Frame(self.notebook, style="Dark.TFrame")
        self.notebook.add(tab, text="  ⚙️ Configuración  ")
        
        # Header
        header = tk.Frame(tab, bg="#151b3d")
        header.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(header, text="CONFIGURACIÓN DEL BOT", bg="#151b3d", fg="#4895ef",
                font=("Segoe UI", 18, "bold")).pack(side=tk.LEFT, padx=20)
        
        tk.Button(header, text="💾 Guardar Cambios", command=self.save_config_changes,
                 bg="#06ffa5", fg="#0a0e27", relief=tk.FLAT, cursor="hand2",
                 font=("Segoe UI", 11, "bold")).pack(side=tk.RIGHT, padx=20)
        
        # Contenedor con scroll
        canvas = tk.Canvas(tab, bg="#0a0e27", highlightthickness=0)
        scrollbar = ttk.Scrollbar(tab, orient="vertical", command=canvas.yview)
        content = tk.Frame(canvas, bg="#0a0e27")
        
        content.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=content, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Secciones de configuración
        self.create_trading_config_section(content)
        self.create_risk_config_section(content)
        self.create_schedule_config_section(content)
    
    def create_trading_config_section(self, parent):
        """Sección de configuración de trading"""
        frame = tk.LabelFrame(parent, text="  CONFIGURACIÓN DE TRADING  ", bg="#151b3d",
                             fg="#4895ef", font=("Segoe UI", 12, "bold"),
                             relief=tk.FLAT, borderwidth=2)
        frame.pack(fill=tk.X, padx=10, pady=10)
        
        container = tk.Frame(frame, bg="#151b3d")
        container.pack(fill=tk.X, padx=20, pady=20)
        
        # Configuraciones
        configs = [
            ("Confianza Mínima (%):", "min_confidence", 0, 100, self.config.get("min_confidence", 75)),
            ("Cooldown entre trades (seg):", "cooldown", 0, 300, self.config.get("cooldown", 60)),
            ("Max trades diarios:", "max_daily_trades", 1, 100, self.config.get("max_daily_trades", 20)),
            ("Max pérdidas consecutivas:", "max_losses", 1, 10, self.config.get("max_losses", 3)),
        ]
        
        self.config_vars = {}
        
        for label, key, min_val, max_val, default in configs:
            row = tk.Frame(container, bg="#151b3d")
            row.pack(fill=tk.X, pady=10)
            
            tk.Label(row, text=label, bg="#151b3d", fg="#e0e6ff",
                    font=("Segoe UI", 10), width=30, anchor="w").pack(side=tk.LEFT)
            
            var = tk.IntVar(value=default)
            self.config_vars[key] = var
            
            scale = tk.Scale(row, from_=min_val, to=max_val, orient=tk.HORIZONTAL,
                           variable=var, bg="#1e2749", fg="#e0e6ff", highlightthickness=0,
                           troughcolor="#0a0e27", activebackground="#4895ef", length=200)
            scale.pack(side=tk.LEFT, padx=10)
            
            value_label = tk.Label(row, textvariable=var, bg="#151b3d", fg="#4895ef",
                                  font=("Segoe UI", 11, "bold"), width=5)
            value_label.pack(side=tk.LEFT)
    
    def create_risk_config_section(self, parent):
        """Sección de gestión de riesgo"""
        frame = tk.LabelFrame(parent, text="  GESTIÓN DE RIESGO  ", bg="#151b3d",
                             fg="#4895ef", font=("Segoe UI", 12, "bold"),
                             relief=tk.FLAT, borderwidth=2)
        frame.pack(fill=tk.X, padx=10, pady=10)
        
        container = tk.Frame(frame, bg="#151b3d")
        container.pack(fill=tk.X, padx=20, pady=20)
        
        # Tamaño de lote
        row = tk.Frame(container, bg="#151b3d")
        row.pack(fill=tk.X, pady=10)
        
        tk.Label(row, text="Tamaño de Lote:", bg="#151b3d", fg="#e0e6ff",
                font=("Segoe UI", 10), width=30, anchor="w").pack(side=tk.LEFT)
        
        self.lot_size_var = tk.DoubleVar(value=self.config.get("lot_size", 0.01))
        self.config_vars["lot_size"] = self.lot_size_var
        
        lot_entry = tk.Entry(row, textvariable=self.lot_size_var, bg="#1e2749", fg="#e0e6ff",
                            font=("Segoe UI", 11), relief=tk.FLAT, width=10)
        lot_entry.pack(side=tk.LEFT, padx=10)
        
        tk.Label(row, text="lots", bg="#151b3d", fg="#8b9dc3",
                font=("Segoe UI", 10)).pack(side=tk.LEFT)
    
    def create_schedule_config_section(self, parent):
        """Sección de horarios"""
        frame = tk.LabelFrame(parent, text="  HORARIOS DE OPERACIÓN  ", bg="#151b3d",
                             fg="#4895ef", font=("Segoe UI", 12, "bold"),
                             relief=tk.FLAT, borderwidth=2)
        frame.pack(fill=tk.X, padx=10, pady=10)
        
        container = tk.Frame(frame, bg="#151b3d")
        container.pack(fill=tk.X, padx=20, pady=20)
        
        # Horarios
        row = tk.Frame(container, bg="#151b3d")
        row.pack(fill=tk.X, pady=10)
        
        tk.Label(row, text="Operar solo entre:", bg="#151b3d", fg="#e0e6ff",
                font=("Segoe UI", 10)).pack(side=tk.LEFT)
        
        self.start_hour_var = tk.StringVar(value=self.config.get("start_hour", "08:00"))
        self.end_hour_var = tk.StringVar(value=self.config.get("end_hour", "20:00"))
        
        self.config_vars["start_hour"] = self.start_hour_var
        self.config_vars["end_hour"] = self.end_hour_var
        
        tk.Entry(row, textvariable=self.start_hour_var, bg="#1e2749", fg="#e0e6ff",
                font=("Segoe UI", 10), relief=tk.FLAT, width=8).pack(side=tk.LEFT, padx=10)
        
        tk.Label(row, text="y", bg="#151b3d", fg="#e0e6ff",
                font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=5)
        
        tk.Entry(row, textvariable=self.end_hour_var, bg="#1e2749", fg="#e0e6ff",
                font=("Segoe UI", 10), relief=tk.FLAT, width=8).pack(side=tk.LEFT, padx=5)
    
    # ==================== PESTAÑA 5: SISTEMA ====================
    
    def create_system_tab(self):
        """Pestaña de información del sistema"""
        tab = ttk.Frame(self.notebook, style="Dark.TFrame")
        self.notebook.add(tab, text="  🔧 Sistema  ")
        
        # Header
        header = tk.Frame(tab, bg="#151b3d")
        header.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(header, text="ESTADO DEL SISTEMA", bg="#151b3d", fg="#4895ef",
                font=("Segoe UI", 18, "bold")).pack(side=tk.LEFT, padx=20)
        
        # Contenido
        content = tk.Frame(tab, bg="#0a0e27")
        content.pack(fill=tk.BOTH, expand=True, padx=10)
        
        # Info del sistema
        self.create_system_info_panel(content)
        self.create_file_status_panel(content)
    
    def create_system_info_panel(self, parent):
        """Panel de información del sistema"""
        frame = tk.LabelFrame(parent, text="  INFORMACIÓN GENERAL  ", bg="#151b3d",
                             fg="#4895ef", font=("Segoe UI", 12, "bold"),
                             relief=tk.FLAT, borderwidth=2)
        frame.pack(fill=tk.X, pady=10)
        
        container = tk.Frame(frame, bg="#151b3d")
        container.pack(fill=tk.X, padx=20, pady=20)
        
        info = [
            ("Versión del Bot:", "v2.0.0"),
            ("Python:", f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"),
            ("Sistema Operativo:", os.name),
            ("Directorio de Trabajo:", os.getcwd())
        ]
        
        for label, value in info:
            row = tk.Frame(container, bg="#151b3d")
            row.pack(fill=tk.X, pady=5)
            
            tk.Label(row, text=label, bg="#151b3d", fg="#8b9dc3",
                    font=("Segoe UI", 10), width=20, anchor="w").pack(side=tk.LEFT)
            
            tk.Label(row, text=value, bg="#151b3d", fg="#e0e6ff",
                    font=("Segoe UI", 10, "bold"), anchor="w").pack(side=tk.LEFT)
    
    def create_file_status_panel(self, parent):
        """Panel de estado de archivos"""
        frame = tk.LabelFrame(parent, text="  ESTADO DE ARCHIVOS  ", bg="#151b3d",
                             fg="#4895ef", font=("Segoe UI", 12, "bold"),
                             relief=tk.FLAT, borderwidth=2)
        frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        self.file_status_text = scrolledtext.ScrolledText(
            frame, height=20, bg="#1e2749", fg="#e0e6ff",
            font=("Consolas", 9), relief=tk.FLAT, wrap=tk.WORD
        )
        self.file_status_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.check_file_status()
    
    # ==================== MÉTODOS DE CONTROL ====================
    
    def start_bot(self):
        """Iniciar el bot"""
        if self.running_thread and self.running_thread.is_alive():
            self.write("⚠ El bot ya está en ejecución\n", "WARNING")
            return
        
        self.bot_state = "RUNNING"
        self.update_status_indicator()
        self.write("► Iniciando bot...\n", "SUCCESS")
        
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        
        self.running_thread = threading.Thread(target=main.start_bot, daemon=True)
        self.running_thread.start()
    
    def stop_bot(self):
        """Detener el bot"""
        self.write("■ Deteniendo bot...\n", "WARNING")
        main.stop_bot()
        
        self.bot_state = "STOPPED"
        self.update_status_indicator()
        
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
    
    def restart_bot(self):
        """Reiniciar el bot"""
        if self.bot_state == "RUNNING":
            self.stop_bot()
            self.root.after(2000, self.start_bot)
        else:
            self.start_bot()
    
    def clear_logs(self):
        """Limpiar logs"""
        self.log_box.delete(1.0, tk.END)
        self.write("✓ Logs limpiados\n", "INFO")
    
    # ==================== MÉTODOS DE ACTUALIZACIÓN ====================
    
    def write(self, message, tag="INFO"):
        """Escribir en logs con timestamp y color"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_box.insert(tk.END, f"[{timestamp}] ", "TIMESTAMP")
        self.log_box.insert(tk.END, message, tag)
        self.log_box.see(tk.END)
    
    def flush(self):
        """Requerido para redirigir stdout"""
        pass
    
    def update_status_indicator(self):
        """Actualizar indicador visual de estado"""
        colors = {
            "STOPPED": "#666666",
            "RUNNING": "#06ffa5",
            "ERROR": "#ff006e"
        }
        
        labels = {
            "STOPPED": "DETENIDO",
            "RUNNING": "EN EJECUCIÓN",
            "ERROR": "ERROR"
        }
        
        label_colors = {
            "STOPPED": "#ff006e",
            "RUNNING": "#06ffa5",
            "ERROR": "#ff006e"
        }
        
        color = colors.get(self.bot_state, "#666666")
        label = labels.get(self.bot_state, "DETENIDO")
        label_color = label_colors.get(self.bot_state, "#ff006e")
        
        self.status_indicator.itemconfig(self.status_circle, fill=color)
        self.status_label.config(text=label, fg=label_color)
        
        if self.bot_state == "RUNNING":
            self.pulse_indicator()
    
    def pulse_indicator(self):
        """Efecto de pulso en el indicador"""
        if self.bot_state == "RUNNING":
            current_color = self.status_indicator.itemcget(self.status_circle, "fill")
            new_color = "#05dd8f" if current_color == "#06ffa5" else "#06ffa5"
            self.status_indicator.itemconfig(self.status_circle, fill=new_color)
            self.root.after(800, self.pulse_indicator)
    
    def load_stats(self):
        """Cargar estadísticas desde learning_data"""
        stats_file = "learning_data/setup_stats.json"
        
        if os.path.exists(stats_file):
            try:
                with open(stats_file, "r") as f:
                    data = json.load(f)
                
                total_wins = sum(s.get("wins", 0) for s in data.values())
                total_losses = sum(s.get("losses", 0) for s in data.values())
                total_pips = sum(s.get("total_pips", 0) for s in data.values())
                
                self.stats["wins"] = total_wins
                self.stats["losses"] = total_losses
                self.stats["total_trades"] = total_wins + total_losses
                self.stats["total_pips"] = total_pips
                
                if self.stats["total_trades"] > 0:
                    self.stats["win_rate"] = (total_wins / self.stats["total_trades"]) * 100
                
            except Exception as e:
                print(f"⚠ Error cargando stats: {e}")
    
    def update_dashboard_stats(self):
        """Actualizar estadísticas del dashboard"""
        self.total_trades_dash.config(text=str(self.stats["total_trades"]))
        self.wins_dash.config(text=str(self.stats["wins"]))
        self.losses_dash.config(text=str(self.stats["losses"]))
        self.winrate_dash.config(text=f"{self.stats['win_rate']:.1f}%")
    
    def update_market_info(self):
        """Actualizar información del mercado"""
        market_file = "/home/travieso/.wine/drive_c/Program Files/MetaTrader 5/MQL5/Files/market_data.json"
        
        if os.path.exists(market_file):
            try:
                with open(market_file, "r") as f:
                    data = json.load(f)
                
                self.symbol_dash.config(text=data.get("symbol", "--"))
                
                analysis = data.get("analysis", {})
                self.trend_dash.config(text=analysis.get("trend", "--"))
                self.volatility_dash.config(text=analysis.get("volatility", "--"))
                
                # Colorear según tendencia
                trend = analysis.get("trend", "")
                if "UP" in trend:
                    self.trend_dash.config(fg="#06ffa5")
                elif "DOWN" in trend:
                    self.trend_dash.config(fg="#ff006e")
                else:
                    self.trend_dash.config(fg="#ffbe0b")
                
                self.regime_dash.config(text=analysis.get("market_regime", "--") 
                                       if "market_regime" in analysis else "--")
                
                indicators = data.get("indicators", {})
                rsi = indicators.get("rsi", "--")
                if isinstance(rsi, (int, float)):
                    self.rsi_dash.config(text=f"{rsi:.1f}")
                    # Colorear RSI
                    if rsi > 70:
                        self.rsi_dash.config(fg="#ff006e")
                    elif rsi < 30:
                        self.rsi_dash.config(fg="#06ffa5")
                    else:
                        self.rsi_dash.config(fg="#e0e6ff")
                else:
                    self.rsi_dash.config(text="--")
                
            except:
                pass
    
    def update_last_signal(self):
        """Actualizar última señal generada"""
        signal_file = "/home/travieso/.wine/drive_c/Program Files/MetaTrader 5/MQL5/Files/signals/signal.json"
        
        if os.path.exists(signal_file):
            try:
                with open(signal_file, "r") as f:
                    signal = json.load(f)
                
                self.signal_text_dash.delete(1.0, tk.END)
                
                action = signal.get('action', 'N/A')
                confidence = signal.get('confidence', 0)
                
                text = f"""
╔══════════════════════════════╗
  Action: {action}
  Confidence: {confidence * 100:.1f}%
  SL: {signal.get('sl_pips', 0)} pips
  TP: {signal.get('tp_pips', 0)} pips
  Setup: {signal.get('setup_name', 'N/A')}
  Time: {signal.get('timestamp', 'N/A')}
╚══════════════════════════════╝

Reason: {signal.get('reason', 'N/A')}
                """
                
                self.signal_text_dash.insert(1.0, text.strip())
                
            except:
                pass
    
    def update_statistics_tab(self):
        """Actualizar pestaña de estadísticas"""
        # Cargar historial
        history = self.load_trade_history()
        
        # Filtrar por período
        period = self.period_var.get()
        filtered = self.filter_history_by_period(history, period)
        
        # Calcular métricas
        if filtered:
            wins = [t for t in filtered if t.get("result") == "WIN"]
            losses = [t for t in filtered if t.get("result") == "LOSS"]
            
            total = len(filtered)
            total_wins = len(wins)
            total_losses = len(losses)
            win_rate = (total_wins / total * 100) if total > 0 else 0
            
            total_pips = sum(t.get("pips", 0) for t in filtered)
            avg_win = sum(t.get("pips", 0) for t in wins) / len(wins) if wins else 0
            avg_loss = sum(abs(t.get("pips", 0)) for t in losses) / len(losses) if losses else 0
            
            pf = (avg_win * total_wins) / (avg_loss * total_losses) if avg_loss > 0 and total_losses > 0 else 0
            
            best = max((t.get("pips", 0) for t in filtered), default=0)
            worst = min((t.get("pips", 0) for t in filtered), default=0)
            
            # Calcular racha
            streak = 0
            for t in reversed(filtered):
                if t.get("result") == "WIN":
                    streak += 1
                else:
                    break
            
            # Actualizar labels
            self.stat_total.config(text=str(total))
            self.stat_wins.config(text=str(total_wins), fg="#06ffa5")
            self.stat_losses.config(text=str(total_losses), fg="#ff006e")
            self.stat_winrate.config(text=f"{win_rate:.1f}%",
                                    fg="#06ffa5" if win_rate >= 50 else "#ff006e")
            self.stat_pips.config(text=f"{total_pips:.2f}",
                                 fg="#06ffa5" if total_pips >= 0 else "#ff006e")
            self.stat_avgwin.config(text=f"+{avg_win:.2f}", fg="#06ffa5")
            self.stat_avgloss.config(text=f"-{avg_loss:.2f}", fg="#ff006e")
            self.stat_pf.config(text=f"{pf:.2f}",
                               fg="#06ffa5" if pf >= 1 else "#ff006e")
            self.stat_best.config(text=f"+{best:.2f}", fg="#06ffa5")
            self.stat_worst.config(text=f"{worst:.2f}", fg="#ff006e")
            self.stat_streak.config(text=f"{streak}W" if streak > 0 else "0",
                                   fg="#06ffa5" if streak > 0 else "#e0e6ff")
        
        # Actualizar setup performance
        self.update_setup_performance()
        
        # Actualizar gráficos
        if MATPLOTLIB_AVAILABLE and filtered:
            self.update_charts(filtered)
    
    def update_setup_performance(self):
        """Actualizar panel de performance por setup"""
        # Limpiar contenedor
        for widget in self.setup_perf_container.winfo_children():
            widget.destroy()
        
        # Cargar stats
        stats_file = "learning_data/setup_stats.json"
        if not os.path.exists(stats_file):
            return
        
        try:
            with open(stats_file, "r") as f:
                stats = json.load(f)
            
            for setup_name, data in stats.items():
                wins = data.get("wins", 0)
                losses = data.get("losses", 0)
                total = wins + losses
                wr = (wins / total * 100) if total > 0 else 0
                pips = data.get("total_pips", 0)
                
                # Frame para cada setup
                setup_frame = tk.Frame(self.setup_perf_container, bg="#1e2749", relief=tk.SOLID, borderwidth=1)
                setup_frame.pack(fill=tk.X, padx=5, pady=5)
                
                # Nombre del setup
                tk.Label(setup_frame, text=setup_name.replace("_", " "), bg="#1e2749", fg="#4895ef",
                        font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=10, pady=(5, 0))
                
                # Stats
                stats_row = tk.Frame(setup_frame, bg="#1e2749")
                stats_row.pack(fill=tk.X, padx=10, pady=5)
                
                tk.Label(stats_row, text=f"{wins}W / {losses}L", bg="#1e2749",
                        fg="#06ffa5" if wins > losses else "#ff006e",
                        font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=5)
                
                tk.Label(stats_row, text=f"WR: {wr:.1f}%", bg="#1e2749",
                        fg="#06ffa5" if wr >= 50 else "#ff006e",
                        font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=5)
                
                tk.Label(stats_row, text=f"{pips:+.1f} pips", bg="#1e2749",
                        fg="#06ffa5" if pips >= 0 else "#ff006e",
                        font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=5)
                
        except:
            pass
    
    def update_charts(self, history):
        """Actualizar gráficos"""
        self.fig.clear()
        
        # Crear subplots
        ax1 = self.fig.add_subplot(221, facecolor='#1e2749')
        ax2 = self.fig.add_subplot(222, facecolor='#1e2749')
        ax3 = self.fig.add_subplot(223, facecolor='#1e2749')
        ax4 = self.fig.add_subplot(224, facecolor='#1e2749')
        
        # Gráfico 1: Equity Curve
        pips = [t.get("pips", 0) for t in history]
        equity = [sum(pips[:i+1]) for i in range(len(pips))]
        
        ax1.plot(equity, color='#06ffa5' if equity[-1] >= 0 else '#ff006e', linewidth=2)
        ax1.set_title('Equity Curve', color='#e0e6ff', fontsize=10)
        ax1.tick_params(colors='#8b9dc3')
        ax1.grid(True, alpha=0.2, color='#4895ef')
        ax1.axhline(y=0, color='#8b9dc3', linestyle='--', alpha=0.5)
        
        # Gráfico 2: Win Rate por día
        daily_stats = defaultdict(lambda: {"wins": 0, "total": 0})
        for t in history:
            date = t.get("timestamp", "")[:10]
            if date:  # Solo si tiene fecha válida
                daily_stats[date]["total"] += 1
                if t.get("result") == "WIN":
                    daily_stats[date]["wins"] += 1
        
        if daily_stats:  # Solo si hay datos
            dates = sorted(daily_stats.keys())
            wr_daily = [(daily_stats[d]["wins"] / daily_stats[d]["total"] * 100) 
                        if daily_stats[d]["total"] > 0 else 0 for d in dates]
            
            colors = ['#06ffa5' if wr >= 50 else '#ff006e' for wr in wr_daily]
            ax2.bar(range(len(dates)), wr_daily, color=colors, alpha=0.7)
            ax2.axhline(y=50, color='#ffbe0b', linestyle='--', alpha=0.5, label='50% WR')
            ax2.set_ylim(0, 100)
            ax2.set_title('Win Rate Diario', color='#e0e6ff', fontsize=10)
            ax2.tick_params(colors='#8b9dc3')
            ax2.grid(True, alpha=0.2, color='#4895ef')
            ax2.legend(facecolor='#1e2749', edgecolor='#4895ef', fontsize=8)
        else:
            ax2.text(0.5, 0.5, 'Datos insuficientes', ha='center', va='center',
                    color='#8b9dc3', fontsize=10, transform=ax2.transAxes)
        
        # Gráfico 3: Distribución de Pips
        ax3.hist([t.get("pips", 0) for t in history], bins=20, color='#4895ef', alpha=0.7)
        ax3.axvline(x=0, color='#8b9dc3', linestyle='--', alpha=0.5)
        ax3.set_title('Distribución de Resultados', color='#e0e6ff', fontsize=10)
        ax3.tick_params(colors='#8b9dc3')
        ax3.grid(True, alpha=0.2, color='#4895ef')
        
        # Gráfico 4: Performance por Setup
        setup_stats = defaultdict(lambda: {"wins": 0, "losses": 0})
        for t in history:
            setup = t.get("setup", "Unknown")
            # Si setup está vacío, extraer del signal_id
            if not setup or setup == "Unknown":
                signal_id = t.get("signal_id", "")
                parts = signal_id.split("_")
                if len(parts) >= 4:
                    setup = "_".join(parts[3:])
            
            if t.get("result") == "WIN":
                setup_stats[setup]["wins"] += 1
            else:
                setup_stats[setup]["losses"] += 1
        
        if setup_stats:
            setups = list(setup_stats.keys())
            wins_data = [setup_stats[s]["wins"] for s in setups]
            losses_data = [setup_stats[s]["losses"] for s in setups]
            
            x = range(len(setups))
            ax4.bar(x, wins_data, label='Wins', color='#06ffa5', alpha=0.7)
            ax4.bar(x, [-l for l in losses_data], label='Losses', color='#ff006e', alpha=0.7)
            ax4.set_xticks(x)
            # Formatear nombres de setups
            setup_labels = [s.replace("_", " ")[:15] for s in setups]
            ax4.set_xticklabels(setup_labels, rotation=45, ha='right', fontsize=8)
            ax4.set_title('Wins/Losses por Setup', color='#e0e6ff', fontsize=10)
            ax4.tick_params(colors='#8b9dc3')
            ax4.legend(facecolor='#1e2749', edgecolor='#4895ef', fontsize=8)
            ax4.grid(True, alpha=0.2, color='#4895ef')
            ax4.axhline(y=0, color='#8b9dc3', linestyle='-', alpha=0.3)
        else:
            ax4.text(0.5, 0.5, 'Datos insuficientes', ha='center', va='center',
                    color='#8b9dc3', fontsize=10, transform=ax4.transAxes)
        
        self.fig.tight_layout()
        self.canvas_chart.draw()
    
    def load_history(self):
        """Cargar historial de trades en la tabla"""
        # Limpiar tabla
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        
        # Cargar datos
        history = self.load_trade_history()
        
        # Filtrar
        filter_type = self.filter_var.get()
        if filter_type == "Solo Ganancias":
            history = [t for t in history if t.get("result") == "WIN"]
        elif filter_type == "Solo Pérdidas":
            history = [t for t in history if t.get("result") == "LOSS"]
        
        # Ordenar por fecha (más reciente primero)
        history = sorted(history, key=lambda x: x.get("timestamp", ""), reverse=True)
        
        # Agregar a tabla
        for trade in history[:100]:  # Limitar a 100 más recientes
            timestamp = trade.get("timestamp", "")
            signal_id = trade.get("signal_id", "")
            setup = trade.get("setup", "")
            
            # Si setup está vacío, extraer del signal_id
            if not setup:
                # Format: 20260206_010111_BUY_EURUSD o 20260206_010111_BUY_MEAN_REVERSION
                parts = signal_id.split("_")
                if len(parts) >= 4:
                    # Tomar todo después del BUY/SELL
                    setup = "_".join(parts[3:])
            
            # Extraer acción del signal_id
            action = "?"
            if "_BUY_" in signal_id:
                action = "BUY"
            elif "_SELL_" in signal_id:
                action = "SELL"
            
            result = trade.get("result", "")
            pips = trade.get("pips", 0)
            
            tag = "WIN" if result == "WIN" else "LOSS"
            
            # Formatear setup name (remover guiones bajos)
            setup_display = setup.replace("_", " ").title() if setup else "Unknown"
            
            self.history_tree.insert("", "end", values=(
                timestamp[:19],  # Solo fecha y hora, sin microsegundos
                signal_id[:25] + "..." if len(signal_id) > 25 else signal_id,
                setup_display,
                action,
                result,
                f"{pips:+.2f}"
            ), tags=(tag,))
    
    def export_history(self):
        """Exportar historial a CSV"""
        try:
            import csv
            from tkinter import filedialog
            
            filename = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
            )
            
            if filename:
                history = self.load_trade_history()
                
                with open(filename, "w", newline="") as f:
                    writer = csv.DictWriter(f, fieldnames=["timestamp", "signal_id", "setup", "result", "pips"])
                    writer.writeheader()
                    writer.writerows(history)
                
                messagebox.showinfo("Éxito", f"Historial exportado a:\n{filename}")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo exportar:\n{e}")
    
    def load_trade_history(self):
        """Cargar historial de trades desde archivo"""
        history_file = "learning_data/trade_history.json"
        
        if os.path.exists(history_file):
            try:
                with open(history_file, "r") as f:
                    return json.load(f)
            except:
                return []
        return []
    
    def filter_history_by_period(self, history, period):
        """Filtrar historial por período"""
        if period == "Hoy":
            today = datetime.now().strftime("%Y-%m-%d")
            return [t for t in history if t.get("timestamp", "").startswith(today)]
        
        elif period == "Esta Semana":
            week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
            return [t for t in history if t.get("timestamp", "") >= week_ago]
        
        elif period == "Este Mes":
            month_ago = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            return [t for t in history if t.get("timestamp", "") >= month_ago]
        
        else:  # Total
            return history
    
    def load_config(self):
        """Cargar configuración desde archivo"""
        config_file = "bot_config.json"
        
        if os.path.exists(config_file):
            try:
                with open(config_file, "r") as f:
                    return json.load(f)
            except:
                pass
        
        # Configuración por defecto
        return {
            "min_confidence": 75,
            "cooldown": 60,
            "max_daily_trades": 20,
            "max_losses": 3,
            "lot_size": 0.01,
            "start_hour": "08:00",
            "end_hour": "20:00"
        }
    
    def save_config_changes(self):
        """Guardar cambios de configuración"""
        try:
            # Recopilar valores
            new_config = {}
            for key, var in self.config_vars.items():
                new_config[key] = var.get()
            
            # Guardar en archivo
            with open("bot_config.json", "w") as f:
                json.dump(new_config, f, indent=4)
            
            self.config = new_config
            
            messagebox.showinfo("Éxito", "Configuración guardada correctamente")
            
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar:\n{e}")
    
    def check_file_status(self):
        """Verificar estado de archivos"""
        self.file_status_text.delete(1.0, tk.END)
        
        files = [
            ("Market Data", "/home/travieso/.wine/drive_c/Program Files/MetaTrader 5/MQL5/Files/market_data.json"),
            ("Signal", "/home/travieso/.wine/drive_c/Program Files/MetaTrader 5/MQL5/Files/signals/signal.json"),
            ("Trade Feedback", "/home/travieso/.wine/drive_c/Program Files/MetaTrader 5/MQL5/Files/trade_feedback.json"),
            ("Setup Stats", "learning_data/setup_stats.json"),
            ("Trade History", "learning_data/trade_history.json"),
            ("Processed Signals", "learning_data/processed_signals.txt")
        ]
        
        for name, path in files:
            exists = os.path.exists(path)
            status = "✓ EXISTE" if exists else "✗ NO EXISTE"
            color = "green" if exists else "red"
            
            self.file_status_text.insert(tk.END, f"{name:20s} ", "INFO")
            self.file_status_text.insert(tk.END, f"{status}\n", color)
            
            if exists:
                try:
                    size = os.path.getsize(path)
                    mtime = datetime.fromtimestamp(os.path.getmtime(path))
                    self.file_status_text.insert(tk.END, 
                        f"  Tamaño: {size} bytes | Modificado: {mtime.strftime('%Y-%m-%d %H:%M:%S')}\n\n",
                        "INFO")
                except:
                    self.file_status_text.insert(tk.END, "  (Error leyendo info del archivo)\n\n", "WARNING")
        
        self.file_status_text.tag_config("green", foreground="#06ffa5")
        self.file_status_text.tag_config("red", foreground="#ff006e")
        self.file_status_text.tag_config("INFO", foreground="#e0e6ff")
        self.file_status_text.tag_config("WARNING", foreground="#ffbe0b")
    
    def update_all_displays(self):
        """Actualizar todos los displays"""
        self.update_dashboard_stats()
        self.update_market_info()
        self.update_last_signal()
    
    def auto_update(self):
        """Actualización automática"""
        self.load_stats()
        self.update_all_displays()
        
        # Actualizar reloj en footer (si existe)
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Repetir cada segundo
        self.root.after(1000, self.auto_update)


# ========== EJECUCIÓN ==========
if __name__ == "__main__":
    root = tk.Tk()
    app = TradingBotGUI(root)
    root.mainloop()

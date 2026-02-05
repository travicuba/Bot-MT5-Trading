"""
bot_gui.py - Interfaz gráfica mejorada para Trading AI Bot

Características:
- Panel de estado visual (Running/Stopped/Error)
- Estadísticas en tiempo real (P&L, Win Rate, # Trades)
- Logs con colores y timestamps
- Panel de información del mercado actual
- Panel de última señal generada
- Historial de trades
"""

import threading
import tkinter as tk
from tkinter import ttk, scrolledtext
from datetime import datetime
import sys
import json
import os

import main


class TradingBotGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("🤖 Trading AI - Professional Controller")
        self.root.geometry("1400x900")
        self.root.configure(bg="#1e1e1e")
        
        # Variables de estado
        self.running_thread = None
        self.bot_state = "STOPPED"  # STOPPED, RUNNING, ERROR
        self.stats = {
            "total_trades": 0,
            "wins": 0,
            "losses": 0,
            "total_pips": 0.0,
            "win_rate": 0.0
        }
        
        # ========== CONFIGURAR ESTILO ==========
        self.setup_styles()
        
        # ========== LAYOUT PRINCIPAL ==========
        # Dividir en 3 secciones: Header, Main, Footer
        
        # HEADER: Estado y controles
        self.create_header()
        
        # MAIN: Dividido en Left (Stats + Market Info) y Right (Logs)
        main_frame = tk.Frame(self.root, bg="#1e1e1e")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Left Panel (30%)
        left_panel = tk.Frame(main_frame, bg="#1e1e1e", width=400)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 5))
        left_panel.pack_propagate(False)
        
        # Right Panel (70%)
        right_panel = tk.Frame(main_frame, bg="#1e1e1e")
        right_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Crear paneles
        self.create_stats_panel(left_panel)
        self.create_market_info_panel(left_panel)
        self.create_last_signal_panel(left_panel)
        self.create_logs_panel(right_panel)
        
        # FOOTER: Información adicional
        self.create_footer()
        
        # ========== INICIALIZAR ==========
        self.load_stats()
        self.update_display()
        
        # Actualizar display cada segundo
        self.auto_update()
        
        # Redirigir prints a la GUI
        sys.stdout = self
        sys.stderr = self
    
    def setup_styles(self):
        """Configurar estilos ttk"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Colores
        bg_dark = "#1e1e1e"
        bg_panel = "#2d2d2d"
        fg_text = "#ffffff"
        accent_green = "#4CAF50"
        accent_red = "#f44336"
        accent_blue = "#2196F3"
        
        # Frame styles
        style.configure("Dark.TFrame", background=bg_dark)
        style.configure("Panel.TFrame", background=bg_panel)
        
        # Label styles
        style.configure("Title.TLabel", 
                       background=bg_panel, 
                       foreground=fg_text, 
                       font=("Arial", 12, "bold"))
        
        style.configure("Stat.TLabel",
                       background=bg_panel,
                       foreground=fg_text,
                       font=("Arial", 10))
        
        style.configure("Value.TLabel",
                       background=bg_panel,
                       foreground=accent_blue,
                       font=("Arial", 14, "bold"))
    
    def create_header(self):
        """Panel superior con estado y controles"""
        header = tk.Frame(self.root, bg="#2d2d2d", height=100)
        header.pack(fill=tk.X, padx=10, pady=(10, 5))
        
        # Estado visual
        status_frame = tk.Frame(header, bg="#2d2d2d")
        status_frame.pack(side=tk.LEFT, padx=20, pady=10)
        
        tk.Label(status_frame, text="Estado:", bg="#2d2d2d", fg="white", 
                font=("Arial", 10)).pack()
        
        self.status_indicator = tk.Canvas(status_frame, width=60, height=60, 
                                         bg="#2d2d2d", highlightthickness=0)
        self.status_indicator.pack(pady=5)
        
        self.status_circle = self.status_indicator.create_oval(10, 10, 50, 50, 
                                                               fill="#808080", outline="")
        
        self.status_label = tk.Label(status_frame, text="DETENIDO", 
                                     bg="#2d2d2d", fg="white", 
                                     font=("Arial", 10, "bold"))
        self.status_label.pack()
        
        # Botones de control
        btn_frame = tk.Frame(header, bg="#2d2d2d")
        btn_frame.pack(side=tk.LEFT, padx=20, pady=10)
        
        self.start_btn = tk.Button(
            btn_frame,
            text="▶️ INICIAR BOT",
            command=self.start_bot,
            bg="#4CAF50",
            fg="white",
            font=("Arial", 12, "bold"),
            width=15,
            height=2,
            relief=tk.FLAT,
            cursor="hand2"
        )
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = tk.Button(
            btn_frame,
            text="⏹️ DETENER BOT",
            command=self.stop_bot,
            bg="#f44336",
            fg="white",
            font=("Arial", 12, "bold"),
            width=15,
            height=2,
            relief=tk.FLAT,
            cursor="hand2",
            state=tk.DISABLED
        )
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        self.restart_btn = tk.Button(
            btn_frame,
            text="🔄 REINICIAR",
            command=self.restart_bot,
            bg="#FF9800",
            fg="white",
            font=("Arial", 12, "bold"),
            width=15,
            height=2,
            relief=tk.FLAT,
            cursor="hand2"
        )
        self.restart_btn.pack(side=tk.LEFT, padx=5)
        
        # Título
        title_frame = tk.Frame(header, bg="#2d2d2d")
        title_frame.pack(side=tk.RIGHT, padx=20)
        
        tk.Label(title_frame, text="🤖 TRADING AI", bg="#2d2d2d", 
                fg="#2196F3", font=("Arial", 20, "bold")).pack()
        tk.Label(title_frame, text="Advanced Market Intelligence System", 
                bg="#2d2d2d", fg="#888", font=("Arial", 10)).pack()
    
    def create_stats_panel(self, parent):
        """Panel de estadísticas"""
        frame = tk.LabelFrame(parent, text="📊 ESTADÍSTICAS", bg="#2d2d2d", 
                             fg="white", font=("Arial", 11, "bold"),
                             relief=tk.RAISED, borderwidth=2)
        frame.pack(fill=tk.X, pady=5)
        
        # Grid de estadísticas
        stats_grid = tk.Frame(frame, bg="#2d2d2d")
        stats_grid.pack(fill=tk.X, padx=10, pady=10)
        
        # Total Trades
        self.create_stat_row(stats_grid, 0, "Total Trades:", "total_trades_label")
        
        # Wins
        self.create_stat_row(stats_grid, 1, "Ganadas:", "wins_label", color="#4CAF50")
        
        # Losses
        self.create_stat_row(stats_grid, 2, "Perdidas:", "losses_label", color="#f44336")
        
        # Win Rate
        self.create_stat_row(stats_grid, 3, "Win Rate:", "win_rate_label", color="#2196F3")
        
        # Total Pips
        self.create_stat_row(stats_grid, 4, "Total Pips:", "total_pips_label", color="#FF9800")
    
    def create_stat_row(self, parent, row, label_text, var_name, color="#2196F3"):
        """Crear fila de estadística"""
        tk.Label(parent, text=label_text, bg="#2d2d2d", fg="#aaa", 
                font=("Arial", 10), anchor="w").grid(row=row, column=0, 
                                                      sticky="w", pady=5, padx=5)
        
        label = tk.Label(parent, text="0", bg="#2d2d2d", fg=color, 
                        font=("Arial", 14, "bold"), anchor="e")
        label.grid(row=row, column=1, sticky="e", pady=5, padx=5)
        
        setattr(self, var_name, label)
        
        # Configurar columnas
        parent.columnconfigure(0, weight=1)
        parent.columnconfigure(1, weight=1)
    
    def create_market_info_panel(self, parent):
        """Panel de información del mercado"""
        frame = tk.LabelFrame(parent, text="📈 MERCADO ACTUAL", bg="#2d2d2d",
                             fg="white", font=("Arial", 11, "bold"),
                             relief=tk.RAISED, borderwidth=2)
        frame.pack(fill=tk.X, pady=5)
        
        info_frame = tk.Frame(frame, bg="#2d2d2d")
        info_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Símbolo
        self.create_info_row(info_frame, 0, "Símbolo:", "symbol_label")
        
        # Tendencia
        self.create_info_row(info_frame, 1, "Tendencia:", "trend_label")
        
        # Volatilidad
        self.create_info_row(info_frame, 2, "Volatilidad:", "volatility_label")
        
        # RSI
        self.create_info_row(info_frame, 3, "RSI:", "rsi_label")
        
        # Régimen
        self.create_info_row(info_frame, 4, "Régimen:", "regime_label")
    
    def create_info_row(self, parent, row, label_text, var_name):
        """Crear fila de información"""
        tk.Label(parent, text=label_text, bg="#2d2d2d", fg="#aaa",
                font=("Arial", 9), anchor="w").grid(row=row, column=0,
                                                     sticky="w", pady=3, padx=5)
        
        label = tk.Label(parent, text="--", bg="#2d2d2d", fg="white",
                        font=("Arial", 10), anchor="e")
        label.grid(row=row, column=1, sticky="e", pady=3, padx=5)
        
        setattr(self, var_name, label)
        
        parent.columnconfigure(0, weight=1)
        parent.columnconfigure(1, weight=1)
    
    def create_last_signal_panel(self, parent):
        """Panel de última señal"""
        frame = tk.LabelFrame(parent, text="🎯 ÚLTIMA SEÑAL", bg="#2d2d2d",
                             fg="white", font=("Arial", 11, "bold"),
                             relief=tk.RAISED, borderwidth=2)
        frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.signal_text = scrolledtext.ScrolledText(
            frame, height=10, bg="#1e1e1e", fg="white",
            font=("Consolas", 9), relief=tk.FLAT,
            wrap=tk.WORD
        )
        self.signal_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    def create_logs_panel(self, parent):
        """Panel de logs mejorado"""
        frame = tk.LabelFrame(parent, text="📋 LOGS DEL SISTEMA", bg="#2d2d2d",
                             fg="white", font=("Arial", 11, "bold"),
                             relief=tk.RAISED, borderwidth=2)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Botón para limpiar logs
        btn_frame = tk.Frame(frame, bg="#2d2d2d")
        btn_frame.pack(fill=tk.X, padx=5, pady=5)
        
        tk.Button(btn_frame, text="🗑️ Limpiar Logs", command=self.clear_logs,
                 bg="#555", fg="white", relief=tk.FLAT, cursor="hand2").pack(side=tk.RIGHT)
        
        # Área de logs con colores
        self.log_box = scrolledtext.ScrolledText(
            frame, height=30, bg="#1e1e1e", fg="#00ff00",
            font=("Consolas", 9), relief=tk.FLAT,
            wrap=tk.WORD
        )
        self.log_box.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Configurar tags para colores
        self.log_box.tag_config("ERROR", foreground="#f44336")
        self.log_box.tag_config("WARNING", foreground="#FF9800")
        self.log_box.tag_config("SUCCESS", foreground="#4CAF50")
        self.log_box.tag_config("INFO", foreground="#2196F3")
        self.log_box.tag_config("TIMESTAMP", foreground="#888")
    
    def create_footer(self):
        """Pie de página con info adicional"""
        footer = tk.Frame(self.root, bg="#2d2d2d", height=30)
        footer.pack(fill=tk.X, padx=10, pady=(5, 10))
        
        self.footer_label = tk.Label(
            footer, text="Sistema listo | Esperando inicio...",
            bg="#2d2d2d", fg="#888", font=("Arial", 9)
        )
        self.footer_label.pack(side=tk.LEFT, padx=10)
        
        self.time_label = tk.Label(
            footer, text="",
            bg="#2d2d2d", fg="#888", font=("Arial", 9)
        )
        self.time_label.pack(side=tk.RIGHT, padx=10)
    
    # ========== MÉTODOS DE CONTROL ==========
    
    def start_bot(self):
        """Iniciar el bot"""
        if self.running_thread and self.running_thread.is_alive():
            self.write("⚠️ El bot ya está en ejecución\n", "WARNING")
            return
        
        self.bot_state = "RUNNING"
        self.update_status_indicator()
        self.write("🚀 Iniciando bot...\n", "SUCCESS")
        
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        
        self.running_thread = threading.Thread(
            target=main.start_bot,
            daemon=True
        )
        self.running_thread.start()
    
    def stop_bot(self):
        """Detener el bot"""
        self.write("🛑 Deteniendo bot...\n", "WARNING")
        main.stop_bot()
        
        self.bot_state = "STOPPED"
        self.update_status_indicator()
        
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
    
    def restart_bot(self):
        """Reiniciar el bot"""
        if self.bot_state == "RUNNING":
            self.stop_bot()
            self.root.after(2000, self.start_bot)  # Esperar 2s antes de reiniciar
        else:
            self.start_bot()
    
    def clear_logs(self):
        """Limpiar logs"""
        self.log_box.delete(1.0, tk.END)
        self.write("📋 Logs limpiados\n", "INFO")
    
    # ========== MÉTODOS DE ACTUALIZACIÓN ==========
    
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
            "STOPPED": "#808080",
            "RUNNING": "#4CAF50",
            "ERROR": "#f44336"
        }
        
        labels = {
            "STOPPED": "DETENIDO",
            "RUNNING": "CORRIENDO",
            "ERROR": "ERROR"
        }
        
        color = colors.get(self.bot_state, "#808080")
        label = labels.get(self.bot_state, "DETENIDO")
        
        self.status_indicator.itemconfig(self.status_circle, fill=color)
        self.status_label.config(text=label)
        
        # Animación de pulso cuando está corriendo
        if self.bot_state == "RUNNING":
            self.pulse_indicator()
    
    def pulse_indicator(self):
        """Efecto de pulso en el indicador"""
        if self.bot_state == "RUNNING":
            # Alternar brillo
            current_color = self.status_indicator.itemcget(self.status_circle, "fill")
            new_color = "#66BB6A" if current_color == "#4CAF50" else "#4CAF50"
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
                
                self.stats["wins"] = total_wins
                self.stats["losses"] = total_losses
                self.stats["total_trades"] = total_wins + total_losses
                
                if self.stats["total_trades"] > 0:
                    self.stats["win_rate"] = (total_wins / self.stats["total_trades"]) * 100
                
            except Exception as e:
                print(f"⚠️ Error cargando stats: {e}")
    
    def update_display(self):
        """Actualizar todos los displays"""
        # Actualizar estadísticas
        self.total_trades_label.config(text=str(self.stats["total_trades"]))
        self.wins_label.config(text=str(self.stats["wins"]))
        self.losses_label.config(text=str(self.stats["losses"]))
        self.win_rate_label.config(text=f"{self.stats['win_rate']:.1f}%")
        self.total_pips_label.config(text=f"{self.stats['total_pips']:.1f}")
        
        # Actualizar info de mercado desde market_data.json
        self.update_market_info()
        
        # Actualizar última señal
        self.update_last_signal()
    
    def update_market_info(self):
        """Actualizar información del mercado"""
        market_file = "/home/travieso/.wine/drive_c/Program Files/MetaTrader 5/MQL5/Files/market_data.json"
        
        if os.path.exists(market_file):
            try:
                with open(market_file, "r") as f:
                    data = json.load(f)
                
                self.symbol_label.config(text=data.get("symbol", "--"))
                
                analysis = data.get("analysis", {})
                self.trend_label.config(text=analysis.get("trend", "--"))
                self.volatility_label.config(text=analysis.get("volatility", "--"))
                self.regime_label.config(text=analysis.get("market_regime", "--") if "market_regime" in analysis else "--")
                
                indicators = data.get("indicators", {})
                rsi = indicators.get("rsi", "--")
                self.rsi_label.config(text=f"{rsi:.1f}" if isinstance(rsi, (int, float)) else "--")
                
            except:
                pass
    
    def update_last_signal(self):
        """Actualizar última señal generada"""
        signal_file = "/home/travieso/.wine/drive_c/Program Files/MetaTrader 5/MQL5/Files/signals/signal.json"
        
        if os.path.exists(signal_file):
            try:
                with open(signal_file, "r") as f:
                    signal = json.load(f)
                
                self.signal_text.delete(1.0, tk.END)
                
                text = f"""
Action: {signal.get('action', 'N/A')}
Confidence: {signal.get('confidence', 0) * 100:.1f}%
SL: {signal.get('sl_pips', 0)} pips
TP: {signal.get('tp_pips', 0)} pips
Setup: {signal.get('setup_name', 'N/A')}
Timestamp: {signal.get('timestamp', 'N/A')}
Reason: {signal.get('reason', 'N/A')}
                """
                
                self.signal_text.insert(1.0, text.strip())
                
            except:
                pass
    
    def auto_update(self):
        """Actualización automática cada segundo"""
        self.update_display()
        
        # Actualizar reloj
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.time_label.config(text=current_time)
        
        # Estado del footer
        if self.bot_state == "RUNNING":
            self.footer_label.config(text="✅ Bot operando | Monitoreando mercado...")
        elif self.bot_state == "ERROR":
            self.footer_label.config(text="❌ Error detectado | Revisar logs")
        else:
            self.footer_label.config(text="⏸️ Bot detenido | Esperando inicio...")
        
        # Repetir cada 1000ms
        self.root.after(1000, self.auto_update)


# ========== EJECUCIÓN ==========
if __name__ == "__main__":
    root = tk.Tk()
    app = TradingBotGUI(root)
    root.mainloop()

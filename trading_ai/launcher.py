"""
launcher.py - Punto de entrada principal del Sistema de Trading Unificado

Gestiona la navegación entre:
  - Pantalla de Inicio (Home / Menú Principal)
  - Panel MetaTrader 5
  - Panel BingX Futures
  - Configuración General y por plataforma
"""

import tkinter as tk
import sys
import os

# Asegurar que el directorio actual esté en el path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

APP_VERSION = "3.0.0"


class TradingLauncher:
    """Gestor principal de navegación del sistema de trading unificado."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Trading AI — Sistema Unificado")
        self.root.geometry("1600x1000")
        self.root.minsize(1200, 780)
        self.root.configure(bg="#0a0e27")

        # Intentar centrar la ventana
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - 1600) // 2
        y = (sh - 1000) // 2
        self.root.geometry(f"1600x1000+{max(0, x)}+{max(0, y)}")

        # Contenedor principal (toda la ventana)
        self.container = tk.Frame(self.root, bg="#0a0e27")
        self.container.pack(fill=tk.BOTH, expand=True)

        # Instancias cacheadas de paneles (se destruyen al volver al home)
        self._mt5_instance = None
        self._bingx_instance = None

        # Mostrar pantalla de inicio
        self.show_home()

    # ------------------------------------------------------------------
    # Navegación
    # ------------------------------------------------------------------

    def _clear_container(self):
        """Destruir todos los widgets del contenedor."""
        for widget in self.container.winfo_children():
            widget.destroy()
        self._mt5_instance = None
        self._bingx_instance = None

    def show_home(self):
        """Mostrar la pantalla de inicio."""
        from home_screen import HomeScreen
        self._clear_container()
        self.root.title("Trading AI — Menú Principal")
        home = HomeScreen(
            self.container,
            on_mt5=self.show_mt5,
            on_bingx=self.show_bingx,
            on_settings=lambda: self.show_settings(mode=None),
        )
        home.pack(fill=tk.BOTH, expand=True)

    def show_mt5(self):
        """Mostrar el panel de MetaTrader 5."""
        from bot_gui_professional import TradingBotGUI
        self._clear_container()
        self.root.title("Trading AI — MetaTrader 5")
        self._mt5_instance = TradingBotGUI(
            self.root,
            parent=self.container,
            on_home=self.show_home,
        )

    def show_bingx(self):
        """Mostrar el panel de BingX Futures."""
        from bingx_gui import BingXPanel
        self._clear_container()
        self.root.title("Trading AI — BingX Futures")
        self._bingx_instance = BingXPanel(
            self.container,
            self.root,
            on_home=self.show_home,
        )
        self._bingx_instance.pack(fill=tk.BOTH, expand=True)

    def show_settings(self, mode=None):
        """
        Mostrar pantalla de configuración.

        mode=None  -> Configuración general
        mode='mt5' -> Solo ajustes MT5
        mode='bingx' -> Solo ajustes BingX
        """
        from settings_screen import SettingsScreen
        self._clear_container()
        title_map = {
            None: "Configuración General",
            "mt5": "Configuración — MetaTrader 5",
            "bingx": "Configuración — BingX",
        }
        self.root.title(f"Trading AI — {title_map.get(mode, 'Configuración')}")
        settings = SettingsScreen(
            self.container,
            self.root,
            on_back=self.show_home,
            mode=mode,
        )
        settings.pack(fill=tk.BOTH, expand=True)

    # ------------------------------------------------------------------
    # Arranque
    # ------------------------------------------------------------------

    def run(self):
        """Iniciar el bucle principal de la aplicación."""
        self.root.mainloop()


# ========== EJECUCIÓN ==========
if __name__ == "__main__":
    app = TradingLauncher()
    app.run()

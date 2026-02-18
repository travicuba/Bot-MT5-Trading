"""
launcher.py - Punto de entrada principal del Sistema de Trading Unificado

Navegación basada en OCULTAMIENTO de frames (pack_forget / pack), NO en
destrucción. Esto permite que el bot MT5 o BingX continúe ejecutándose en
segundo plano mientras el usuario navega a otra sección.
"""

import tkinter as tk
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

APP_VERSION = "3.0.1"


class TradingLauncher:
    """
    Gestor de navegación del sistema de trading.

    Estrategia de navegación:
      - Home, MT5 y BingX son paneles PERSISTENTES: se crean una sola vez y se
        muestran/ocultan con pack()/pack_forget().  El hilo del bot y los
        callbacks after() continúan funcionando aunque el panel esté oculto.
      - Settings es TRANSITORIO: se destruye y re-crea cada vez para reflejar
        la configuración más actualizada.
    """

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Trading AI — Sistema Unificado")
        self.root.geometry("1600x1000")
        self.root.minsize(1200, 780)
        self.root.configure(bg="#0a0e27")
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # Centrar ventana
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = max(0, (sw - 1600) // 2)
        y = max(0, (sh - 1000) // 2)
        self.root.geometry(f"1600x1000+{x}+{y}")

        # Contenedor raíz de todos los paneles
        self.container = tk.Frame(self.root, bg="#0a0e27")
        self.container.pack(fill=tk.BOTH, expand=True)

        # Registro de frames persistentes y sus instancias
        # {'home': tk.Frame, 'mt5': tk.Frame, 'bingx': tk.Frame}
        self._frames: dict[str, tk.Frame] = {}
        self._instances: dict[str, object] = {}
        self._current: str | None = None

        # Frame transitorio para Settings (destruido y re-creado cada vez)
        self._settings_frame: tk.Frame | None = None

        # Mostrar inicio
        self.show_home()

    # ──────────────────────────────────────────
    # Utilidad de navegación
    # ──────────────────────────────────────────

    def _show_persistent(self, name: str, builder):
        """
        Muestra un panel persistente.
        - Si no existe, lo construye llamando a builder(frame).
        - Si ya existe, simplemente lo hace visible.
        - Oculta cualquier otro panel (persistente o settings).
        """
        # Destruir Settings transitorio si existe
        self._destroy_settings()

        # Ocultar panel actual
        if self._current and self._current in self._frames:
            self._frames[self._current].pack_forget()

        # Crear panel si es la primera vez
        if name not in self._frames:
            frame = tk.Frame(self.container, bg="#0a0e27")
            self._frames[name] = frame
            instance = builder(frame)
            self._instances[name] = instance

        # Mostrar
        self._frames[name].pack(fill=tk.BOTH, expand=True)
        self._current = name

    def _show_settings(self, mode=None):
        """
        Muestra la pantalla de configuración (transitoria).
        Se destruye cada vez que se sale para leer config actualizada.
        """
        # Ocultar panel actual persistente
        if self._current and self._current in self._frames:
            self._frames[self._current].pack_forget()
        # Si había un settings anterior, destruirlo
        self._destroy_settings()

        from settings_screen import SettingsScreen
        self._settings_frame = tk.Frame(self.container, bg="#0a0e27")
        s = SettingsScreen(
            self._settings_frame,
            self.root,
            on_back=self.show_home,
            mode=mode,
        )
        s.pack(fill=tk.BOTH, expand=True)
        self._settings_frame.pack(fill=tk.BOTH, expand=True)

    def _destroy_settings(self):
        """Destruye el frame de Settings si existe."""
        if self._settings_frame is not None:
            try:
                self._settings_frame.destroy()
            except Exception:
                pass
            self._settings_frame = None

    # ──────────────────────────────────────────
    # Pantallas públicas
    # ──────────────────────────────────────────

    def show_home(self):
        """Mostrar la pantalla de inicio (Menú Principal)."""
        self.root.title("Trading AI — Menú Principal")

        def _build(frame):
            from home_screen import HomeScreen
            home = HomeScreen(
                frame,
                on_mt5=self.show_mt5,
                on_bingx=self.show_bingx,
                on_settings=lambda: self._show_settings(mode=None),
            )
            home.pack(fill=tk.BOTH, expand=True)
            return home

        self._show_persistent("home", _build)

    def show_mt5(self):
        """Mostrar el panel de MetaTrader 5."""
        self.root.title("Trading AI — MetaTrader 5")

        def _build(frame):
            from bot_gui_professional import TradingBotGUI
            instance = TradingBotGUI(
                self.root,
                parent=frame,
                on_home=self.show_home,
            )
            return instance

        self._show_persistent("mt5", _build)

    def show_bingx(self):
        """Mostrar el panel de BingX Futures."""
        self.root.title("Trading AI — BingX Futures")

        def _build(frame):
            from bingx_gui import BingXPanel
            panel = BingXPanel(frame, self.root, on_home=self.show_home)
            panel.pack(fill=tk.BOTH, expand=True)
            return panel

        self._show_persistent("bingx", _build)

    def show_settings(self, mode=None):
        """Mostrar configuración (acceso público desde botones externos)."""
        title_map = {None: "General", "mt5": "MetaTrader 5", "bingx": "BingX"}
        self.root.title(f"Trading AI — Configuración {title_map.get(mode, '')}")
        self._show_settings(mode=mode)

    # ──────────────────────────────────────────
    # Cierre seguro
    # ──────────────────────────────────────────

    def _on_close(self):
        """Confirmar cierre si algún bot está activo."""
        mt5_running = False
        bx_running  = False

        mt5_inst = self._instances.get("mt5")
        if mt5_inst and getattr(mt5_inst, "bot_state", "STOPPED") == "RUNNING":
            mt5_running = True

        bx_inst = self._instances.get("bingx")
        if bx_inst and getattr(bx_inst, "bot_state", "STOPPED") == "RUNNING":
            bx_running = True

        if mt5_running or bx_running:
            from tkinter import messagebox
            bots = []
            if mt5_running:
                bots.append("MT5")
            if bx_running:
                bots.append("BingX")
            ans = messagebox.askyesno(
                "Bot activo",
                f"Los siguientes bots están ejecutándose: {', '.join(bots)}\n\n"
                "¿Deseas cerrar la aplicación? Los bots se detendrán.",
            )
            if not ans:
                return

        # Restaurar stdout antes de salir
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__
        self.root.destroy()

    # ──────────────────────────────────────────
    # Arranque
    # ──────────────────────────────────────────

    def run(self):
        self.root.mainloop()


# ========== EJECUCIÓN ==========
if __name__ == "__main__":
    app = TradingLauncher()
    app.run()

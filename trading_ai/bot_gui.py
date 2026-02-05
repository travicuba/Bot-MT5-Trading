import threading
import tkinter as tk
from tkinter.scrolledtext import ScrolledText
import sys

import main  # tu motor


class TradingBotGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Trading AI Controller")

        self.running_thread = None

        # -------- BOTONES --------
        btn_frame = tk.Frame(root)
        btn_frame.pack(pady=10)

        self.start_btn = tk.Button(
            btn_frame, text="▶️ Iniciar", width=15, command=self.start_bot
        )
        self.start_btn.pack(side=tk.LEFT, padx=5)

        self.stop_btn = tk.Button(
            btn_frame, text="⏹️ Detener", width=15, command=self.stop_bot
        )
        self.stop_btn.pack(side=tk.LEFT, padx=5)

        # -------- LOGS --------
        self.log_box = ScrolledText(root, height=25, width=100)
        self.log_box.pack(padx=10, pady=10)

        # Redirigir prints a la GUI
        sys.stdout = self
        sys.stderr = self

    def write(self, message):
        self.log_box.insert(tk.END, message)
        self.log_box.see(tk.END)

    def flush(self):
        pass

    def start_bot(self):
        if self.running_thread and self.running_thread.is_alive():
            self.write("⚠️ El bot ya está en ejecución\n")
            return

        self.write("🚀 Iniciando bot...\n")

        self.running_thread = threading.Thread(
            target=main.start_bot,  # ✅ CORRECTO
            daemon=True
        )
        self.running_thread.start()

    def stop_bot(self):
        self.write("🛑 Deteniendo bot...\n")
        main.stop_bot()  # ✅ CORRECTO


# -------- EJECUCIÓN --------
if __name__ == "__main__":
    root = tk.Tk()
    app = TradingBotGUI(root)
    root.mainloop()
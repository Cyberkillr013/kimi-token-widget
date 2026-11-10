import argparse
import os
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import font

from token_usage import collect_sessions, summarize


def draw_avatar(canvas):
    purple = "#8b7cff"
    light_purple = "#b9b0ff"
    face = "#c9c2ff"
    dark = "#28223f"
    pink = "#ff9ebd"
    gold = "#ffe59a"

    canvas.create_polygon(12, 21, 16, 5, 29, 16, fill=purple, outline=light_purple, width=2)
    canvas.create_polygon(36, 16, 49, 5, 53, 22, fill=purple, outline=light_purple, width=2)
    canvas.create_polygon(16, 15, 18, 9, 24, 15, fill=pink, outline="")
    canvas.create_polygon(41, 15, 47, 9, 49, 16, fill=pink, outline="")
    canvas.create_oval(7, 10, 57, 60, fill=purple, outline=light_purple, width=2)
    canvas.create_oval(14, 20, 50, 55, fill=face, outline="")

    canvas.create_polygon(
        32, 15, 34, 19, 38, 19, 35, 22, 36, 26, 32, 23.5, 28, 26, 29, 22, 26, 19, 30, 19,
        fill=gold,
        outline="",
    )
    canvas.create_polygon(54, 3, 55.5, 7, 59, 7, 56.5, 9, 57.5, 13, 54, 10.5, 50.5, 13, 51.5, 9, 49, 7, 52.5, 7, fill=gold, outline="")
    canvas.create_oval(3, 32, 6, 35, fill=gold, outline="")

    canvas.create_oval(21, 29, 26, 35, fill=dark, outline="")
    canvas.create_oval(38, 29, 43, 35, fill=dark, outline="")
    canvas.create_oval(22, 30, 24, 32, fill="white", outline="")
    canvas.create_oval(39, 30, 41, 32, fill="white", outline="")
    canvas.create_oval(16, 38, 23, 42, fill=pink, outline="")
    canvas.create_oval(41, 38, 48, 42, fill=pink, outline="")
    canvas.create_oval(30, 36, 34, 39, fill=dark, outline="")
    canvas.create_line(28, 40, 30, 42, 32, 43, 34, 42, 36, 40, fill=dark, width=2, smooth=True)
    canvas.create_line(13, 43, 20, 42, fill=dark, width=1)
    canvas.create_line(14, 47, 21, 44, fill=dark, width=1)
    canvas.create_line(44, 42, 51, 43, fill=dark, width=1)
    canvas.create_line(43, 44, 50, 47, fill=dark, width=1)


class TokenWidget:
    def __init__(self, root, data_root, refresh_seconds):
        self.root = root
        self.data_root = data_root
        self.refresh_seconds = refresh_seconds
        self.results = queue.Queue()
        self.loading = False
        self.closed = False
        self.topmost = tk.BooleanVar(value=True)

        self.background = "#10141f"
        self.panel = "#181e2b"
        self.foreground = "#f3f6fc"

        root.title("Kimi Token Usage")
        root.overrideredirect(True)
        root.attributes("-topmost", True)
        root.configure(bg=self.background, highlightbackground="#30394d", highlightthickness=1)
        root.resizable(False, False)

        width, height = 300, 104
        x = root.winfo_screenwidth() - width - 28
        y = root.winfo_screenheight() - height - 76
        root.geometry(f"{width}x{height}+{max(x, 0)}+{max(y, 0)}")

        self.total_font = font.Font(family="Segoe UI", size=20, weight="bold")
        self.total = tk.StringVar(value="…")

        main = tk.Frame(root, bg=self.panel)
        main.pack(fill="both", expand=True, padx=7, pady=7)

        avatar = tk.Canvas(main, width=64, height=64, bg=self.panel, highlightthickness=0, cursor="hand2")
        avatar.pack(side="left", padx=(7, 13))
        draw_avatar(avatar)
        total_label = tk.Label(main, textvariable=self.total, bg=self.panel, fg=self.foreground, font=self.total_font)
        total_label.pack(side="left", fill="x", expand=True, padx=(0, 9))

        self.menu = tk.Menu(
            root,
            tearoff=False,
            bg=self.panel,
            fg=self.foreground,
            activebackground="#30394d",
            activeforeground=self.foreground,
        )
        self.menu.add_checkbutton(label="Always on top", variable=self.topmost, command=self.toggle_topmost)
        self.menu.add_command(label="Refresh now", command=self.refresh)
        self.menu.add_separator()
        self.menu.add_command(label="Close", command=self.close)
        root.bind_all("<Button-3>", self.show_menu)
        root.bind("<Escape>", lambda event: self.close())
        avatar.bind("<Double-Button-1>", lambda event: self.refresh())

        for widget in (root, main, avatar, total_label):
            widget.bind("<ButtonPress-1>", self.start_drag)
            widget.bind("<B1-Motion>", self.drag)

        root.after(0, self.refresh)
        root.after(100, self.process_results)

    def refresh(self):
        if self.closed:
            return
        self.root.after(self.refresh_seconds * 1000, self.refresh)
        if self.loading:
            return
        self.loading = True
        threading.Thread(target=self.load_usage, daemon=True).start()

    def load_usage(self):
        try:
            summary = summarize(collect_sessions(self.data_root))
            self.results.put(("ok", summary))
        except Exception as error:
            self.results.put(("error", str(error)))

    def process_results(self):
        if self.closed:
            return
        try:
            while True:
                result = self.results.get_nowait()
                self.loading = False
                if result[0] == "error":
                    self.total.set("Unavailable")
                    self.total_font.configure(size=18)
                    continue
                total = f"{result[1]['totalTokens']:,}"
                self.total.set(total)
                self.total_font.configure(size=20 if len(total) <= 13 else 17)
        except queue.Empty:
            pass
        self.root.after(100, self.process_results)

    def toggle_topmost(self):
        self.root.attributes("-topmost", self.topmost.get())

    def show_menu(self, event):
        try:
            self.menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.menu.grab_release()

    def start_drag(self, event):
        self.drag_x = event.x_root - self.root.winfo_x()
        self.drag_y = event.y_root - self.root.winfo_y()

    def drag(self, event):
        self.root.geometry(f"+{event.x_root - self.drag_x}+{event.y_root - self.drag_y}")

    def close(self):
        self.closed = True
        self.root.destroy()


def main():
    parser = argparse.ArgumentParser(description="Show a live Kimi Code token-count desktop widget.")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(os.environ.get("KIMI_CODE_HOME", Path.home() / ".kimi-code")),
    )
    parser.add_argument("--refresh-seconds", type=int, default=15)
    args = parser.parse_args()
    if args.refresh_seconds < 5:
        parser.error("--refresh-seconds must be at least 5")

    root = tk.Tk()
    TokenWidget(root, args.root.expanduser(), args.refresh_seconds)
    root.mainloop()


if __name__ == "__main__":
    main()

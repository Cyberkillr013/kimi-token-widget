import argparse
import math
import os
import queue
import random
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import font

from token_usage import collect_sessions, summarize


def draw_avatar(canvas, look_x=0, look_y=0, blink=False, happy=False, grabbed=False, heart_offset=0):
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

    if grabbed:
        canvas.create_line(20, 30, 25, 32, 20, 34, fill=dark, width=2)
        canvas.create_line(44, 30, 39, 32, 44, 34, fill=dark, width=2)
    elif happy:
        canvas.create_line(20, 33, 23, 30, 26, 33, fill=dark, width=2, smooth=True)
        canvas.create_line(38, 33, 41, 30, 44, 33, fill=dark, width=2, smooth=True)
    elif blink:
        canvas.create_line(21, 32, 26, 32, fill=dark, width=2)
        canvas.create_line(38, 32, 43, 32, fill=dark, width=2)
    else:
        canvas.create_oval(21 + look_x, 29 + look_y, 26 + look_x, 35 + look_y, fill=dark, outline="")
        canvas.create_oval(38 + look_x, 29 + look_y, 43 + look_x, 35 + look_y, fill=dark, outline="")
        canvas.create_oval(22 + look_x, 30 + look_y, 24 + look_x, 32 + look_y, fill="white", outline="")
        canvas.create_oval(39 + look_x, 30 + look_y, 41 + look_x, 32 + look_y, fill="white", outline="")

    canvas.create_oval(16, 38, 23, 42, fill=pink, outline="")
    canvas.create_oval(41, 38, 48, 42, fill=pink, outline="")
    if happy:
        canvas.create_oval(28, 38, 36, 47, fill=dark, outline="")
        canvas.create_oval(30, 43, 34, 46, fill=pink, outline="")
    elif grabbed:
        canvas.create_oval(30, 39, 34, 44, fill=dark, outline="")
    else:
        canvas.create_oval(30, 36, 34, 39, fill=dark, outline="")
        canvas.create_line(28, 40, 30, 42, 32, 43, 34, 42, 36, 40, fill=dark, width=2, smooth=True)

    canvas.create_line(13, 43, 20, 42, fill=dark, width=1)
    canvas.create_line(14, 47, 21, 44, fill=dark, width=1)
    canvas.create_line(44, 42, 51, 43, fill=dark, width=1)
    canvas.create_line(43, 44, 50, 47, fill=dark, width=1)

    if heart_offset is not None:
        canvas.create_text(53, 19 - heart_offset, text="♥", fill=pink, font=("Segoe UI", 12, "bold"))
        canvas.create_text(10, 17 - heart_offset / 2, text="♥", fill=gold, font=("Segoe UI", 9, "bold"))


def transform_avatar(canvas, scale, offset_x, offset_y):
    for item in canvas.find_all():
        coordinates = canvas.coords(item)
        transformed = []
        for index in range(0, len(coordinates), 2):
            transformed.extend((
                32 + (coordinates[index] - 32) * scale + offset_x,
                32 + (coordinates[index + 1] - 32) * scale + offset_y,
            ))
        canvas.coords(item, *transformed)


class TokenWidget:
    def __init__(self, root, data_root, refresh_seconds):
        self.root = root
        self.data_root = data_root
        self.refresh_seconds = refresh_seconds
        self.results = queue.Queue()
        self.loading = False
        self.closed = False
        self.topmost = tk.BooleanVar(value=True)
        self.wandering = tk.BooleanVar(value=True)
        self.hovering = False
        self.dragging = False
        self.drag_moved = False
        self.pet_until = 0
        now = time.monotonic()
        self.next_blink = now + random.uniform(2, 5)
        self.blink_until = 0
        self.next_wander = now + 3
        self.wander_target = None

        self.background = "#10141f"
        self.panel = "#181e2b"
        self.foreground = "#f3f6fc"

        root.title("Kimi Token Usage")
        root.overrideredirect(True)
        root.attributes("-topmost", True)
        root.configure(bg=self.background, highlightbackground="#30394d", highlightthickness=1)
        root.resizable(False, False)

        width, height = 300, 104
        x = max(root.winfo_screenwidth() - width - 28, 0)
        y = max(root.winfo_screenheight() - height - 76, 0)
        root.geometry(f"{width}x{height}+{x}+{y}")
        self.wander_origin = (x, y)

        self.total_font = font.Font(family="Segoe UI", size=20, weight="bold")
        self.total = tk.StringVar(value="…")

        main = tk.Frame(root, bg=self.panel)
        main.pack(fill="both", expand=True, padx=7, pady=7)

        self.avatar = tk.Canvas(main, width=64, height=64, bg=self.panel, highlightthickness=0, cursor="hand2")
        self.avatar.pack(side="left", padx=(7, 13))
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
        self.menu.add_checkbutton(label="Wander nearby", variable=self.wandering, command=self.toggle_wandering)
        self.menu.add_command(label="Refresh now", command=self.refresh)
        self.menu.add_separator()
        self.menu.add_command(label="Close", command=self.close)
        root.bind_all("<Button-3>", self.show_menu)
        root.bind("<Escape>", lambda event: self.close())
        self.avatar.bind("<Double-Button-1>", lambda event: self.refresh())
        self.avatar.bind("<Enter>", lambda event: self.set_hover(True))
        self.avatar.bind("<Leave>", lambda event: self.set_hover(False))

        for widget in (root, main, self.avatar, total_label):
            widget.bind("<ButtonPress-1>", self.start_drag)
            widget.bind("<B1-Motion>", self.drag)
            widget.bind("<ButtonRelease-1>", self.stop_drag)

        root.after(0, self.refresh)
        root.after(70, self.animate)
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

    def animate(self):
        if self.closed:
            return
        now = time.monotonic()
        if now >= self.next_blink:
            self.blink_until = now + 0.14
            self.next_blink = now + random.uniform(2.5, 5.5)

        petting = now < self.pet_until
        happy = self.hovering or petting
        pointer_x, pointer_y = self.root.winfo_pointerxy()
        relative_x = pointer_x - self.avatar.winfo_rootx() - 32
        relative_y = pointer_y - self.avatar.winfo_rooty() - 32
        look_x = max(-1.8, min(1.8, relative_x / 35))
        look_y = max(-1.5, min(1.5, relative_y / 40))

        if petting:
            offset_x = math.sin(now * 18) * 1.2
            offset_y = -abs(math.sin(now * 9)) * 2.5
        elif self.hovering:
            offset_x = 0
            offset_y = math.sin(now * 6) * 1.8
        else:
            offset_x = 0
            offset_y = math.sin(now * 2.4) * 1.2
        scale = 1 + math.sin(now * 2.4) * 0.015
        heart_offset = (1.4 - (self.pet_until - now)) * 7 if petting else None

        self.avatar.delete("all")
        draw_avatar(
            self.avatar,
            look_x,
            look_y,
            blink=now < self.blink_until and not happy,
            happy=happy,
            grabbed=self.dragging and self.drag_moved,
            heart_offset=heart_offset,
        )
        transform_avatar(self.avatar, scale, offset_x, offset_y)
        self.update_wander(now)
        self.root.after(70, self.animate)

    def update_wander(self, now):
        if not self.wandering.get() or self.dragging:
            self.wander_target = None
            self.next_wander = now + 2
            return
        if now >= self.next_wander:
            origin_x, origin_y = self.wander_origin
            maximum_x = max(self.root.winfo_screenwidth() - self.root.winfo_width(), 0)
            maximum_y = max(self.root.winfo_screenheight() - self.root.winfo_height(), 0)
            self.wander_target = (
                min(max(origin_x + random.randint(-28, 28), 0), maximum_x),
                min(max(origin_y + random.randint(-20, 20), 0), maximum_y),
            )
            self.next_wander = now + random.uniform(4, 7)
        if self.wander_target:
            current_x, current_y = self.root.winfo_x(), self.root.winfo_y()
            target_x, target_y = self.wander_target
            difference_x, difference_y = target_x - current_x, target_y - current_y
            if abs(difference_x) <= 1 and abs(difference_y) <= 1:
                self.wander_target = None
            else:
                self.root.geometry(f"+{round(current_x + difference_x * 0.08)}+{round(current_y + difference_y * 0.08)}")

    def set_hover(self, hovering):
        self.hovering = hovering

    def pet(self):
        now = time.monotonic()
        self.pet_until = now + 1.4
        self.next_blink = now + 1.5

    def toggle_topmost(self):
        self.root.attributes("-topmost", self.topmost.get())

    def toggle_wandering(self):
        self.wander_origin = (self.root.winfo_x(), self.root.winfo_y())
        self.wander_target = None
        self.next_wander = time.monotonic() + 2

    def show_menu(self, event):
        try:
            self.menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.menu.grab_release()

    def start_drag(self, event):
        self.dragging = True
        self.drag_moved = False
        self.press_position = (event.x_root, event.y_root)
        self.drag_x = event.x_root - self.root.winfo_x()
        self.drag_y = event.y_root - self.root.winfo_y()

    def drag(self, event):
        if abs(event.x_root - self.press_position[0]) > 3 or abs(event.y_root - self.press_position[1]) > 3:
            self.drag_moved = True
        if self.drag_moved:
            self.root.geometry(f"+{event.x_root - self.drag_x}+{event.y_root - self.drag_y}")

    def stop_drag(self, event):
        if not self.dragging:
            return
        was_click = not self.drag_moved
        self.dragging = False
        self.wander_origin = (self.root.winfo_x(), self.root.winfo_y())
        self.wander_target = None
        self.next_wander = time.monotonic() + 4
        if was_click and event.widget is self.avatar:
            self.pet()

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

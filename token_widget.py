import argparse
import os
import queue
import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import font

from token_usage import collect_sessions, summarize


def compact_number(value):
    if value >= 1_000_000_000:
        return f"{value / 1_000_000_000:.2f}B"
    if value >= 1_000_000:
        return f"{value / 1_000_000:.2f}M"
    if value >= 1_000:
        return f"{value / 1_000:.1f}K"
    return str(value)


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
        self.muted = "#93a0b8"
        self.accent = "#8b7cff"

        root.title("Kimi Token Usage")
        root.overrideredirect(True)
        root.attributes("-topmost", True)
        root.configure(bg=self.background, highlightbackground="#30394d", highlightthickness=1)
        root.resizable(False, False)

        width, height = 370, 250
        x = root.winfo_screenwidth() - width - 28
        y = root.winfo_screenheight() - height - 76
        root.geometry(f"{width}x{height}+{max(x, 0)}+{max(y, 0)}")

        self.ui_font = font.Font(family="Segoe UI", size=10)
        self.total_font = font.Font(family="Segoe UI", size=25, weight="bold")
        self.heading_font = font.Font(family="Segoe UI", size=10, weight="bold")

        self.total = tk.StringVar(value="—")
        self.session_count = tk.StringVar(value="Reading local sessions…")
        self.breakdown = tk.StringVar(value="")
        self.latest = tk.StringVar(value="—")
        self.latest_title = tk.StringVar(value="Latest session")
        self.status = tk.StringVar(value="")

        header = tk.Frame(root, bg=self.background)
        header.pack(fill="x", padx=14, pady=(10, 4))
        title = tk.Label(
            header,
            text="KIMI TOKEN USAGE",
            bg=self.background,
            fg=self.accent,
            font=self.heading_font,
        )
        title.pack(side="left")
        self.make_button(header, "×", self.close, 12).pack(side="right")
        self.make_button(header, "↻", self.refresh, 11).pack(side="right", padx=(0, 8))

        main = tk.Frame(root, bg=self.panel)
        main.pack(fill="both", expand=True, padx=10, pady=(0, 8))

        tk.Label(main, text="ALL SESSIONS", bg=self.panel, fg=self.muted, font=self.ui_font).pack(
            anchor="w", padx=12, pady=(9, 0)
        )
        tk.Label(main, textvariable=self.total, bg=self.panel, fg=self.foreground, font=self.total_font).pack(
            anchor="w", padx=12
        )
        tk.Label(main, textvariable=self.session_count, bg=self.panel, fg=self.muted, font=self.ui_font).pack(
            anchor="w", padx=12
        )
        tk.Label(main, textvariable=self.breakdown, bg=self.panel, fg=self.muted, font=self.ui_font).pack(
            anchor="w", padx=12, pady=(3, 8)
        )

        latest_row = tk.Frame(main, bg=self.panel)
        latest_row.pack(fill="x", padx=12, pady=(0, 8))
        latest_text = tk.Frame(latest_row, bg=self.panel)
        latest_text.pack(side="left", fill="x", expand=True)
        tk.Label(
            latest_text,
            textvariable=self.latest_title,
            bg=self.panel,
            fg=self.muted,
            font=self.ui_font,
        ).pack(anchor="w")
        tk.Label(
            latest_row,
            textvariable=self.latest,
            bg=self.panel,
            fg=self.foreground,
            font=self.heading_font,
        ).pack(side="right")

        tk.Label(root, textvariable=self.status, bg=self.background, fg=self.muted, font=self.ui_font).pack(
            pady=(0, 7)
        )

        self.menu = tk.Menu(root, tearoff=False, bg=self.panel, fg=self.foreground, activebackground="#30394d")
        self.menu.add_checkbutton(label="Always on top", variable=self.topmost, command=self.toggle_topmost)
        self.menu.add_command(label="Refresh now", command=self.refresh)
        self.menu.add_separator()
        self.menu.add_command(label="Close", command=self.close)
        root.bind_all("<Button-3>", self.show_menu)

        for widget in (header, title):
            widget.bind("<ButtonPress-1>", self.start_drag)
            widget.bind("<B1-Motion>", self.drag)

        root.after(0, self.refresh)
        root.after(100, self.process_results)

    def make_button(self, parent, text, command, size):
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=self.background,
            fg=self.muted,
            activebackground=self.background,
            activeforeground=self.foreground,
            font=font.Font(family="Segoe UI", size=size),
            borderwidth=0,
            cursor="hand2",
            width=2,
        )

    def refresh(self):
        if self.loading or self.closed:
            return
        self.loading = True
        self.status.set("Refreshing…")
        threading.Thread(target=self.load_usage, daemon=True).start()
        if not self.closed:
            self.root.after(self.refresh_seconds * 1000, self.refresh)

    def load_usage(self):
        try:
            sessions = collect_sessions(self.data_root)
            summary = summarize(sessions)
            latest = next((session for session in sessions if session["usageRecords"]), None)
            self.results.put(("ok", summary, latest, datetime.now()))
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
                    self.status.set(f"Error: {result[1]}")
                    continue
                _, summary, latest, updated_at = result
                usage = summary["usage"]
                self.total.set(f"{summary['totalTokens']:,}")
                self.session_count.set(
                    f"{summary['sessions']} sessions · {summary['sessionsWithUsage']} with usage"
                )
                self.breakdown.set(
                    f"Input {compact_number(usage['inputOther'])}  ·  "
                    f"Cached {compact_number(usage['inputCacheRead'])}  ·  "
                    f"Output {compact_number(usage['output'])}"
                )
                if latest:
                    session_id = latest["sessionId"].removeprefix("session_")[:8]
                    self.latest_title.set(f"Latest session · {session_id}")
                    self.latest.set(f"{latest['totalTokens']:,}")
                else:
                    self.latest_title.set("Latest session")
                    self.latest.set("No usage")
                self.status.set(f"Updated {updated_at:%H:%M:%S} · every {self.refresh_seconds}s")
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

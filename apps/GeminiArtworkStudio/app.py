"""
app.py — Gemini Artwork Studio entry point.  Run with:  py app.py
"""

from __future__ import annotations

import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import customtkinter as ctk

from utils.settings import Settings
from engine.export.exporter import EXPORT_PROFILES
from engine.pipeline import BatchProcessor, ImageResult
from ui.widgets import DropZone, ImagePreviewPanel, LogPanel, ProgressSection
from ui.settings_panel import SettingsPanel
from utils.image_utils import collect_images

ACCENT  = "#7C6CFA"
BG      = "#11111B"
SURFACE = "#1E1E2E"
SURFACE2= "#27273A"
TEXT    = "#CDD6F4"
MUTED   = "#6C7086"
ERROR   = "#F38BA8"


class App(ctk.CTk):
    def __init__(self, settings: Settings):
        super().__init__()
        self._settings = settings
        self._queue: list[Path] = []
        self._processor = None
        self._batch_thread = None
        self._done_count = 0
        self._setup_window()
        self._build()

    def _setup_window(self):
        self.title("✦ Gemini Artwork Studio")
        w = int(self._settings.get("window_width", 1280))
        h = int(self._settings.get("window_height", 800))
        self.geometry(f"{w}x{h}")
        self.minsize(1100, 700)
        self.configure(fg_color=BG)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build(self):
        # Header
        header = ctk.CTkFrame(self, fg_color=SURFACE, height=56, corner_radius=0)
        header.pack(fill="x")
        header.pack_propagate(False)
        ctk.CTkLabel(
            header, text="✦  Gemini Artwork Studio",
            font=ctk.CTkFont(size=18, weight="bold"), text_color=ACCENT,
        ).pack(side="left", padx=20, pady=10)
        self._status = ctk.CTkLabel(
            header, text="Ready", font=ctk.CTkFont(size=12), text_color=MUTED,
        )
        self._status.pack(side="right", padx=20)

        # Body
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=12, pady=12)
        body.columnconfigure(0, weight=0)
        body.columnconfigure(1, weight=3)
        body.columnconfigure(2, weight=2)
        body.rowconfigure(0, weight=1)

        # Left sidebar
        self._settings_panel = SettingsPanel(
            body, settings=self._settings, on_change=lambda: None,
        )
        self._settings_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        # Centre
        centre = ctk.CTkFrame(body, fg_color="transparent")
        centre.grid(row=0, column=1, sticky="nsew", padx=(0, 8))
        centre.rowconfigure(1, weight=1)
        centre.columnconfigure(0, weight=1)

        self._drop = DropZone(centre, on_files_added=self._on_files, height=100)
        self._drop.grid(row=0, column=0, sticky="ew", pady=(0, 8))

        self._preview = ImagePreviewPanel(centre)
        self._preview.grid(row=1, column=0, sticky="nsew", pady=(0, 8))

        # Action bar
        bar = ctk.CTkFrame(centre, fg_color="transparent")
        bar.grid(row=2, column=0, sticky="ew")

        ctk.CTkButton(
            bar, text="▶  Process All",
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=ACCENT, hover_color="#6458D8", height=40,
            command=self._start,
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            bar, text="✕  Clear",
            fg_color=SURFACE2, hover_color=SURFACE, height=40,
            command=self._clear,
        ).pack(side="left")

        self._queue_label = ctk.CTkLabel(
            bar, text="0 images", font=ctk.CTkFont(size=12), text_color=MUTED,
        )
        self._queue_label.pack(side="right")

        self._progress = ProgressSection(centre, on_cancel=self._cancel)
        self._progress.grid(row=3, column=0, sticky="ew", pady=(8, 0))

        # Right log
        right = ctk.CTkFrame(body, fg_color="transparent")
        right.grid(row=0, column=2, sticky="nsew")
        right.rowconfigure(1, weight=1)
        right.columnconfigure(0, weight=1)
        ctk.CTkLabel(
            right, text="Log", font=ctk.CTkFont(size=12, weight="bold"), text_color=MUTED,
        ).grid(row=0, column=0, sticky="w", pady=(0, 4))
        self._log = LogPanel(right)
        self._log.grid(row=1, column=0, sticky="nsew")

    def _on_files(self, paths: list[Path]):
        added = 0
        for p in collect_images(paths):
            if p not in self._queue:
                self._queue.append(p)
                self._preview.add_image(p)
                added += 1
        self._queue_label.configure(text=f"{len(self._queue)} image(s)")
        if added:
            self._log.append(f"Added {added} image(s).")

    def _clear(self):
        if self._batch_thread and self._batch_thread.is_alive():
            self._log.append("Cannot clear while processing.")
            return
        self._queue.clear()
        self._preview.clear()
        self._progress.reset()
        self._queue_label.configure(text="0 images")
        self._status.configure(text="Ready")

    def _start(self):
        if not self._queue:
            self._log.append("No images in queue.")
            return
        if self._batch_thread and self._batch_thread.is_alive():
            self._log.append("Already processing.")
            return
        self._done_count = 0
        self._progress.start()
        self._status.configure(text=f"Processing 0 / {len(self._queue)}")
        self._processor = BatchProcessor(
            images=list(self._queue),
            settings=self._settings,
            on_image_done=self._on_done,
            on_batch_done=self._on_batch_done,
            on_log=self._log.append,
        )
        self._batch_thread = threading.Thread(target=self._processor.start, daemon=True)
        self._batch_thread.start()

    def _cancel(self):
        if self._processor:
            self._processor.cancel()
            self._log.append("Cancelling…")

    def _on_done(self, result: ImageResult):
        self._done_count += 1
        frac = self._done_count / max(1, len(self._queue))
        def _update():
            self._preview.set_status(result.path, "✓" if result.success else "✗")
            self._progress.update(frac)
            self._status.configure(text=f"Processing {self._done_count} / {len(self._queue)}")
        self.after(0, _update)

    def _on_batch_done(self, results: list[ImageResult]):
        ok = sum(1 for r in results if r.success)
        fail = len(results) - ok
        def _update():
            self._progress.finish()
            msg = f"Done — {ok} succeeded" + (f", {fail} failed" if fail else "")
            self._status.configure(text=msg)
            self._log.append(f"\n{'='*40}\n{msg}")
            self._log.append(f"Output → {self._settings.get('output_folder')}")
        self.after(0, _update)

    def _on_close(self):
        self._settings.update({
            "window_width": self.winfo_width(),
            "window_height": self.winfo_height(),
        })
        if self._processor:
            self._processor.cancel()
        self.destroy()


if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    settings = Settings()
    App(settings).mainloop()
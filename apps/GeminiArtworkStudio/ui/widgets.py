"""
widgets.py — Reusable UI components: DropZone, ImagePreviewPanel, LogPanel, ProgressSection.
"""

from __future__ import annotations

import time
from pathlib import Path
from tkinter import filedialog
from typing import Callable, Optional

import customtkinter as ctk
from PIL import Image

ACCENT  = "#7C6CFA"
SURFACE = "#1E1E2E"
SURFACE2= "#27273A"
TEXT    = "#CDD6F4"
MUTED   = "#6C7086"
SUCCESS = "#A6E3A1"
ERROR   = "#F38BA8"
WARNING = "#FAB387"


class DropZone(ctk.CTkFrame):
    def __init__(self, parent, on_files_added: Callable[[list[Path]], None], **kwargs):
        super().__init__(parent, fg_color=SURFACE2, corner_radius=12,
                         border_width=2, border_color=ACCENT, **kwargs)
        self._callback = on_files_added
        self._build()

    def _build(self):
        self.label = ctk.CTkLabel(
            self,
            text="⬇  Drop images or folders here\nor click to browse",
            font=ctk.CTkFont(size=15),
            text_color=MUTED,
        )
        self.label.pack(expand=True, fill="both", padx=20, pady=30)
        self.label.bind("<Button-1>", self._browse)
        self.bind("<Button-1>", self._browse)

        try:
            self.drop_target_register("DND_Files")
            self.dnd_bind("<<Drop>>", self._on_drop)
        except AttributeError:
            pass

    def _browse(self, _event=None):
        paths = filedialog.askopenfilenames(
            title="Select images",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.webp *.tif *.tiff"),
                       ("All files", "*.*")],
        )
        if paths:
            self._callback([Path(p) for p in paths])

    def _on_drop(self, event):
        paths = []
        for token in _parse_dnd(event.data):
            p = Path(token)
            if p.exists():
                paths.append(p)
        if paths:
            self._callback(paths)


class ImagePreviewPanel(ctk.CTkScrollableFrame):
    THUMB = (120, 120)

    def __init__(self, parent, **kwargs):
        super().__init__(parent, fg_color=SURFACE, **kwargs)
        self._items: dict[Path, ctk.CTkLabel] = {}
        self._tk_images: list = []

    def add_image(self, path: Path):
        if path in self._items:
            return
        try:
            pil = Image.open(path)
            pil.thumbnail(self.THUMB, Image.LANCZOS)
            tk_img = ctk.CTkImage(pil, size=pil.size)
            self._tk_images.append(tk_img)
        except Exception:
            tk_img = None

        frame = ctk.CTkFrame(self, fg_color=SURFACE2, corner_radius=8)
        col = len(self._items) % 4
        row = len(self._items) // 4
        frame.grid(row=row, column=col, padx=6, pady=6, sticky="nsew")

        if tk_img:
            ctk.CTkLabel(frame, image=tk_img, text="").pack(padx=4, pady=(4, 0))

        name = path.name[:18] + ("…" if len(path.name) > 18 else "")
        lbl = ctk.CTkLabel(frame, text=name, font=ctk.CTkFont(size=10), text_color=MUTED)
        lbl.pack(padx=4, pady=(2, 4))
        self._items[path] = lbl

    def set_status(self, path: Path, status: str):
        if path in self._items:
            colors = {"✓": SUCCESS, "✗": ERROR, "↻": WARNING}
            lbl = self._items[path]
            lbl.configure(
                text=f"{status} {path.name[:14]}",
                text_color=colors.get(status, TEXT),
            )

    def clear(self):
        for w in self.winfo_children():
            w.destroy()
        self._items.clear()


class LogPanel(ctk.CTkFrame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, fg_color=SURFACE, **kwargs)
        self.textbox = ctk.CTkTextbox(
            self, fg_color=SURFACE, text_color=TEXT,
            font=ctk.CTkFont(family="Courier New", size=11),
            wrap="word", state="disabled",
        )
        self.textbox.pack(fill="both", expand=True, padx=4, pady=4)

    def append(self, line: str):
        self.textbox.after(0, self._insert, line)

    def _insert(self, line: str):
        self.textbox.configure(state="normal")
        self.textbox.insert("end", line + "\n")
        self.textbox.configure(state="disabled")
        self.textbox.see("end")

    def clear(self):
        self.textbox.configure(state="normal")
        self.textbox.delete("1.0", "end")
        self.textbox.configure(state="disabled")


class ProgressSection(ctk.CTkFrame):
    def __init__(self, parent, on_cancel: Callable, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self._on_cancel = on_cancel
        self._start_time: Optional[float] = None
        self._build()

    def _build(self):
        self.progress_bar = ctk.CTkProgressBar(self, height=12, progress_color=ACCENT)
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x", side="left", expand=True, padx=(0, 12))

        self.eta_label = ctk.CTkLabel(
            self, text="", font=ctk.CTkFont(size=11), text_color=MUTED, width=90
        )
        self.eta_label.pack(side="left")

        self.cancel_btn = ctk.CTkButton(
            self, text="Cancel", width=80,
            fg_color=ERROR, hover_color="#C0455A", command=self._on_cancel,
        )
        self.cancel_btn.pack(side="left", padx=(8, 0))

    def start(self):
        self._start_time = time.perf_counter()
        self.progress_bar.set(0)
        self.eta_label.configure(text="ETA: —")
        self.cancel_btn.configure(state="normal")

    def update(self, fraction: float):
        self.progress_bar.set(max(0.0, min(1.0, fraction)))
        if self._start_time and fraction > 0.01:
            elapsed = time.perf_counter() - self._start_time
            remaining = (elapsed / fraction) - elapsed
            self.eta_label.configure(text=f"ETA: {_fmt(remaining)}")

    def finish(self):
        self.progress_bar.set(1.0)
        self.eta_label.configure(text="Done ✓")
        self.cancel_btn.configure(state="disabled")

    def reset(self):
        self.progress_bar.set(0)
        self.eta_label.configure(text="")
        self.cancel_btn.configure(state="normal")


def _fmt(s: float) -> str:
    if s < 0: return "—"
    if s < 60: return f"{int(s)}s"
    return f"{int(s//60)}m {int(s%60)}s"


def _parse_dnd(raw: str) -> list[str]:
    paths, token, in_brace = [], "", False
    for ch in raw:
        if ch == "{": in_brace = True
        elif ch == "}":
            in_brace = False
            if token: paths.append(token); token = ""
        elif ch == " " and not in_brace:
            if token: paths.append(token); token = ""
        else:
            token += ch
    if token: paths.append(token)
    return paths
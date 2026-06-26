"""
settings_panel.py — Left sidebar settings controls.
"""

from __future__ import annotations

import os
from pathlib import Path
from tkinter import filedialog
from typing import Callable

import customtkinter as ctk

from engine.export.exporter import EXPORT_PROFILES
from utils.settings import Settings

ACCENT  = "#7C6CFA"
SURFACE = "#1E1E2E"
SURFACE2= "#27273A"
TEXT    = "#CDD6F4"
MUTED   = "#6C7086"


class SettingsPanel(ctk.CTkScrollableFrame):
    def __init__(self, parent, settings: Settings, on_change: Callable, **kwargs):
        super().__init__(parent, fg_color=SURFACE2, width=260, **kwargs)
        self._settings = settings
        self._on_change = on_change
        self._profile_vars: dict[str, ctk.BooleanVar] = {}
        self._build()

    def _section(self, title: str):
        ctk.CTkLabel(
            self, text=title.upper(),
            font=ctk.CTkFont(size=10, weight="bold"), text_color=ACCENT,
        ).pack(anchor="w", padx=16, pady=(16, 2))

    def _dropdown(self, options: list[str], key: str, cast=str):
        var = ctk.StringVar(value=str(self._settings.get(key, options[0])))
        def _cb(val):
            self._settings.set(key, cast(val))
            self._on_change()
        ctk.CTkOptionMenu(
            self, values=options, variable=var, command=_cb,
            fg_color=SURFACE, button_color=ACCENT, text_color=TEXT,
        ).pack(fill="x", padx=12, pady=2)

    def _build(self):
        # Output folder
        self._section("Output Folder")
        folder = str(self._settings.get("output_folder", ""))
        self._folder_label = ctk.CTkLabel(
            self, text=folder[-32:] if len(folder) > 32 else folder,
            font=ctk.CTkFont(size=10), text_color=MUTED, wraplength=200,
        )
        self._folder_label.pack(fill="x", padx=12)
        ctk.CTkButton(
            self, text="Browse…", height=28,
            fg_color=SURFACE, border_width=1, border_color=ACCENT, text_color=TEXT,
            command=self._browse,
        ).pack(fill="x", padx=12, pady=(4, 0))

        # Upscale target
        self._section("Upscale Target")
        self._dropdown(["4096", "8192", "16384"], "upscale_target")

        # Tile size
        self._section("Tile Size")
        self._dropdown(["256", "512", "1024", "2048"], "tile_size", cast=int)

        # Crop mode
        self._section("Crop Mode")
        self._dropdown(["center", "smart", "letterbox", "blurred"], "crop_mode")

        # Export profiles
        self._section("Export Profiles")
        enabled = set(self._settings.get("preferred_exports", ["Master"]))
        for name in EXPORT_PROFILES:
            var = ctk.BooleanVar(value=name in enabled)
            self._profile_vars[name] = var
            def _toggle(n=name, v=var):
                active = [k for k, bv in self._profile_vars.items() if bv.get()]
                self._settings.set("preferred_exports", active)
                self._on_change()
            ctk.CTkCheckBox(
                self, text=name, variable=var, command=_toggle,
                checkmark_color=ACCENT, fg_color=SURFACE, hover_color=SURFACE2,
            ).pack(anchor="w", padx=16, pady=2)

        # CPU threads
        self._section("CPU Threads")
        max_t = os.cpu_count() or 8
        current = int(self._settings.get("cpu_threads", max(1, max_t - 1)))
        self._threads_label = ctk.CTkLabel(
            self, text=f"Threads: {current}", font=ctk.CTkFont(size=11), text_color=TEXT,
        )
        self._threads_label.pack(anchor="w", padx=16)
        slider = ctk.CTkSlider(
            self, from_=1, to=max_t, number_of_steps=max_t - 1,
            progress_color=ACCENT, command=self._on_slide,
        )
        slider.set(current)
        slider.pack(fill="x", padx=12, pady=(2, 8))

    def _browse(self):
        folder = filedialog.askdirectory(title="Select output folder")
        if folder:
            self._settings.set("output_folder", folder)
            self._folder_label.configure(text=folder[-32:] if len(folder) > 32 else folder)
            self._on_change()

    def _on_slide(self, val: float):
        t = int(round(val))
        self._settings.set("cpu_threads", t)
        self._threads_label.configure(text=f"Threads: {t}")
        self._on_change()
"""
settings.py — Persistent application settings management.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

DEFAULT_SETTINGS: dict[str, Any] = {
    "output_folder": str(Path.home() / "GeminiArtworkStudio" / "output"),
    "tile_size": 512,
    "preferred_model": "realesrgan-x4plus",
    "preferred_exports": ["Master", "Poster"],
    "theme": "dark",
    "cpu_threads": max(1, (os.cpu_count() or 4) - 1),
    "upscale_target": "8192",
    "crop_mode": "center",
    "jpeg_quality": 95,
    "window_width": 1280,
    "window_height": 800,
}

SETTINGS_PATH = Path(__file__).parent.parent / "settings.json"


class Settings:
    def __init__(self, path: Path = SETTINGS_PATH) -> None:
        self._path = path
        self._data: dict[str, Any] = {}
        self.load()

    def load(self) -> None:
        if self._path.exists():
            try:
                with self._path.open("r", encoding="utf-8") as f:
                    loaded = json.load(f)
                self._data = {**DEFAULT_SETTINGS, **loaded}
                return
            except (json.JSONDecodeError, OSError):
                pass
        self._data = dict(DEFAULT_SETTINGS)
        self.save()

    def save(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with self._path.open("w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2)
        except OSError as exc:
            print(f"[Settings] Could not save settings: {exc}")

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value
        self.save()

    def update(self, pairs: dict[str, Any]) -> None:
        self._data.update(pairs)
        self.save()

    def __getitem__(self, key: str) -> Any:
        return self._data[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.set(key, value)

    def all(self) -> dict[str, Any]:
        return dict(self._data)
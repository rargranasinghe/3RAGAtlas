"""
image_utils.py — Image loading, saving, and file discovery.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image, UnidentifiedImageError

log = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS: frozenset[str] = frozenset(
    {".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff"}
)


def load_image(path: Path) -> tuple[np.ndarray, Optional[bytes]]:
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported format: {suffix}")
    try:
        pil_img = Image.open(path)
        pil_img.verify()
        pil_img = Image.open(path)
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError(f"Cannot open image: {exc}") from exc

    exif_bytes: Optional[bytes] = None
    try:
        exif_bytes = pil_img.info.get("exif")
    except Exception:
        pass

    if pil_img.mode != "RGB":
        pil_img = pil_img.convert("RGB")

    return np.array(pil_img, dtype=np.uint8), exif_bytes


def save_image(
    array: np.ndarray,
    path: Path,
    quality: int = 95,
    exif_bytes: Optional[bytes] = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pil_img = Image.fromarray(array)
    suffix = path.suffix.lower()
    save_kwargs: dict = {}
    if suffix in {".jpg", ".jpeg"}:
        save_kwargs["quality"] = quality
        save_kwargs["subsampling"] = 0
        if exif_bytes:
            save_kwargs["exif"] = exif_bytes
    elif suffix == ".webp":
        save_kwargs["quality"] = quality
        if exif_bytes:
            save_kwargs["exif"] = exif_bytes
    elif suffix in {".tif", ".tiff"}:
        save_kwargs["compression"] = "lzw"
    pil_img.save(path, **save_kwargs)


def collect_images(paths: list[Path]) -> list[Path]:
    result: list[Path] = []
    for p in paths:
        if p.is_dir():
            for f in sorted(p.iterdir()):
                if f.suffix.lower() in SUPPORTED_EXTENSIONS:
                    result.append(f)
        elif p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS:
            result.append(p)
    return result


def is_supported(path: Path) -> bool:
    return path.suffix.lower() in SUPPORTED_EXTENSIONS


def image_dimensions(path: Path) -> tuple[int, int]:
    with Image.open(path) as img:
        return img.size
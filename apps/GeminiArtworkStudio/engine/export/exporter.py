"""
exporter.py — Redbubble export profiles and image cropping.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import cv2
import numpy as np
from PIL import Image

log = logging.getLogger(__name__)

CropMode = Literal["center", "smart", "letterbox", "transparent", "blurred"]


@dataclass(frozen=True)
class ExportProfile:
    name: str
    width: int
    height: int
    folder: str


EXPORT_PROFILES: dict[str, ExportProfile] = {
    "Master":   ExportProfile("Master",   16384, 16384, "Master"),
    "Poster":   ExportProfile("Poster",    8310, 11790, "Poster"),
    "Puzzle":   ExportProfile("Puzzle",    9075,  6201, "Puzzle"),
    "DeskMat":  ExportProfile("DeskMat",   8268,  4331, "DeskMat"),
    "Blanket":  ExportProfile("Blanket",   7632,  6480, "Blanket"),
    "Tapestry": ExportProfile("Tapestry",  7632,  6480, "Tapestry"),
    "Pillow":   ExportProfile("Pillow",    3225,  3225, "Pillow"),
}


def _center_crop(img: np.ndarray, tw: int, th: int) -> np.ndarray:
    h, w = img.shape[:2]
    x0 = max(0, (w - tw) // 2)
    y0 = max(0, (h - th) // 2)
    return img[y0:y0 + th, x0:x0 + tw]


def _smart_crop(img: np.ndarray, tw: int, th: int) -> np.ndarray:
    h, w = img.shape[:2]
    x0 = max(0, (w - tw) // 2)
    slack_y = max(0, h - th)
    y0 = int(slack_y * 0.2)
    return img[y0:y0 + th, x0:x0 + tw]


def _fit_with_padding(img: np.ndarray, tw: int, th: int, mode: CropMode) -> np.ndarray:
    h, w = img.shape[:2]
    scale = min(tw / w, th / h)
    new_w = int(round(w * scale))
    new_h = int(round(h * scale))
    resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)

    if mode == "transparent":
        canvas = np.zeros((th, tw, 4), dtype=np.uint8)
        resized_rgba = cv2.cvtColor(resized, cv2.COLOR_RGB2RGBA)
        ox, oy = (tw - new_w) // 2, (th - new_h) // 2
        canvas[oy:oy + new_h, ox:ox + new_w] = resized_rgba
        return canvas

    elif mode == "blurred":
        bg = cv2.resize(img, (tw, th), interpolation=cv2.INTER_LANCZOS4)
        bg = cv2.GaussianBlur(bg, (0, 0), sigmaX=40)
        bg = cv2.addWeighted(bg, 0.6, np.zeros_like(bg), 0.0, 0)
        ox, oy = (tw - new_w) // 2, (th - new_h) // 2
        bg[oy:oy + new_h, ox:ox + new_w] = resized
        return bg

    else:  # letterbox
        canvas = np.zeros((th, tw, 3), dtype=np.uint8)
        ox, oy = (tw - new_w) // 2, (th - new_h) // 2
        canvas[oy:oy + new_h, ox:ox + new_w] = resized
        return canvas


def fit_to_profile(
    img: np.ndarray,
    profile: ExportProfile,
    crop_mode: CropMode = "center",
) -> np.ndarray:
    h, w = img.shape[:2]
    tw, th = profile.width, profile.height

    if w == tw and h == th:
        return img

    if crop_mode in ("letterbox", "transparent", "blurred"):
        return _fit_with_padding(img, tw, th, crop_mode)

    img_aspect = w / h
    target_aspect = tw / th

    if img_aspect > target_aspect:
        scale = th / h
        new_w, new_h = int(round(w * scale)), th
    else:
        scale = tw / w
        new_w, new_h = tw, int(round(h * scale))

    scaled = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)

    if crop_mode == "smart":
        return _smart_crop(scaled, tw, th)
    return _center_crop(scaled, tw, th)


def export_image(
    img: np.ndarray,
    stem: str,
    output_root: Path,
    profiles: list[str],
    crop_mode: CropMode = "center",
    jpeg_quality: int = 95,
) -> list[Path]:
    saved: list[Path] = []
    for profile_name in profiles:
        if profile_name not in EXPORT_PROFILES:
            log.warning("Unknown profile %r — skipping.", profile_name)
            continue
        profile = EXPORT_PROFILES[profile_name]
        fitted = fit_to_profile(img, profile, crop_mode)
        out_dir = output_root / profile.folder
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{stem}_{profile_name}.png"
        Image.fromarray(fitted).save(out_path)
        log.info("Exported %s", out_path.name)
        saved.append(out_path)
    return saved
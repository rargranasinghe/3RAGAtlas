"""
upscaler.py — Adaptive tiled AI upscaling via Real-ESRGAN ONNX (CPU).
Compatible with Python 3.12, 3.13, 3.14. No PyTorch or basicsr needed.
"""

from __future__ import annotations

import logging
import threading
import urllib.request
from pathlib import Path
from typing import Callable, Optional

import cv2
import numpy as np

log = logging.getLogger(__name__)

OVERLAP = 8

ONNX_MODELS: dict[str, dict] = {
    "realesrgan-x4plus": {
        "filename": "realesrgan_x4plus.onnx",
        "scale": 4,
        "urls": [
            "https://huggingface.co/tidus2102/Real-ESRGAN/resolve/main/Real-ESRGAN_x4plus.onnx",
            "https://huggingface.co/imgdesignart/realesrgan-x4-onnx/resolve/main/onnx/model.onnx",
        ],
    },
    "realesrgan-x2plus": {
        "filename": "realesrgan_x2plus.onnx",
        "scale": 2,
        "urls": [
            "https://huggingface.co/tidus2102/Real-ESRGAN/resolve/main/Real-ESRGAN_x2plus.onnx",
        ],
    },
}


def build_upscale_plan(
    source_long_edge: int,
    target_long_edge: int,
    available_models: list[str],
) -> list[tuple[str, int]]:
    if target_long_edge <= source_long_edge:
        return []
    ratio = target_long_edge / source_long_edge
    plan: list[tuple[str, int]] = []
    while ratio > 1.05:
        if ratio >= 3.5 and "realesrgan-x4plus" in available_models:
            plan.append(("realesrgan-x4plus", 4))
            ratio /= 4
        else:
            plan.append(("realesrgan-x2plus", 2))
            ratio /= 2
    return plan


def _cosine_window(size: int) -> np.ndarray:
    t = np.linspace(0, 2 * np.pi, size, endpoint=False)
    return (0.5 - 0.5 * np.cos(t)).astype(np.float32)


def _bicubic_upscale(img: np.ndarray, scale: int) -> np.ndarray:
    h, w = img.shape[:2]
    return cv2.resize(img, (w * scale, h * scale), interpolation=cv2.INTER_CUBIC)


def _onnx_upscale_tile(session, tile: np.ndarray) -> np.ndarray:
    rgb = cv2.cvtColor(tile, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    nchw = np.transpose(rgb, (2, 0, 1))[np.newaxis]
    input_name = session.get_inputs()[0].name
    outputs = session.run(None, {input_name: nchw})
    out = outputs[0][0]
    out = np.clip(out, 0.0, 1.0)
    out = np.transpose(out, (1, 2, 0))
    out = (out * 255.0).round().astype(np.uint8)
    return cv2.cvtColor(out, cv2.COLOR_RGB2BGR)


def _tiled_onnx_upscale(
    img_bgr: np.ndarray,
    session,
    scale: int,
    tile_size: int,
    progress_cb: Optional[Callable[[float], None]],
    cancel_event: threading.Event,
) -> np.ndarray:
    h, w = img_bgr.shape[:2]
    out_h, out_w = h * scale, w * scale
    output = np.zeros((out_h, out_w, 3), dtype=np.float32)
    weight = np.zeros((out_h, out_w, 1), dtype=np.float32)

    xs = list(range(0, w, tile_size - OVERLAP * 2))
    ys = list(range(0, h, tile_size - OVERLAP * 2))
    total = len(xs) * len(ys)
    done = 0

    for y in ys:
        for x in xs:
            if cancel_event.is_set():
                raise InterruptedError("Cancelled.")

            x1 = max(0, x - OVERLAP)
            y1 = max(0, y - OVERLAP)
            x2 = min(w, x + tile_size + OVERLAP)
            y2 = min(h, y + tile_size + OVERLAP)
            tile = img_bgr[y1:y2, x1:x2]

            up_tile = _onnx_upscale_tile(session, tile)

            ox1, oy1 = x1 * scale, y1 * scale
            ox2, oy2 = x2 * scale, y2 * scale
            tw, th = up_tile.shape[1], up_tile.shape[0]
            wx = _cosine_window(tw)
            wy = _cosine_window(th)
            blend = (wy[:, np.newaxis] * wx[np.newaxis, :])[:, :, np.newaxis]

            output[oy1:oy2, ox1:ox2] += up_tile.astype(np.float32) * blend
            weight[oy1:oy2, ox1:ox2] += blend

            done += 1
            if progress_cb:
                progress_cb(done / total)

    weight = np.maximum(weight, 1e-6)
    return np.clip(output / weight, 0, 255).astype(np.uint8)


def _load_session(model_name: str, model_dir: Path):
    try:
        import onnxruntime as ort
    except ImportError:
        log.warning("onnxruntime not installed — using bicubic fallback.")
        return None

    info = ONNX_MODELS.get(model_name)
    if not info:
        return None

    model_path = model_dir / info["filename"]

    if not model_path.exists():
        model_dir.mkdir(parents=True, exist_ok=True)
        downloaded = False
        for url in info.get("urls", []):
            tmp = model_path.with_suffix(".tmp")
            try:
                log.info("Downloading %s from %s", info["filename"], url)
                urllib.request.urlretrieve(url, tmp)
                tmp.rename(model_path)
                downloaded = True
                break
            except Exception as exc:
                log.warning("Download failed (%s): %s", url, exc)
                if tmp.exists():
                    tmp.unlink()
        if not downloaded:
            log.error("All downloads failed for %s — using bicubic.", info["filename"])
            return None

    try:
        session = ort.InferenceSession(
            str(model_path), providers=["CPUExecutionProvider"]
        )
        log.info("Loaded ONNX model: %s", model_path.name)
        return session
    except Exception as exc:
        log.error("Could not load ONNX model: %s", exc)
        return None


def _trim_to_target(img: np.ndarray, target: int) -> np.ndarray:
    h, w = img.shape[:2]

    def _crop(size: int) -> tuple[int, int]:
        excess = size - target
        if 0 < excess <= 32:
            lo = excess // 2
            return lo, size - (excess - lo)
        return 0, size

    y0, y1 = _crop(h)
    x0, x1 = _crop(w)
    return img[y0:y1, x0:x1]


class TiledUpscaler:
    """Adaptive multi-pass tiled upscaler — ONNX on CPU, bicubic fallback."""

    def __init__(
        self,
        model_dir: Path,
        tile_size: int = 512,
        cancel_event: Optional[threading.Event] = None,
    ) -> None:
        self.model_dir = model_dir
        self.tile_size = tile_size
        self.cancel_event = cancel_event or threading.Event()
        self._available_models = list(ONNX_MODELS.keys())
        self._session_cache: dict[str, object] = {}

    def _get_session(self, model_name: str):
        if model_name not in self._session_cache:
            self._session_cache[model_name] = _load_session(model_name, self.model_dir)
        return self._session_cache[model_name]

    def upscale(
        self,
        img_rgb: np.ndarray,
        target_long_edge: int,
        progress_cb: Optional[Callable[[float], None]] = None,
    ) -> np.ndarray:
        h, w = img_rgb.shape[:2]
        plan = build_upscale_plan(max(h, w), target_long_edge, self._available_models)

        if not plan:
            return img_rgb

        log.info("Plan: %s", " → ".join(f"x{s}" for _, s in plan))
        current = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)

        for step_idx, (model_name, scale) in enumerate(plan):
            if self.cancel_event.is_set():
                raise InterruptedError("Cancelled.")

            session = self._get_session(model_name)

            def _cb(frac: float, _i: int = step_idx, _n: int = len(plan)) -> None:
                if progress_cb:
                    progress_cb((_i + frac) / _n)

            if session is not None:
                current = _tiled_onnx_upscale(
                    current, session, scale, self.tile_size, _cb, self.cancel_event
                )
            else:
                current = _bicubic_upscale(current, scale)
                if progress_cb:
                    progress_cb((step_idx + 1) / len(plan))

        current = _trim_to_target(current, target_long_edge)
        return cv2.cvtColor(current, cv2.COLOR_BGR2RGB)
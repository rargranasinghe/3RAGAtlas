"""
pipeline.py — Single-image pipeline and batch processor.
"""

from __future__ import annotations

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, Future
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from utils.image_utils import load_image
from utils.settings import Settings
from engine.upscaler.upscaler import TiledUpscaler
from engine.export.exporter import export_image

log = logging.getLogger(__name__)


@dataclass
class ImageResult:
    path: Path
    success: bool
    error: str = ""
    elapsed_seconds: float = 0.0
    original_size: tuple[int, int] = (0, 0)
    final_size: tuple[int, int] = (0, 0)
    exports: list[Path] = field(default_factory=list)


def process_image(
    image_path: Path,
    settings: Settings,
    cancel_event: threading.Event,
    progress_cb: Optional[Callable[[float], None]] = None,
    log_cb: Optional[Callable[[str], None]] = None,
) -> ImageResult:
    def _log(msg: str) -> None:
        log.info(msg)
        if log_cb:
            log_cb(msg)

    t0 = time.perf_counter()
    result = ImageResult(path=image_path, success=False)

    try:
        _log(f"Loading: {image_path.name}")
        img_rgb, exif_bytes = load_image(image_path)
        h, w = img_rgb.shape[:2]
        result.original_size = (w, h)
        _log(f"  Source: {w}×{h}")

        if cancel_event.is_set():
            raise InterruptedError("Cancelled.")
        if progress_cb:
            progress_cb(0.05)

        target_px = int(settings.get("upscale_target", "8192"))
        model_dir = Path(__file__).parent.parent / "models"
        tile_size = int(settings.get("tile_size", 512))

        upscaler = TiledUpscaler(
            model_dir=model_dir,
            tile_size=tile_size,
            cancel_event=cancel_event,
        )

        def _up_progress(frac: float) -> None:
            if progress_cb:
                progress_cb(0.05 + frac * 0.75)

        _log(f"  Upscaling to {target_px}px …")
        upscaled = upscaler.upscale(img_rgb, target_long_edge=target_px, progress_cb=_up_progress)
        uh, uw = upscaled.shape[:2]
        result.final_size = (uw, uh)
        _log(f"  Upscaled: {uw}×{uh}")

        if cancel_event.is_set():
            raise InterruptedError("Cancelled.")
        if progress_cb:
            progress_cb(0.82)

        profiles = settings.get("preferred_exports", ["Master"])
        output_root = Path(settings.get("output_folder", "output"))
        crop_mode = settings.get("crop_mode", "center")
        stem = image_path.stem

        _log(f"  Exporting {len(profiles)} profile(s)…")
        exports = export_image(
            img=upscaled,
            stem=stem,
            output_root=output_root,
            profiles=profiles,
            crop_mode=crop_mode,
        )
        result.exports = exports

        if progress_cb:
            progress_cb(1.0)

        elapsed = time.perf_counter() - t0
        result.elapsed_seconds = elapsed
        result.success = True
        _log(f"✓ Done in {elapsed:.1f}s — {len(exports)} file(s) written.")

    except InterruptedError:
        result.error = "Cancelled."
        _log(f"✗ {image_path.name}: cancelled.")
    except MemoryError:
        result.error = "Out of memory — reduce tile size."
        _log(f"✗ {image_path.name}: out of memory.")
    except Exception as exc:
        result.error = str(exc)
        _log(f"✗ {image_path.name}: {exc}")
        log.exception("Error processing %s", image_path)

    return result


class BatchProcessor:
    def __init__(
        self,
        images: list[Path],
        settings: Settings,
        on_image_done: Optional[Callable[[ImageResult], None]] = None,
        on_batch_done: Optional[Callable[[list[ImageResult]], None]] = None,
        on_log: Optional[Callable[[str], None]] = None,
    ) -> None:
        self.images = images
        self.settings = settings
        self.on_image_done = on_image_done
        self.on_batch_done = on_batch_done
        self.on_log = on_log
        self.results: list[ImageResult] = []
        self.cancel_event = threading.Event()
        self._lock = threading.Lock()

    def start(self) -> None:
        log.info("Batch: %d images", len(self.images))
        for path in self.images:
            if self.cancel_event.is_set():
                break
            result = process_image(
                path, self.settings, self.cancel_event, None, self.on_log
            )
            with self._lock:
                self.results.append(result)
            if self.on_image_done:
                self.on_image_done(result)

        if self.on_batch_done:
            self.on_batch_done(list(self.results))

    def cancel(self) -> None:
        self.cancel_event.set()
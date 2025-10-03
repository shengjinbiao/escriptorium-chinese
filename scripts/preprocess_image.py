from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageOps


@dataclass
class Panel:
    left: int
    top: int
    right: int
    bottom: int

    def bounds(self) -> tuple[int, int, int, int]:
        return self.left, self.top, self.right, self.bottom


def detect_dark_panels(
    image: Image.Image,
    *,
    threshold: int,
    downscale: int,
    min_area: int,
    min_width_px: int,
    min_height_px: int,
    rectangularity: float,
    central_band_height: int,
    central_light_ratio: float,
    bright_threshold: int,
) -> Iterable[Panel]:
    """Yield rectangular dark panels that likely contain light text."""
    width, height = image.size
    downscale = max(1, downscale)
    reduced = image.resize((max(1, width // downscale), max(1, height // downscale)), Image.BILINEAR)
    reduced_arr = np.asarray(reduced, dtype=np.uint8)
    dark_mask = reduced_arr < threshold

    visited = np.zeros_like(dark_mask, dtype=bool)
    panels: list[Panel] = []
    h, w = dark_mask.shape

    def neighbors(y: int, x: int):
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w:
                yield ny, nx

    for y in range(h):
        for x in range(w):
            if not dark_mask[y, x] or visited[y, x]:
                continue

            queue = deque([(y, x)])
            visited[y, x] = True
            pixels: list[tuple[int, int]] = []

            min_y = max_y = y
            min_x = max_x = x

            while queue:
                cy, cx = queue.popleft()
                pixels.append((cy, cx))
                if cy < min_y:
                    min_y = cy
                elif cy > max_y:
                    max_y = cy
                if cx < min_x:
                    min_x = cx
                elif cx > max_x:
                    max_x = cx

                for ny, nx in neighbors(cy, cx):
                    if not visited[ny, nx] and dark_mask[ny, nx]:
                        visited[ny, nx] = True
                        queue.append((ny, nx))

            area = len(pixels)
            if area < min_area:
                continue

            bbox_area = (max_y - min_y + 1) * (max_x - min_x + 1)
            fill_ratio = area / bbox_area if bbox_area else 0
            if fill_ratio < rectangularity:
                continue

            left = max(0, min_x * downscale)
            top = max(0, min_y * downscale)
            right = min(width, (max_x + 1) * downscale)
            bottom = min(height, (max_y + 1) * downscale)

            width_px = right - left
            height_px = bottom - top

            if width_px <= 0 or height_px <= 0:
                continue

            if width_px < min_width_px or height_px < min_height_px:
                continue

            band_height = max(1, min(central_band_height, bottom - top))
            band_top = top + (bottom - top - band_height) // 2
            band_bottom = band_top + band_height

            region = image.crop((left, top, right, bottom))
            band = image.crop((left, band_top, right, band_bottom))
            band_arr = np.asarray(band, dtype=np.uint8)

            bright_pixels = np.count_nonzero(band_arr >= bright_threshold)
            total_pixels = band_arr.size
            if total_pixels == 0:
                continue

            if (bright_pixels / total_pixels) < central_light_ratio:
                continue

            panels.append(Panel(left, top, right, bottom))

    return panels


def preprocess_black_on_white(
    src: Path,
    *,
    threshold: int = 140,
    downscale: int = 4,
    min_area: int = 200,
    min_width_ratio: float = 0.05,
    min_height_ratio: float = 0.04,
    min_width_px: int = 0,
    min_height_px: int = 0,
    rectangularity: float = 0.35,
    central_band_height: int = 40,
    central_light_ratio: float = 0.01,
    bright_threshold: int = 170,
    panel_binarize_threshold: Optional[int] = 160,
    overlay_path: Optional[Path] = None,
) -> Tuple[Path, Optional[Path]]:
    """Invert dark rectangular panels and binarize them to white background/black text."""
    src = src.expanduser().resolve()
    if not src.exists():
        raise FileNotFoundError(src)

    image = Image.open(src)
    grayscale = ImageOps.grayscale(image)
    enhanced = ImageOps.autocontrast(grayscale, cutoff=1)

    page_width, page_height = enhanced.size
    min_width_limit = max(int(page_width * min_width_ratio), min_width_px)
    min_height_limit = max(int(page_height * min_height_ratio), min_height_px)

    panels = list(
        detect_dark_panels(
        enhanced,
        threshold=threshold,
        downscale=downscale,
        min_area=min_area,
        min_width_px=min_width_limit,
        min_height_px=min_height_limit,
        rectangularity=rectangularity,
        central_band_height=central_band_height,
        central_light_ratio=central_light_ratio,
        bright_threshold=bright_threshold,
        )
    )

    mask = Image.new("L", enhanced.size, 0)
    draw = ImageDraw.Draw(mask)

    for panel in panels:
        draw.rectangle(panel.bounds(), fill=255)

    enh_arr = np.asarray(enhanced, dtype=np.uint8)
    mask_arr = np.asarray(mask, dtype=np.uint8)
    inverted_arr = 255 - enh_arr

    if panel_binarize_threshold is not None:
        thresh = np.uint8(max(0, min(255, panel_binarize_threshold)))
        panel_arr = np.where(inverted_arr > thresh, 255, 0).astype(np.uint8)
    else:
        panel_arr = inverted_arr

    result_arr = np.where(mask_arr > 0, panel_arr, enh_arr).astype(np.uint8)
    combined = Image.fromarray(result_arr, mode="L")

    dest = src.with_name(f"{src.stem}_preprocessed{src.suffix}")
    combined.save(dest)

    overlay_output: Optional[Path] = None
    if overlay_path is not None:
        overlay_output = overlay_path.expanduser().resolve()
    elif panels:
        overlay_output = src.with_name(f"{src.stem}_panels.png")

    if overlay_output is not None:
        overlay_image = image.convert("RGB")
        overlay_draw = ImageDraw.Draw(overlay_image)
        stroke = max(2, downscale)
        for panel in panels:
            overlay_draw.rectangle(panel.bounds(), outline=(255, 0, 0), width=stroke)
        overlay_image.save(overlay_output)

    return dest, overlay_output


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Preprocess pages with black background text blocks.")
    parser.add_argument("image", type=Path, help="Path to the source image file.")
    parser.add_argument("--threshold", type=int, default=140, help="Dark detection threshold (0-255).")
    parser.add_argument("--downscale", type=int, default=4, help="Factor to shrink image for panel detection.")
    parser.add_argument("--min-area", type=int, default=200, help="Minimum dark area (in downscaled pixels) to consider.")
    parser.add_argument("--rectangularity", type=float, default=0.35, help="Required area/bounding-box ratio for panels.")
    parser.add_argument("--min-width-ratio", type=float, default=0.05, help="Minimum panel width as a fraction of page width.")
    parser.add_argument("--min-height-ratio", type=float, default=0.04, help="Minimum panel height as a fraction of page height.")
    parser.add_argument("--min-width", type=int, default=0, help="Minimum panel width in pixels (applied after ratio).")
    parser.add_argument("--min-height", type=int, default=0, help="Minimum panel height in pixels (applied after ratio).")
    parser.add_argument("--central-band-height", type=int, default=40, help="Height of the central band inspected for light strokes.")
    parser.add_argument("--central-light-ratio", type=float, default=0.01, help="Minimum fraction of bright pixels within the central band.")
    parser.add_argument("--bright-threshold", type=int, default=170, help="Brightness threshold for detecting light strokes (0-255).")
    parser.add_argument(
        "--panel-binarize-threshold",
        type=int,
        default=160,
        help="Threshold for binarising inverted panels; set to -1 to skip binarisation.",
    )
    parser.add_argument(
        "--overlay",
        type=Path,
        help="Optional path to save an overlay image showing detected panels.",
    )
    args = parser.parse_args()

    output_path, overlay_path = preprocess_black_on_white(
        args.image,
        threshold=args.threshold,
        downscale=args.downscale,
        min_area=args.min_area,
        min_width_ratio=args.min_width_ratio,
        min_height_ratio=args.min_height_ratio,
        min_width_px=args.min_width,
        min_height_px=args.min_height,
        rectangularity=args.rectangularity,
        central_band_height=args.central_band_height,
        central_light_ratio=args.central_light_ratio,
        bright_threshold=args.bright_threshold,
        panel_binarize_threshold=None if args.panel_binarize_threshold < 0 else args.panel_binarize_threshold,
        overlay_path=args.overlay,
    )
    print(output_path)
    if overlay_path is not None:
        print(overlay_path)

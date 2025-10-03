"""Reading-order heuristics shared between batch scripts and the app."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple, TYPE_CHECKING

import statistics

if TYPE_CHECKING:  # pragma: no cover
    from .models import Line

HORIZONTAL_GROUP_THRESHOLD = 60
DOUBLE_LINE_VPOS_THRESHOLD = 40
VERTICAL_TIE_THRESHOLD = 25
SHORT_LINE_WIDTH_THRESHOLD = 150
WIDTH_STEP_THRESHOLD = 30
MIN_DOUBLE_LINE_X_GAP = 50
MAX_DOUBLE_LINE_X_GAP = 200


@dataclass
class LineMetrics:
    line: "Line"
    x: float
    vpos: float
    width: float
    left_span: float
    right_span: float

    @property
    def ratio(self) -> float:
        left = max(self.left_span, 1.0)
        right = max(self.right_span, 1.0)
        smaller = min(left, right)
        return max(left, right) / smaller if smaller else 1.0


def _normalize_point(point) -> Tuple[float, float]:
    if isinstance(point, dict):
        x = point.get("x") or point.get(0) or 0.0
        y = point.get("y") or point.get(1) or 0.0
        return float(x), float(y)
    if isinstance(point, (list, tuple)) and len(point) >= 2:
        return float(point[0]), float(point[1])
    return float(point or 0.0), 0.0


def _extract_points(line: "Line") -> List[Tuple[float, float]]:
    baseline = line.baseline or []
    if baseline:
        return [_normalize_point(pt) for pt in baseline]
    mask = line.mask or []
    if mask:
        return [_normalize_point(pt) for pt in mask]
    box = getattr(line, "box", None)
    if box:
        min_x, min_y, max_x, max_y = box
        return [(min_x, min_y), (max_x, min_y), (max_x, max_y), (min_x, max_y)]
    return []


def build_metrics(line: "Line") -> Optional[LineMetrics]:
    points = _extract_points(line)
    if not points:
        return None
    xs = [pt[0] for pt in points]
    ys = [pt[1] for pt in points]
    if not xs or not ys:
        return None
    min_x = min(xs)
    max_x = max(xs)
    width = max(max_x - min_x, 1.0)
    x_avg = sum(xs) / len(xs)
    vpos = min(ys)
    left_span = max(x_avg - min_x, 0.0)
    right_span = max(max_x - x_avg, 0.0)
    return LineMetrics(line=line, x=x_avg, vpos=vpos, width=width, left_span=left_span, right_span=right_span)


def group_textlines(items: List[LineMetrics], *, column_desc: bool) -> List[dict]:
    groups: List[dict] = []
    for data in sorted(items, key=lambda m: m.x, reverse=column_desc):
        for group in groups:
            if abs(data.x - group["x_ref"]) <= HORIZONTAL_GROUP_THRESHOLD:
                group["items"].append(data)
                group["x_ref"] = sum(metric.x for metric in group["items"]) / len(group["items"])
                break
        else:
            groups.append({"x_ref": data.x, "items": [data]})
    groups.sort(key=lambda g: g["x_ref"], reverse=column_desc)
    return groups


def maybe_merge_double_columns(groups: List[dict]) -> None:
    changed = True
    while changed:
        changed = False
        idx = 0
        while idx < len(groups) - 1:
            right = groups[idx]
            left = groups[idx + 1]
            combined = right["items"] + left["items"]
            combined_sorted = sorted(combined, key=lambda d: d.vpos)
            if len(combined_sorted) >= 2:
                first, second = combined_sorted[0], combined_sorted[1]
                cross_pair = (first in right["items"] and second in left["items"]) or (first in left["items"] and second in right["items"])
                if cross_pair:
                    v_gap = abs(first.vpos - second.vpos)
                    x_gap = abs(first.x - second.x)
                    widths_ok = first.width <= SHORT_LINE_WIDTH_THRESHOLD and second.width <= SHORT_LINE_WIDTH_THRESHOLD
                    peers = [item for item in combined_sorted if item not in (first, second)]
                    peer_widths = [item.width for item in peers]
                    peer_ratios = [item.ratio for item in peers]
                    baseline_ratio = statistics.median(peer_ratios) if peer_ratios else 1.0
                    baseline_width = statistics.median(peer_widths) if peer_widths else min(first.width, second.width)
                    ratio_factor = 1.6
                    width_factor = 1.35
                    def is_mask(item: LineMetrics) -> bool:
                        if not peer_ratios or not peer_widths:
                            return False
                        if item.ratio <= baseline_ratio * ratio_factor:
                            return False
                        return item.width >= baseline_width * width_factor
                    if not widths_ok and (is_mask(first) or is_mask(second)):
                        widths_ok = True
                    third = combined_sorted[2] if len(combined_sorted) >= 3 else None
                    width_step_ok = True
                    if third is not None:
                        width_step_ok = (third.width - max(first.width, second.width)) >= WIDTH_STEP_THRESHOLD
                    if v_gap <= DOUBLE_LINE_VPOS_THRESHOLD and MIN_DOUBLE_LINE_X_GAP <= x_gap <= MAX_DOUBLE_LINE_X_GAP and widths_ok and width_step_ok:
                        right["items"].extend(left["items"])
                        right["x_ref"] = sum(metric.x for metric in right["items"]) / len(right["items"])
                        del groups[idx + 1]
                        changed = True
                        continue
            idx += 1
    groups.sort(key=lambda g: g["x_ref"], reverse=True)


def sort_group_items(items: List[LineMetrics], *, column_desc: bool) -> None:
    items.sort(key=lambda d: (d.vpos, -d.x if column_desc else d.x))
    swapped = True
    while swapped:
        swapped = False
        for i in range(len(items) - 1):
            current, nxt = items[i], items[i + 1]
            v_gap = current.vpos - nxt.vpos
            if abs(v_gap) <= VERTICAL_TIE_THRESHOLD:
                should_swap = current.x < nxt.x if column_desc else current.x > nxt.x
            else:
                should_swap = v_gap > 0
            if should_swap:
                items[i], items[i + 1] = items[i + 1], items[i]
                swapped = True


def order_lines_in_block(lines: Sequence["Line"], *, column_desc: bool) -> Tuple[List["Line"], float]:
    metrics: List[LineMetrics] = []
    for line in lines:
        metric = build_metrics(line)
        if metric is not None:
            metrics.append(metric)
    if not metrics:
        ordered = sorted(lines, key=lambda obj: obj.order)
        return ordered, 0.0
    groups = group_textlines(metrics, column_desc=column_desc)
    maybe_merge_double_columns(groups)
    groups.sort(key=lambda g: g["x_ref"], reverse=column_desc)
    ordered: List["Line"] = []
    seen = set()
    for group in groups:
        sort_group_items(group["items"], column_desc=column_desc)
        for metric in group["items"]:
            ordered.append(metric.line)
            seen.add(metric.line)
    for line in lines:
        if line not in seen:
            ordered.append(line)
    center = sum(metric.x for metric in metrics) / len(metrics)
    return ordered, center


def order_document_lines(lines: Sequence["Line"], *, column_desc: bool) -> List["Line"]:
    if not lines:
        return []
    by_block: dict[Optional[int], List["Line"]] = {}
    for line in lines:
        by_block.setdefault(line.block_id, []).append(line)
    blocks_with_centers: List[Tuple[float, List["Line"]]] = []
    for block_lines in by_block.values():
        ordered, center = order_lines_in_block(block_lines, column_desc=column_desc)
        blocks_with_centers.append((center, ordered))
    blocks_with_centers.sort(key=lambda item: item[0], reverse=column_desc)
    ordered_lines: List["Line"] = []
    for _, block_lines in blocks_with_centers:
        ordered_lines.extend(block_lines)
    return ordered_lines

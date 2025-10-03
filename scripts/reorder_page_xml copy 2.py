#!/usr/bin/env python3
"""Reorder ALTO XML TextLine elements to match reading order.

This script groups text lines by their horizontal position and sorts each
column top-to-bottom while handling mixed single-/double-line layouts.
"""
from __future__ import annotations

import argparse
import sys
import xml.etree.ElementTree as ET
from statistics import median
from typing import Iterable, List, Optional

# Default heuristic thresholds (pixels) tuned for the current project.
HORIZONTAL_GROUP_THRESHOLD = 60
DOUBLE_LINE_VPOS_THRESHOLD = 40
VERTICAL_TIE_THRESHOLD = 25
SHORT_LINE_WIDTH_THRESHOLD = 150
WIDTH_STEP_THRESHOLD = 30
MIN_DOUBLE_LINE_X_GAP = 50
MAX_DOUBLE_LINE_X_GAP = 200

ALTO_DEFAULT_NAMESPACE = "http://www.loc.gov/standards/alto/ns-v4#"


def parse_args(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sort ALTO TextLine nodes to follow visual reading order."
    )
    parser.add_argument("input", help="Path to the ALTO XML file to reorder")
    parser.add_argument(
        "-o",
        "--output",
        help=(
            "Destination for the rewritten XML. Defaults to the input path, "
            "meaning the file is updated in place."
        ),
    )
    parser.add_argument(
        "--indent",
        action="store_true",
        help="Pretty-print the XML with two-space indentation (disabled by default).",
    )
    parser.add_argument(
        "--ensure-namespace",
        action="store_true",
        help="Inject the standard ALTO default namespace if the root element is missing one.",
    )
    return parser.parse_args(argv)


def get_namespace(tag: str) -> Optional[str]:
    if tag.startswith("{") and "}" in tag:
        return tag[1 : tag.index("}")]
    return None


def tag_matches(element: ET.Element, local_name: str) -> bool:
    if element.tag == local_name:
        return True
    if element.tag.endswith(f"}}{local_name}"):
        return True
    return False


def compute_metrics(line: ET.Element) -> tuple[float, float, float, float, float, float]:
    baseline = line.get("BASELINE", "").strip()
    coords = [int(value) for value in baseline.split()] if baseline else []

    xs = coords[0::2]
    ys = coords[1::2]

    if xs:
        x_avg = sum(xs) / len(xs)
    else:
        x_avg = float(line.get("HPOS", 0))

    if ys:
        y_min = min(ys)
    else:
        y_min = float(line.get("VPOS", 0))

    vpos = float(line.get("VPOS", 0))
    width = float(line.get("WIDTH", 0))
    namespace = get_namespace(line.tag)
    if namespace:
        polygon = line.find(f'{{{namespace}}}Shape/{{{namespace}}}Polygon')
    else:
        polygon = line.find('Shape/Polygon')
    if polygon is not None and polygon.get("POINTS"):
        p_coords = [int(value) for value in polygon.get("POINTS").split()]
        px = p_coords[0::2]
        min_x = min(px)
        max_x = max(px)
    else:
        hpos = float(line.get("HPOS", x_avg))
        min_x = hpos
        max_x = hpos + width
    left_span = max(x_avg - min_x, 0.0)
    right_span = max(max_x - x_avg, 0.0)
    return x_avg, y_min, vpos, width, left_span, right_span


def group_textlines(textlines: List[dict]) -> List[dict]:
    groups: List[dict] = []
    for data in textlines:
        for group in groups:
            if abs(data["x"] - group["x_ref"]) <= HORIZONTAL_GROUP_THRESHOLD:
                group["items"].append(data)
                group["x_ref"] = sum(item["x"] for item in group["items"]) / len(group["items"])
                break
        else:
            groups.append({"x_ref": data["x"], "items": [data]})
    groups.sort(key=lambda g: g["x_ref"], reverse=True)
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
            combined_sorted = sorted(combined, key=lambda d: d["vpos"])
            if len(combined_sorted) >= 2:
                first, second = combined_sorted[0], combined_sorted[1]
                cross_group_pair = (
                    (first in right["items"] and second in left["items"]) or
                    (first in left["items"] and second in right["items"])
                )
                if cross_group_pair:
                    v_gap = abs(first["vpos"] - second["vpos"])
                    x_gap = abs(first["x"] - second["x"])
                    widths_ok = (
                        first["width"] <= SHORT_LINE_WIDTH_THRESHOLD and
                        second["width"] <= SHORT_LINE_WIDTH_THRESHOLD
                    )
                    peer_widths = [item["width"] for item in combined_sorted if item not in (first, second)]
                    peer_ratios = []
                    for item in combined_sorted:
                        left_span = max(item.get("left_span", 0.0), 1.0)
                        right_span = max(item.get("right_span", 0.0), 1.0)
                        ratio = max(left_span, right_span) / max(min(left_span, right_span), 1.0)
                        if item not in (first, second):
                            peer_ratios.append(ratio)
                    baseline_ratio = median(peer_ratios) if peer_ratios else 1.0
                    baseline_width = median(peer_widths) if peer_widths else min(first["width"], second["width"])
                    ratio_factor = 1.6
                    width_factor = 1.35

                    def is_mask(item: dict) -> bool:
                        left_span = max(item.get("left_span", 0.0), 1.0)
                        right_span = max(item.get("right_span", 0.0), 1.0)
                        ratio = max(left_span, right_span) / max(min(left_span, right_span), 1.0)
                        if not peer_ratios:
                            return False
                        if ratio <= baseline_ratio * ratio_factor:
                            return False
                        if not peer_widths:
                            return False
                        return item["width"] >= baseline_width * width_factor

                    if not widths_ok:
                        if is_mask(first) and is_mask(second):
                            widths_ok = True
                        elif is_mask(first) or is_mask(second):
                            widths_ok = True
                    third = combined_sorted[2] if len(combined_sorted) >= 3 else None
                    width_step_ok = True
                    if third is not None:
                        width_step_ok = (
                            third["width"] - max(first["width"], second["width"])
                        ) >= WIDTH_STEP_THRESHOLD
                    if not widths_ok and combined_sorted:
                        narrow_candidates = [item["width"] for item in combined_sorted[2:]]
                        if narrow_candidates:
                            narrow_width = min(narrow_candidates)
                            if narrow_width < SHORT_LINE_WIDTH_THRESHOLD:
                                dynamic_limit = max(
                                    SHORT_LINE_WIDTH_THRESHOLD,
                                    narrow_width + WIDTH_STEP_THRESHOLD * 3,
                                    narrow_width * 1.5,
                                )
                                if (
                                    first["width"] <= dynamic_limit
                                    and second["width"] <= dynamic_limit
                                    and max(first["width"], second["width"]) >= narrow_width + WIDTH_STEP_THRESHOLD
                                ):
                                    widths_ok = True

                    if (
                        v_gap <= DOUBLE_LINE_VPOS_THRESHOLD
                        and MIN_DOUBLE_LINE_X_GAP <= x_gap <= MAX_DOUBLE_LINE_X_GAP
                        and widths_ok
                        and width_step_ok
                    ):
                        right["items"].extend(left["items"])
                        right["x_ref"] = (
                            sum(item["x"] for item in right["items"])
                            / len(right["items"])
                        )
                        del groups[idx + 1]
                        changed = True
                        continue
            idx += 1


def sort_group_items(items: List[dict]) -> None:
    items.sort(key=lambda d: (d["vpos"], -d["x"]))
    swapped = True
    while swapped:
        swapped = False
        for i in range(len(items) - 1):
            current, nxt = items[i], items[i + 1]
            v_gap = current["vpos"] - nxt["vpos"]
            if abs(v_gap) <= VERTICAL_TIE_THRESHOLD:
                if current["x"] < nxt["x"]:
                    items[i], items[i + 1] = items[i + 1], items[i]
                    swapped = True
            elif v_gap > 0:
                items[i], items[i + 1] = items[i + 1], items[i]
                swapped = True


def ensure_default_namespace(root: ET.Element) -> Optional[str]:
    namespace = get_namespace(root.tag)
    if namespace:
        if 'xmlns' not in root.attrib:
            for attr, value in list(root.attrib.items()):
                if attr.startswith('xmlns:') and value == namespace:
                    del root.attrib[attr]
                    root.set('xmlns', namespace)
                    break
        return namespace
    if (root.tag == "alto" or root.tag.endswith(":alto")) and "xmlns" not in root.attrib:
        root.set("xmlns", ALTO_DEFAULT_NAMESPACE)
        return ALTO_DEFAULT_NAMESPACE
    if root.tag == "alto" and "xmlns" in root.attrib:
        return root.attrib.get("xmlns")
    return None


def reorder_textlines(root: ET.Element, inject_namespace: bool = False) -> None:
    namespace = ensure_default_namespace(root) if inject_namespace else get_namespace(root.tag)
    if namespace:
        try:
            ET.register_namespace('', namespace)
        except (ValueError, AttributeError):
            pass
    ns = {"alto": namespace} if namespace else {}

    if namespace:
        blocks = root.findall('.//alto:TextBlock', ns)
        if not blocks:
            blocks = root.findall('.//TextBlock')
    else:
        blocks = root.findall('.//TextBlock')

    for block in blocks:
        children = list(block)
        textlines: List[dict] = []
        for child in children:
            if not tag_matches(child, 'TextLine'):
                continue
            x, y_base, vpos, width, left_span, right_span = compute_metrics(child)
            textlines.append({
                "element": child,
                "x": x,
                "y": y_base,
                "vpos": vpos,
                "width": width,
                "left_span": left_span,
                "right_span": right_span,
            })
        if not textlines:
            continue

        textlines.sort(key=lambda d: d["x"], reverse=True)
        groups = group_textlines(textlines)
        maybe_merge_double_columns(groups)

        ordered_elements: List[ET.Element] = []
        for group in groups:
            sort_group_items(group["items"])
            ordered_elements.extend(item["element"] for item in group["items"])

        ordered_iter = iter(ordered_elements)
        new_children: List[ET.Element] = []
        for child in children:
            if tag_matches(child, 'TextLine'):
                new_children.append(next(ordered_iter))
            else:
                new_children.append(child)
        block[:] = new_children


def main() -> None:
    args = parse_args()

    # Capture original declaration to preserve quoting and spacing.
    with open(args.input, 'rb') as src:
        original_bytes = src.read()

    original_header: Optional[bytes] = None
    if original_bytes.startswith(b'<?xml'):
        newline_idx = original_bytes.find(b'\n')
        if newline_idx != -1:
            original_header = original_bytes[: newline_idx + 1]
        else:
            original_header = original_bytes

    try:
        root = ET.fromstring(original_bytes)
    except ET.ParseError as exc:
        sys.stderr.write(f"Failed to parse XML: {exc}\n")
        sys.exit(1)
    tree = ET.ElementTree(root)

    reorder_textlines(root, inject_namespace=args.ensure_namespace)

    if args.indent:
        try:
            ET.indent(tree, space='  ')
        except AttributeError:
            pass

    output_path = args.output or args.input
    tree.write(output_path, encoding='UTF-8', xml_declaration=True)

    if original_header is not None:
        with open(output_path, 'rb') as out:
            updated_bytes = out.read()
        if updated_bytes.startswith(b'<?xml'):
            newline_idx = updated_bytes.find(b'\n')
            if newline_idx != -1:
                current_header = updated_bytes[: newline_idx + 1]
                if current_header != original_header:
                    updated_bytes = original_header + updated_bytes[newline_idx + 1 :]
                    with open(output_path, 'wb') as out:
                        out.write(updated_bytes)


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Reorder ALTO XML TextLine elements to match reading order.

This script can process individual ALTO files or a zip archive of ALTO/PAGE XML
pages, rewriting the files so their `TextLine` nodes follow a consistent
right-to-left column and top-to-bottom reading order.
"""
from __future__ import annotations

import argparse
import io
import sys
import zipfile
from pathlib import Path
from statistics import median
from typing import Iterable, List, Optional, Sequence
import xml.etree.ElementTree as ET

# Default heuristic thresholds (pixels) tuned for the current project.
HORIZONTAL_GROUP_THRESHOLD = 60
DOUBLE_LINE_VPOS_THRESHOLD = 40
VERTICAL_TIE_THRESHOLD = 25
SHORT_LINE_WIDTH_THRESHOLD = 150
WIDTH_STEP_THRESHOLD = 30
MIN_DOUBLE_LINE_X_GAP = 50
MAX_DOUBLE_LINE_X_GAP = 200

ALTO_DEFAULT_NAMESPACE = "http://www.loc.gov/standards/alto/ns-v4#"
SUPPORTED_EXTENSIONS = {".xml", ".alto", ".page"}


def parse_args(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sort ALTO TextLine nodes to follow visual reading order."
    )
    parser.add_argument("input", help="Path to an ALTO/PAGE XML file or a zip archive")
    parser.add_argument(
        "-o",
        "--output",
        help=(
            "Destination for the rewritten XML or zip archive. Defaults to the "
            "input path (in-place update)."
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
    parser.add_argument(
        "--extensions",
        nargs="*",
        default=None,
        help=(
            "Additional file extensions to include when processing zip archives. "
            "Defaults to common ALTO/PAGE extensions (.xml, .alto, .page)."
        ),
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
    namespace = get_namespace(line.tag)
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


def parse_xml_bytes(data: bytes) -> ET.ElementTree:
    try:
        root = ET.fromstring(data)
    except ET.ParseError as exc:
        raise ValueError(f"Failed to parse XML: {exc}") from exc
    return ET.ElementTree(root)


def serialize_xml(tree: ET.ElementTree, indent: bool) -> bytes:
    if indent:
        try:
            ET.indent(tree, space='  ')
        except AttributeError:
            pass
    buffer = io.BytesIO()
    tree.write(buffer, encoding='UTF-8', xml_declaration=True)
    return buffer.getvalue()


def process_xml_bytes(data: bytes, *, indent: bool, inject_namespace: bool) -> bytes:
    tree = parse_xml_bytes(data)
    root = tree.getroot()
    reorder_textlines(root, inject_namespace=inject_namespace)
    return serialize_xml(tree, indent)


def process_file(path: Path, output_path: Optional[Path], *, indent: bool, inject_namespace: bool) -> None:
    with path.open('rb') as src:
        original_bytes = src.read()

    updated_bytes = process_xml_bytes(
        original_bytes,
        indent=indent,
        inject_namespace=inject_namespace,
    )

    dest = output_path or path
    dest.write_bytes(updated_bytes)


def process_zip(input_path: Path, output_path: Optional[Path], *, indent: bool, inject_namespace: bool, extensions: Optional[Sequence[str]]) -> None:
    allowed_exts = set(ext.lower() for ext in (extensions or SUPPORTED_EXTENSIONS))
    output_buffer = io.BytesIO()

    with zipfile.ZipFile(input_path, 'r') as zf, zipfile.ZipFile(output_buffer, 'w', compression=zipfile.ZIP_DEFLATED) as out_zip:
        for info in zf.infolist():
            with zf.open(info) as src:
                data = src.read()
            ext = Path(info.filename).suffix.lower()
            if ext in allowed_exts:
                try:
                    updated = process_xml_bytes(data, indent=indent, inject_namespace=inject_namespace)
                except ValueError as exc:
                    sys.stderr.write(f"Skipping {info.filename}: {exc}\n")
                    updated = data
                out_zip.writestr(info, updated)
            else:
                out_zip.writestr(info, data)

    dest = output_path or input_path
    dest.write_bytes(output_buffer.getvalue())


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output) if args.output else None

    if input_path.suffix.lower() == '.zip':
        process_zip(
            input_path,
            output_path,
            indent=args.indent,
            inject_namespace=args.ensure_namespace,
            extensions=args.extensions,
        )
    else:
        process_file(
            input_path,
            output_path,
            indent=args.indent,
            inject_namespace=args.ensure_namespace,
        )


if __name__ == '__main__':
    main()

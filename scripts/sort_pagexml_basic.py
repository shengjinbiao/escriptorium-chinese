#!/usr/bin/env python3
"""Baseline PAGE/ALTO line re-ordering script (original heuristics).

This script retains the very first ordering approach we explored: columns are
clustered by X centre and processed from right to left, and within each column
lines are simply sorted from right to left using their centre X coordinate.

It supports single-file processing (PAGE or ALTO). Use the newer
`scripts/sort_pagexml.py` for batch/directory handling or more features.
"""
from __future__ import annotations

import argparse
import statistics
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional

DEFAULT_PAGE_XML_NS = "http://schema.primaresearch.org/PAGE/gts/pagecontent/2013-07-15"
PAGE_XML_NS = DEFAULT_PAGE_XML_NS
NSMAP = {"pc": PAGE_XML_NS}


def configure_namespace(ns_uri: Optional[str]) -> None:
    global PAGE_XML_NS, NSMAP
    PAGE_XML_NS = ns_uri or DEFAULT_PAGE_XML_NS
    NSMAP = {"pc": PAGE_XML_NS}
    ET.register_namespace("", PAGE_XML_NS)


@dataclass
class LineInfo:
    element: ET.Element
    parent: ET.Element
    min_x: float
    max_x: float
    min_y: float
    max_y: float

    @property
    def width(self) -> float:
        return self.max_x - self.min_x

    @property
    def height(self) -> float:
        return self.max_y - self.min_y

    @property
    def center_x(self) -> float:
        return (self.min_x + self.max_x) / 2.0

    @property
    def center_y(self) -> float:
        return (self.min_y + self.max_y) / 2.0


def parse_points(points_attr: str) -> List[tuple]:
    pts: List[tuple] = []
    for pair in points_attr.strip().split():
        if "," not in pair:
            continue
        try:
            x_str, y_str = pair.split(",", 1)
            pts.append((float(x_str), float(y_str)))
        except ValueError:
            continue
    return pts


def points_bbox(points: Iterable[tuple]) -> Optional[tuple]:
    xs: List[float] = []
    ys: List[float] = []
    for x, y in points:
        xs.append(x)
        ys.append(y)
    if not xs:
        return None
    return min(xs), max(xs), min(ys), max(ys)


def load_page_lines(page_root: ET.Element) -> List[LineInfo]:
    lines: List[LineInfo] = []
    for region in page_root.findall(".//pc:TextRegion", NSMAP):
        for line in region.findall("pc:TextLine", NSMAP):
            coords_el = line.find("pc:Coords", NSMAP)
            if coords_el is None or not coords_el.get("points"):
                continue
            bbox = points_bbox(parse_points(coords_el.get("points", "")))
            if not bbox:
                continue
            min_x, max_x, min_y, max_y = bbox
            lines.append(LineInfo(line, region, min_x, max_x, min_y, max_y))
    return lines


def alto_line_bbox(line: ET.Element, string_tag: str, polygon_tag: Optional[str]) -> Optional[tuple]:
    def attr_float(el: ET.Element, name: str) -> Optional[float]:
        value = el.get(name)
        if value is None:
            return None
        try:
            return float(value)
        except ValueError:
            return None

    hpos = attr_float(line, "HPOS")
    vpos = attr_float(line, "VPOS")
    width = attr_float(line, "WIDTH")
    height = attr_float(line, "HEIGHT")
    if None not in (hpos, vpos, width, height):
        return hpos, hpos + width, vpos, vpos + height

    xs: List[float] = []
    ys: List[float] = []

    for token in line.findall(string_tag):
        th = attr_float(token, "HPOS")
        tv = attr_float(token, "VPOS")
        tw = attr_float(token, "WIDTH")
        tht = attr_float(token, "HEIGHT")
        if None in (th, tv, tw, tht):
            continue
        xs.extend([th, th + tw])
        ys.extend([tv, tv + tht])

    if polygon_tag:
        polygon = line.find(polygon_tag)
        if polygon is not None and polygon.get("POINTS"):
            for pair in polygon.get("POINTS").strip().split():
                if "," not in pair:
                    continue
                try:
                    x_str, y_str = pair.split(",", 1)
                    xs.append(float(x_str))
                    ys.append(float(y_str))
                except ValueError:
                    continue

    if xs and ys:
        return min(xs), max(xs), min(ys), max(ys)
    return None


def load_alto_lines(root: ET.Element, ns: Optional[str]) -> List[LineInfo]:
    lines: List[LineInfo] = []
    textblock_tag = f"{{{ns}}}TextBlock" if ns else "TextBlock"
    textline_tag = f"{{{ns}}}TextLine" if ns else "TextLine"
    string_tag = f"{{{ns}}}String" if ns else "String"
    shape_tag = f"{{{ns}}}Shape" if ns else "Shape"
    polygon_tag = f"{{{ns}}}Polygon" if ns else "Polygon"

    for block in root.findall(f".//{textblock_tag}"):
        for line in block.findall(textline_tag):
            shape_el = line.find(shape_tag)
            polygon = None
            if shape_el is not None:
                polygon = shape_el.find(polygon_tag)
            bbox = alto_line_bbox(line, string_tag, polygon_tag if polygon is not None else None)
            if bbox is None:
                continue
            min_x, max_x, min_y, max_y = bbox
            lines.append(LineInfo(line, block, min_x, max_x, min_y, max_y))
    return lines


def estimate_threshold(values: List[float], default: float, scale: float) -> float:
    filtered = [abs(v) for v in values if v > 0]
    if not filtered:
        return default
    med = statistics.median(filtered)
    return max(default, med * scale)


def cluster_columns(lines: List[LineInfo], threshold: float) -> List[List[LineInfo]]:
    groups: List[List[LineInfo]] = []
    centroids: List[float] = []
    for line in sorted(lines, key=lambda l: l.center_x, reverse=True):
        placed = False
        for idx, centre in enumerate(centroids):
            if abs(line.center_x - centre) <= threshold:
                groups[idx].append(line)
                centroids[idx] = sum(l.center_x for l in groups[idx]) / len(groups[idx])
                placed = True
                break
        if not placed:
            groups.append([line])
            centroids.append(line.center_x)
    return groups


def group_by_rows(lines: List[LineInfo], y_threshold: float) -> List[List[LineInfo]]:
    rows: List[List[LineInfo]] = []
    if not lines:
        return rows
    sorted_lines = sorted(lines, key=lambda l: l.min_y)
    for line in sorted_lines:
        appended = False
        for row in rows:
            row_bottom = max(l.max_y for l in row)
            if line.min_y <= row_bottom + y_threshold:
                row.append(line)
                appended = True
                break
        if not appended:
            rows.append([line])
    return rows


def order_lines(lines: List[LineInfo]) -> List[LineInfo]:
    if not lines:
        return []
    widths = [line.width for line in lines]
    heights = [line.height for line in lines]
    page_width = max((line.max_x for line in lines), default=0) - min((line.min_x for line in lines), default=0)
    column_threshold = estimate_threshold(widths, default=page_width / 12.0 if page_width else 40.0, scale=1.25)
    row_threshold = estimate_threshold(heights, default=20.0, scale=0.6)

    columns = cluster_columns(lines, column_threshold)
    columns.sort(key=lambda group: sum(l.center_x for l in group) / len(group), reverse=True)

    ordered: List[LineInfo] = []
    for column in columns:
        rows = group_by_rows(column, row_threshold)
        for row in rows:
            ordered.extend(sorted(row, key=lambda l: l.center_x, reverse=True))
    return ordered


def reorder_parents(ordered: List[LineInfo]) -> None:
    by_parent = {}
    for info in ordered:
        by_parent.setdefault(info.parent, []).append(info)
    for parent, parent_lines in by_parent.items():
        for info in parent_lines:
            if info.element in list(parent):
                parent.remove(info.element)
        for info in parent_lines:
            parent.append(info.element)


def update_custom_attr(element: ET.Element, index: int) -> None:
    custom = element.get("custom", "").strip()
    entry = f"readingOrder {{index:{index};}}"
    if not custom:
        element.set("custom", entry)
        return
    if "readingOrder" in custom:
        start = custom.find("readingOrder")
        end = custom.find("}", start)
        if end != -1:
            end += 1
            custom = custom[:start] + entry + custom[end:]
        else:
            custom = entry
    else:
        if not custom.endswith(";") and not custom.endswith("}"):
            custom = custom + ";"
        custom = custom + " " + entry
    element.set("custom", custom.strip())


def process_page(root: ET.Element) -> bool:
    page_el = root.find("pc:Page", NSMAP)
    if page_el is None:
        print("No <Page> element found in XML.", file=sys.stderr)
        return False
    lines = load_page_lines(page_el)
    if not lines:
        print("No TextLine elements with coordinates found.", file=sys.stderr)
        return False
    ordered = order_lines(lines)
    reorder_parents(ordered)
    for idx, info in enumerate(ordered):
        update_custom_attr(info.element, idx)
    return True


def process_alto(root: ET.Element) -> bool:
    ns = extract_namespace(root.tag)
    lines = load_alto_lines(root, ns)
    if not lines:
        print("No ALTO TextLine elements with usable coordinates found.", file=sys.stderr)
        return False
    ordered = order_lines(lines)
    reorder_parents(ordered)
    for idx, info in enumerate(ordered):
        info.element.set("READING_ORDER", str(idx))
    return True


def extract_namespace(tag: str) -> Optional[str]:
    if not tag.startswith("{"):
        return None
    try:
        return tag[1 : tag.index("}")]
    except ValueError:
        return None


def determine_format(root: ET.Element) -> Optional[str]:
    ns = extract_namespace(root.tag) or ""
    lname = root.tag.split("}")[-1].lower()
    if "pagecontent" in ns or lname == "pcgts":
        return "page"
    if "alto" in ns or lname == "alto":
        return "alto"
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Reorder a PAGE or ALTO XML file using the baseline heuristics.")
    parser.add_argument("input", type=Path, help="Input XML file")
    parser.add_argument("-o", "--output", type=Path, help="Output file (defaults to stdout).")
    parser.add_argument("--inplace", action="store_true", help="Overwrite the input file in place.")
    args = parser.parse_args()

    if not args.input.exists():
        parser.error(f"Input file '{args.input}' does not exist")

    if args.inplace and args.output:
        parser.error("Specify either --inplace or --output, not both.")

    tree = ET.parse(args.input)
    root = tree.getroot()
    configure_namespace(extract_namespace(root.tag))

    doc_type = determine_format(root)
    if doc_type == "page":
        success = process_page(root)
    elif doc_type == "alto":
        success = process_alto(root)
    else:
        print("Unsupported XML format.", file=sys.stderr)
        return 1

    if not success:
        return 1

    destination = args.input if args.inplace else args.output
    if destination:
        tree.write(destination, encoding="UTF-8", xml_declaration=True)
    else:
        tree.write(sys.stdout.buffer, encoding="UTF-8", xml_declaration=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

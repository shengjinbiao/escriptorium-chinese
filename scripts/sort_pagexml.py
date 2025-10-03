#!/usr/bin/env python3
"""Sort PAGE/PAGE-XML or ALTO TextLine elements using geometric heuristics.

This script reorders the lines in a PAGE-XML or ALTO XML file so they follow a
reading order tailored for traditionally typeset Chinese layouts: columns ordered from
right to left, and inside each column, content ordered from top to bottom with
rightmost items first when lines overlap in height (handling double or nested
lines).

The resulting order is written back into the XML by:
    * Physically reordering the <TextLine> elements inside each region
    * Refreshing the "readingOrder {index:...;}" entry inside every line's
      "custom" attribute (creating it if missing)

Usage:
    python scripts/sort_pagexml.py INPUT.xml -o OUTPUT.xml
    python scripts/sort_pagexml.py INPUT.xml --inplace
    python scripts/sort_pagexml.py INPUT_DIR/ -o OUTPUT_DIR/

The heuristics are intentionally lightweight and only rely on the coordinates
already present in PAGE-XML exports produced by eScriptorium.
"""
from __future__ import annotations

import argparse
import io
import re
import statistics
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional
import shutil

# Default PAGE namespace used by most exports; overridden when parsing files
DEFAULT_PAGE_XML_NS = "http://schema.primaresearch.org/PAGE/gts/pagecontent/2013-07-15"
PAGE_XML_NS = DEFAULT_PAGE_XML_NS
NSMAP = {"pc": PAGE_XML_NS}
TEXTLINE_TAG = f"{{{PAGE_XML_NS}}}TextLine"
COORDS_TAG = f"{{{PAGE_XML_NS}}}Coords"

SKIP_FILENAMES = {"mets.xml"}


def configure_namespace(ns_uri: Optional[str]) -> None:
    """Update namespace globals so helper functions follow the document's URI."""
    global PAGE_XML_NS, NSMAP, TEXTLINE_TAG, COORDS_TAG

    PAGE_XML_NS = ns_uri or DEFAULT_PAGE_XML_NS
    NSMAP = {"pc": PAGE_XML_NS}
    TEXTLINE_TAG = f"{{{PAGE_XML_NS}}}TextLine"
    COORDS_TAG = f"{{{PAGE_XML_NS}}}Coords"
    ET.register_namespace("", PAGE_XML_NS)


@dataclass
class LineInfo:
    element: ET.Element
    parent: ET.Element
    poly: List[tuple]
    min_x: float
    max_x: float
    min_y: float
    max_y: float
    tag: Optional[str] = None
    index: int = 0

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
            poly = parse_points(coords_el.get("points", ""))
            bbox = points_bbox(poly)
            if not bbox:
                continue
            min_x, max_x, min_y, max_y = bbox
            lines.append(
                LineInfo(
                    element=line,
                    parent=region,
                    poly=poly,
                    min_x=min_x,
                    max_x=max_x,
                    min_y=min_y,
                    max_y=max_y,
                    index=len(lines),
                )
            )
    return lines


def alto_line_bbox(line: ET.Element, string_tag: str, polygon: Optional[ET.Element]) -> Optional[tuple]:
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
        thpos = attr_float(token, "HPOS")
        tvpos = attr_float(token, "VPOS")
        twidth = attr_float(token, "WIDTH")
        theight = attr_float(token, "HEIGHT")
        if None in (thpos, tvpos, twidth, theight):
            continue
        xs.extend([thpos, thpos + twidth])
        ys.extend([tvpos, tvpos + theight])

    if polygon is not None and polygon.get("POINTS"):
        for pair in polygon.get("POINTS", "").strip().split():
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


def build_alto_tag_map(root: ET.Element, ns: Optional[str]) -> dict[str, str]:
    tag_map: dict[str, str] = {}
    other_tag = f"{{{ns}}}OtherTag" if ns else "OtherTag"
    for tag in root.findall(f".//{other_tag}"):
        tag_id = tag.get("ID")
        label = tag.get("LABEL")
        if tag_id and label:
            tag_map[tag_id] = label.lower()
    return tag_map


def load_alto_lines(root: ET.Element, ns: Optional[str], tag_map: Optional[dict[str, str]] = None) -> List[LineInfo]:
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
            bbox = alto_line_bbox(line, string_tag, polygon)
            if bbox is None:
                continue
            min_x, max_x, min_y, max_y = bbox
            tag_label = None
            tag_refs = line.get("TAGREFS", "")
            if tag_map and tag_refs:
                for tag_id in tag_refs.split():
                    mapped = tag_map.get(tag_id)
                    if mapped:
                        tag_label = mapped
                        break
            lines.append(
                LineInfo(
                    element=line,
                    parent=block,
                    poly=[],
                    min_x=min_x,
                    max_x=max_x,
                    min_y=min_y,
                    max_y=max_y,
                    tag=tag_label,
                    index=len(lines),
                )
            )
    return lines


def estimate_threshold(values: List[float], default: float, scale: float) -> float:
    filtered = [abs(v) for v in values if v > 0]
    if not filtered:
        return default
    med = statistics.median(filtered)
    return max(default, med * scale)


def cluster_columns(lines: List[LineInfo], threshold: float, median_height: float) -> List[List[LineInfo]]:
    groups: List[List[LineInfo]] = []
    centroids: List[float] = []
    for line in sorted(lines, key=lambda l: l.center_x, reverse=True):
        placed = False
        for idx, centre in enumerate(centroids):
            tag = (line.tag or "").lower()
            is_short = median_height and line.height <= median_height * 0.4
            is_def = tag == "default"
            boost = 1.5 if (is_def or is_short) else 1.0
            if abs(line.center_x - centre) <= threshold * boost:
                groups[idx].append(line)
                new_centre = sum(l.center_x for l in groups[idx]) / len(groups[idx])
                centroids[idx] = new_centre
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
    median_height = statistics.median(heights) if heights else 0.0
    median_width = statistics.median(widths) if widths else 0.0
    centers = sorted((line.center_x for line in lines), reverse=True)
    center_gaps = [centers[i] - centers[i + 1] for i in range(len(centers) - 1)]
    center_gap_median = statistics.median(center_gaps) if center_gaps else 0.0
    page_width = max((line.max_x for line in lines), default=0) - min(
        (line.min_x for line in lines), default=0
    )
    base_threshold = max(center_gap_median * 1.2, median_width * 1.25, page_width / 12.0 if page_width else 40.0)
    column_threshold = max(40.0, base_threshold)
    row_threshold = estimate_threshold(heights, default=20.0, scale=0.6)

    columns = cluster_columns(lines, column_threshold, median_height)

    column_map = {line.index: idx for idx, column in enumerate(columns) for line in column}
    sorted_by_index = sorted(lines, key=lambda l: l.index)

    def is_main_line(line: LineInfo) -> bool:
        tag = (line.tag or "").lower()
        if tag == "doubleline":
            return True
        if median_height and line.height >= median_height * 0.7:
            return True
        if median_width and line.width >= median_width * 0.8:
            return True
        return False

    for idx, line in enumerate(sorted_by_index):
        if (line.tag or "").lower() != "default":
            continue
        current_column = column_map.get(line.index)
        if current_column is None:
            continue

        prev_main = None
        for prev in reversed(sorted_by_index[:idx]):
            if is_main_line(prev):
                prev_main = prev
                break

        next_main = None
        for nxt in sorted_by_index[idx + 1 :]:
            if is_main_line(nxt):
                next_main = nxt
                break

        target = None
        if prev_main and next_main:
            prev_col = column_map.get(prev_main.index)
            next_col = column_map.get(next_main.index)
            if prev_col is not None and prev_col == next_col:
                target = prev_main
            else:
                target = min(
                    [prev_main, next_main],
                    key=lambda candidate: abs(candidate.center_x - line.center_x),
                )
        elif prev_main:
            target = prev_main
        elif next_main:
            target = next_main

        if target is None:
            continue

        target_column = column_map.get(target.index)
        if target_column is None or target_column == current_column:
            continue

        try:
            columns[current_column].remove(line)
        except ValueError:
            continue
        columns[target_column].append(line)
        column_map[line.index] = target_column

    columns = [column for column in columns if column]
    column_centers = [sum(l.center_x for l in column) / len(column) for column in columns]
    columns = [column for _, column in sorted(zip(column_centers, columns), key=lambda item: item[0], reverse=True)]

    ordered: List[LineInfo] = []
    for column in columns:
        column_sorted = sorted(column, key=lambda l: l.index)
        ordered.extend(column_sorted)
    return ordered


READING_ORDER_PATTERN = re.compile(r"readingOrder\s*\{[^}]*\}")


def extract_namespace(tag: str) -> Optional[str]:
    if not tag.startswith("{"):
        return None
    try:
        return tag[1 : tag.index("}")]
    except ValueError:
        return None


def local_name(tag: str) -> str:
    if tag.startswith("{") and "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def update_custom_attr(element: ET.Element, index: int) -> None:
    custom = element.get("custom", "").strip()
    entry = f"readingOrder {{index:{index};}}"
    if not custom:
        element.set("custom", entry)
        return
    if READING_ORDER_PATTERN.search(custom):
        custom = READING_ORDER_PATTERN.sub(entry, custom)
    else:
        if not custom.endswith(";") and not custom.endswith("}"):
            custom = custom + ";"
        custom = custom + " " + entry
    element.set("custom", custom.strip())


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


def process_page_document(root: ET.Element) -> bool:
    page_el = root.find("pc:Page", NSMAP)
    if page_el is None:
        print("No <Page> element found in XML.", file=sys.stderr)
        return False

    lines = load_page_lines(page_el)
    if not lines:
        print("No TextLine elements with coordinates found.", file=sys.stderr)
        return True

    ordered = order_lines(lines)
    reorder_parents(ordered)

    for idx, info in enumerate(ordered):
        update_custom_attr(info.element, idx)

    return True


def process_alto_document(root: ET.Element) -> bool:
    ns = extract_namespace(root.tag)
    tag_map = build_alto_tag_map(root, ns)
    lines = load_alto_lines(root, ns, tag_map)
    if not lines:
        print("No ALTO TextLine elements with usable coordinates found.", file=sys.stderr)
        return True

    ordered = order_lines(lines)
    reorder_parents(ordered)

    for idx, info in enumerate(ordered):
        info.element.set("READING_ORDER", str(idx))

    return True


def reorder_tree(tree: ET.ElementTree, source: Optional[str] = None) -> bool:
    root = tree.getroot()
    configure_namespace(extract_namespace(root.tag))

    doc_type = determine_format(root)
    if doc_type == "page":
        return process_page_document(root)
    if doc_type == "alto":
        return process_alto_document(root)

    label = f" for '{source}'" if source else ""
    print(f"Unsupported XML document format{label}.", file=sys.stderr)
    return False


def process_xml_bytes(data: bytes, source: Optional[str] = None) -> Optional[bytes]:
    try:
        root = ET.fromstring(data)
    except ET.ParseError as exc:
        label = f" '{source}'" if source else ""
        print(f"Failed to parse{label}: {exc}", file=sys.stderr)
        return None

    tree = ET.ElementTree(root)
    if not reorder_tree(tree, source=source):
        return None

    buffer = io.BytesIO()
    tree.write(buffer, encoding="UTF-8", xml_declaration=True)
    return buffer.getvalue()


def determine_format(root: ET.Element) -> Optional[str]:
    ns = extract_namespace(root.tag) or ""
    lname = local_name(root.tag).lower()
    if "pagecontent" in ns or lname == "pcgts":
        return "page"
    if "alto" in ns or lname == "alto":
        return "alto"
    return None


def write_tree(tree: ET.ElementTree, destination: Optional[Path]) -> None:
    if destination is None:
        tree.write(sys.stdout.buffer, encoding="UTF-8", xml_declaration=True)
    else:
        destination.parent.mkdir(parents=True, exist_ok=True)
        tree.write(destination, encoding="UTF-8", xml_declaration=True)


def process_file(input_path: Path, output_path: Optional[Path], inplace: bool) -> bool:
    if input_path.name.lower() in SKIP_FILENAMES:
        if not inplace and output_path is not None:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(input_path, output_path)
        return True
    try:
        tree = ET.parse(input_path)
    except (ET.ParseError, OSError) as exc:
        print(f"Failed to parse '{input_path}': {exc}", file=sys.stderr)
        return False

    if not reorder_tree(tree, source=str(input_path)):
        return False

    destination = input_path if inplace and output_path is None else output_path
    write_tree(tree, destination)
    return True


def process_zip(input_path: Path, output_path: Optional[Path], inplace: bool) -> bool:
    if inplace and output_path is not None:
        raise ValueError("Output path must be omitted when using --inplace with zip input")

    target_path: Path
    temp_file: Optional[tempfile.NamedTemporaryFile] = None
    if inplace:
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
        target_path = Path(temp_file.name)
        temp_file.close()
    else:
        if output_path is None:
            raise ValueError("Output zip path is required when not using --inplace")
        target_path = output_path
        target_path.parent.mkdir(parents=True, exist_ok=True)

    failures = 0
    handled_xml = False

    with zipfile.ZipFile(input_path, "r") as zin, zipfile.ZipFile(
        target_path, "w", compression=zipfile.ZIP_DEFLATED
    ) as zout:
        for info in zin.infolist():
            data = zin.read(info.filename)

            if info.is_dir():
                zout.writestr(info, b"")
                continue

            if info.filename.lower().endswith(".xml") and Path(info.filename).name.lower() not in SKIP_FILENAMES:
                handled_xml = True
                processed = process_xml_bytes(data, source=info.filename)
                if processed is None:
                    failures += 1
                    processed = data

                info_new = zipfile.ZipInfo(info.filename, date_time=info.date_time)
                info_new.compress_type = info.compress_type or zipfile.ZIP_DEFLATED
                info_new.external_attr = info.external_attr
                zout.writestr(info_new, processed)
            else:
                zout.writestr(info, data)

    if inplace:
        assert temp_file is not None
        shutil.move(target_path, input_path)

    if not handled_xml:
        print("No XML files found in the zip archive.", file=sys.stderr)
        return False

    if failures:
        print(f"Completed with {failures} file(s) failing in archive '{input_path.name}'.", file=sys.stderr)
        return False

    return True


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Reorder PAGE or ALTO XML files using RTL vertical reading heuristics."
    )
    parser.add_argument("input", type=Path, help="Input XML file or directory")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Output file or directory. Required for directory input unless --inplace is set.",
    )
    parser.add_argument("--inplace", action="store_true", help="Overwrite the input file(s) in place.")
    args = parser.parse_args()

    if not args.input.exists():
        parser.error(f"Input path '{args.input}' does not exist")

    if args.input.is_file() and args.input.suffix.lower() == ".zip":
        if args.inplace and args.output:
            parser.error("Specify either --inplace or --output for zip processing, not both.")

        output_zip = args.output
        if not args.inplace:
            if output_zip is None:
                parser.error("Output zip path is required when not using --inplace with a zip archive")
            if output_zip.exists() and output_zip.is_dir():
                parser.error("Output path must be a zip file, not a directory")

        try:
            success = process_zip(args.input, output_zip, args.inplace)
        except ValueError as exc:
            parser.error(str(exc))
        return 0 if success else 1

    if args.input.is_dir():
        if not args.inplace and not args.output:
            parser.error("For directory input, specify --inplace or provide --output directory")

        output_dir = None
        if not args.inplace:
            output_dir = args.output
            if output_dir is None:
                parser.error("Output directory is required when not using --inplace")
            output_dir.mkdir(parents=True, exist_ok=True)

        failures = 0
        handled_xml = False
        for path in sorted(args.input.rglob("*")):
            if path.is_dir():
                continue
            relative = path.relative_to(args.input)
            if path.suffix.lower() == ".xml":
                handled_xml = True
                destination = None if args.inplace else output_dir / relative  # type: ignore[arg-type]
                if not process_file(path, destination, args.inplace):
                    failures += 1
            else:
                if not args.inplace and output_dir is not None:
                    dest = output_dir / relative
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(path, dest)

        if not handled_xml:
            print("No XML files found in the input directory.", file=sys.stderr)
            return 1

        if failures:
            print(f"Completed with {failures} file(s) failing.", file=sys.stderr)
            return 1
        return 0

    if args.inplace and args.output:
        parser.error("Specify either --inplace or --output for single-file processing, not both.")

    output_path = args.output
    if output_path and output_path.is_dir():
        output_path = output_path / args.input.name

    if not process_file(args.input, output_path, args.inplace):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

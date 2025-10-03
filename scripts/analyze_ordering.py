#!/usr/bin/env python3
"""Analyse PAGE/ALTO datasets to extract reading-order heuristics.

This helper walks through a directory or zip archive, parses each XML page, and
prints summary statistics (median heights/widths, tag counts, etc.). Optionally
write the result to CSV.  Use it on your "ground-truth" ordering to refine the
sorting algorithm.
"""
from __future__ import annotations

import argparse
import csv
import statistics
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional
import zipfile

DEFAULT_PAGE_XML_NS = "http://schema.primaresearch.org/PAGE/gts/pagecontent/2013-07-15"
SKIP_FILENAMES = {"mets.xml"}


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


def determine_format(root: ET.Element) -> Optional[str]:
    ns = extract_namespace(root.tag) or ""
    lname = local_name(root.tag).lower()
    if "pagecontent" in ns or lname == "pcgts":
        return "page"
    if "alto" in ns or lname == "alto":
        return "alto"
    return None


@dataclass
class LineSample:
    tag: str
    width: float
    height: float
    center_x: float
    min_y: float
    max_y: float


def parse_page_lines(root: ET.Element, ns: str) -> List[LineSample]:
    lines: List[LineSample] = []
    textline_tag = f"{{{ns}}}TextLine"
    coords_tag = f"{{{ns}}}Coords"
    for region in root.findall(f".//{{{ns}}}TextRegion"):
        for line in region.findall(textline_tag):
            coords = line.find(coords_tag)
            if coords is None or not coords.get("points"):
                continue
            pts = []
            for pair in coords.get("points", "").split():
                if "," not in pair:
                    continue
                try:
                    x_str, y_str = pair.split(",", 1)
                    pts.append((float(x_str), float(y_str)))
                except ValueError:
                    continue
            if not pts:
                continue
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            min_x, max_x = min(xs), max(xs)
            min_y, max_y = min(ys), max(ys)
            lines.append(
                LineSample(
                    tag="none",
                    width=max_x - min_x,
                    height=max_y - min_y,
                    center_x=(min_x + max_x) / 2.0,
                    min_y=min_y,
                    max_y=max_y,
                )
            )
    return lines


def build_alto_tag_map(root: ET.Element, ns: Optional[str]) -> dict[str, str]:
    tag_map: dict[str, str] = {}
    other_tag = f"{{{ns}}}OtherTag" if ns else "OtherTag"
    for tag in root.findall(f".//{other_tag}"):
        tag_id = tag.get("ID")
        label = tag.get("LABEL")
        if tag_id and label:
            tag_map[tag_id] = label.lower()
    return tag_map


def parse_alto_lines(root: ET.Element, ns: Optional[str]) -> List[LineSample]:
    tag_map = build_alto_tag_map(root, ns)
    textblock_tag = f"{{{ns}}}TextBlock" if ns else "TextBlock"
    textline_tag = f"{{{ns}}}TextLine" if ns else "TextLine"
    for_block: List[LineSample] = []
    for block in root.findall(f".//{textblock_tag}"):
        for line in block.findall(textline_tag):
            attr = line.attrib
            try:
                hpos = float(attr.get("HPOS"))
                vpos = float(attr.get("VPOS"))
                width = float(attr.get("WIDTH"))
                height = float(attr.get("HEIGHT"))
            except (TypeError, ValueError):
                continue
            tag_label = "none"
            for tag_id in attr.get("TAGREFS", "").split():
                mapped = tag_map.get(tag_id)
                if mapped:
                    tag_label = mapped
                    break
            for_block.append(
                LineSample(
                    tag=tag_label,
                    width=width,
                    height=height,
                    center_x=hpos + width / 2.0,
                    min_y=vpos,
                    max_y=vpos + height,
                )
            )
    return for_block


def load_lines(path: Path) -> List[LineSample]:
    tree = ET.parse(path)
    root = tree.getroot()
    doc_type = determine_format(root)
    if doc_type == "page":
        ns = extract_namespace(root.tag) or DEFAULT_PAGE_XML_NS
        return parse_page_lines(root, ns)
    if doc_type == "alto":
        ns = extract_namespace(root.tag)
        return parse_alto_lines(root, ns)
    raise ValueError(f"Unsupported XML document format in '{path}'")


def load_lines_from_bytes(data: bytes, filename: str) -> List[LineSample]:
    root = ET.fromstring(data)
    doc_type = determine_format(root)
    if doc_type == "page":
        ns = extract_namespace(root.tag) or DEFAULT_PAGE_XML_NS
        return parse_page_lines(root, ns)
    if doc_type == "alto":
        ns = extract_namespace(root.tag)
        return parse_alto_lines(root, ns)
    raise ValueError(f"Unsupported XML document format in '{filename}'")


def summarise(lines: List[LineSample]) -> dict:
    widths = [line.width for line in lines]
    heights = [line.height for line in lines]
    centers = sorted((line.center_x for line in lines), reverse=True)
    center_gaps = [centers[i] - centers[i + 1] for i in range(len(centers) - 1)]
    tags = [line.tag for line in lines]

    summary = {
        "count": len(lines),
        "count_default": tags.count("default"),
        "count_doubleline": tags.count("doubleline"),
        "count_none": tags.count("none"),
        "median_height": statistics.median(heights) if heights else 0.0,
        "median_width": statistics.median(widths) if widths else 0.0,
        "median_center_gap": statistics.median(center_gaps) if center_gaps else 0.0,
        "short_ratio": 0.0,
    }
    if heights:
        median_height = summary["median_height"]
        short = [h for h in heights if h <= median_height * 0.5]
        summary["short_ratio"] = len(short) / len(heights)

    first_tags = ",".join(tags[:6]) if tags else ""
    summary["first_tags"] = first_tags
    return summary


def iter_xml_files(path: Path) -> Iterable[Path]:
    if path.is_file():
        yield path
    else:
        yield from path.rglob("*.xml")


def analyse_directory(path: Path) -> List[tuple[str, dict]]:
    results = []
    for file_path in iter_xml_files(path):
        if file_path.name.lower() in SKIP_FILENAMES:
            continue
        try:
            lines = load_lines(file_path)
        except Exception as exc:  # pylint: disable=broad-except
            print(f"Skipping '{file_path}': {exc}")
            continue
        summary = summarise(lines)
        results.append((str(file_path), summary))
    return results


def analyse_zip(path: Path) -> List[tuple[str, dict]]:
    results = []
    with zipfile.ZipFile(path, "r") as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            if not info.filename.lower().endswith(".xml"):
                continue
            if Path(info.filename).name.lower() in SKIP_FILENAMES:
                continue
            try:
                data = zf.read(info.filename)
                lines = load_lines_from_bytes(data, info.filename)
            except Exception as exc:  # pylint: disable=broad-except
                print(f"Skipping '{info.filename}' in zip: {exc}")
                continue
            summary = summarise(lines)
            results.append((info.filename, summary))
    return results


def print_results(rows: List[tuple[str, dict]]) -> None:
    headers = [
        "file",
        "count",
        "count_default",
        "count_doubleline",
        "count_none",
        "median_height",
        "median_width",
        "median_center_gap",
        "short_ratio",
        "first_tags",
    ]
    print("\t".join(headers))
    for filename, summary in rows:
        print(
            "\t".join(
                [
                    filename,
                    str(summary["count"]),
                    str(summary["count_default"]),
                    str(summary["count_doubleline"]),
                    str(summary["count_none"]),
                    f"{summary['median_height']:.2f}",
                    f"{summary['median_width']:.2f}",
                    f"{summary['median_center_gap']:.2f}",
                    f"{summary['short_ratio']:.3f}",
                    summary["first_tags"],
                ]
            )
        )


def write_csv(rows: List[tuple[str, dict]], destination: Path) -> None:
    headers = [
        "file",
        "count",
        "count_default",
        "count_doubleline",
        "count_none",
        "median_height",
        "median_width",
        "median_center_gap",
        "short_ratio",
        "first_tags",
    ]
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        for filename, summary in rows:
            writer.writerow(
                [
                    filename,
                    summary["count"],
                    summary["count_default"],
                    summary["count_doubleline"],
                    summary["count_none"],
                    f"{summary['median_height']:.2f}",
                    f"{summary['median_width']:.2f}",
                    f"{summary['median_center_gap']:.2f}",
                    f"{summary['short_ratio']:.3f}",
                    summary["first_tags"],
                ]
            )


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyse PAGE/ALTO documents for reading-order heuristics.")
    parser.add_argument("input", type=Path, help="Input XML file/directory or zip archive")
    parser.add_argument("--csv", type=Path, help="Optional CSV output path")
    args = parser.parse_args()

    if not args.input.exists():
        parser.error(f"Input '{args.input}' does not exist")

    if args.input.is_file() and args.input.suffix.lower() == ".zip":
        rows = analyse_zip(args.input)
    else:
        rows = analyse_directory(args.input)

    if not rows:
        print("No XML files processed.")
        return 1

    print_results(rows)
    if args.csv:
        args.csv.parent.mkdir(parents=True, exist_ok=True)
        write_csv(rows, args.csv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

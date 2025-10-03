# Reading Order Sorting Tool / 阅读顺序整理工具

This utility reorders `TextLine` elements inside ALTO or PAGE XML so the stored
sequence matches the intended reading order (right-to-left columns, top-to-bottom
within a column). It was tuned on mixed single-line and double-line layouts such
as *正德琼台志*.

这个工具会重新排列 ALTO/PAGE XML 中的 `TextLine` 节点，使其与版面阅读顺序一致（列内自上而下、列与列之间自右向左）。算法针对《正德琼台志》中单行、双行交错的版式进行了调优。

## Usage / 使用方法

### Single XML page / 单个 XML 页面

```bash
python3 scripts/reorder_page_xml.py path/to/page.xml --ensure-namespace
```

- EN: In-place rewrite; add `-o output.xml` to write elsewhere. Existing
  whitespace is preserved unless `--indent` is supplied.
- 中文：默认原地覆盖，使用 `-o output.xml` 可输出到新文件。不加 `--indent`
  时保留原有空白格式。

### Zip archive / 批量处理 ZIP 压缩包

```bash
python3 scripts/reorder_page_xml.py batch.zip --ensure-namespace -o batch_sorted.zip
```

- EN: Every XML entry whose extension matches `.xml/.alto/.page` (or custom
  `--extensions`) is reordered; other files are copied unchanged.
- 中文：压缩包内所有扩展名为 `.xml/.alto/.page`（或通过 `--extensions`
  指定的扩展名）的文件都会被顺序整理，其他附件保持原样。

### Common flags / 常用参数

- `--ensure-namespace` – EN: inject default ALTO namespace when missing. 中文：
  如果页面缺省默认命名空间，则补写 `xmlns="http://www.loc.gov/standards/alto/ns-v4#"`。
- `--indent` – EN: pretty-print with two-space indentation. 中文：重新缩进输出，便于
  人工阅读。
- `--extensions .xml .alto` – EN/中文：指定 ZIP 内需要处理的额外扩展名。

## Algorithm Overview / 算法概述

1. **TextLine extraction / 行元素提取** – EN: gather each `TextLine` within its
   `TextBlock` and compute averages from `BASELINE`, `HPOS`, `VPOS`, `WIDTH`, and
   polygon coordinates. 中文：遍历每个 `TextBlock` 的 `TextLine`，从基线、位置和
   多边形坐标计算平均水平位置、最小垂直位置、宽度等指标。
2. **Initial column grouping / 初始列分组** – EN: group lines whose x-average is
   within ±60 px to form columns from right to left. 中文：按照平均水平位置每 60 像素
   聚合，识别自右向左排列的列群。
3. **Double-line merging / 双行合并判定** – EN: neighbouring groups merge when the
   top lines form a double-line (vertical gap ≤40 px, horizontal gap 50–200 px,
   widths typical of short lines). Header-specific checks compare baseline
   position to polygon extents to catch mask bleed. 中文：若相邻列顶端两行满足
   垂直差 ≤40 像素、水平差 50–200 像素且宽度接近短行，同时基线相对多边形的位置
   显示为页眉掩膜，判定为同一双行并合并列群。
4. **Within-column ordering / 列内排序** – EN: lines primarily sorted by `VPOS`
   (top to bottom). When two lines share height (≤25 px difference), order them
   right-to-left so the right fragment of a double-line is read first. 中文：列内按
   `VPOS` 从上到下排序；若高度相差不超过 25 像素，则按水平位置自右向左读出双行。
5. **Rewrite / 写回** – EN: only the order of `TextLine` nodes inside their
   parent `TextBlock` changes; everything else stays untouched. 中文：仅调整
   `TextBlock` 下 `TextLine` 的顺序，其他 XML 结构不改动。

## Tuning Heuristics / 阈值调整

All thresholds (e.g. `HORIZONTAL_GROUP_THRESHOLD`, `DOUBLE_LINE_VPOS_THRESHOLD`)
live near the top of `scripts/reorder_page_xml.py`. Modify them if your material
uses very different spacing.

所有阈值（如 `HORIZONTAL_GROUP_THRESHOLD`、`DOUBLE_LINE_VPOS_THRESHOLD`）集中在脚本开头。
若排版差异较大，可按需调整。

## Batch Tips / 批量处理建议

- EN: Always keep a backup or route output to a new folder when tuning values.
  Combine with `find`/`xargs` for large corpora if you prefer processing files
  individually. 中文：调整参数时请先备份或输出到新目录；若想逐个文件处理，也可以
  搭配 `find`/`xargs` 执行。

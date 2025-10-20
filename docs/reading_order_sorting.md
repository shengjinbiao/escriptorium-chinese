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

问题：

排序算法开关，script如果是Hand（Traditional Variant）我把文档改成l2r，排序就用老算法，排序是混乱的。改回去r2l，会启用新算法，排序是正确的。其实如果从左到右，只有横排，如果从右到左，只有竖排。这一点以前没有注意到。read direction会影响document里面图片的排序，一个是从左到右1页递增，另一个是从右到左递增。text panel一个靠左，另一个靠右。靠右的话，加上标点以后，标点的位置在屏幕上的显示有时候是错误的，比如这一句：“散三策文燦亦不用，瑞枏自爲檄諭獻忠。獻忠特文燦庇，” 最右面的逗号会跑到最左边来。光标的移动也跟平时使用电脑的习惯不同。键盘右箭头移动光标其实是向左移动，键盘的左箭头向右移动光标。键盘的上下箭头移动跟平时的习惯是相同的。然而，r2l一直往一个方向移动光标，到结尾会先跑回去结尾再移动到上一行或者下一行。

所有的Han排版变体中，只有Han(Hanzi, kanji, hanja)vertical 是从上到下排字符，似乎是日本现有少数排版方式设计的。中国不管大陆，台湾，香港这些地区，繁体字从左到右读，使用横排，r2l其实是从上到下读然后换行从右到左。翻页的话l2r肯定是横排从左到右翻页，而r2l肯定是竖排从右到左翻页。

Han(Hanzi, kanji, hanja) vertical 还有一个奇怪的地方，基线的顶端不是在顶部，而是在底部，编号也在底部显示，长方形的屏幕，底部没有完全显示，需要滚动条下拉才能看见。


现象原因

浏览器在 writing-mode: vertical-rl 下会以“右→左列、下→上基线”来布置 inline 内容。再叠加我们当前的容器布局（多半是 flex 或 absolute 定位），导致行号/基线靠下，并且文本块整体从底部开始渲染——这与我们想要的顶部对齐冲突。
修正建议

为竖排模式的容器显式设置 writing-mode: vertical-rl 但同时加 text-orientation: mixed、align-content:flex-start/justify-content:flex-start（若用 flex），并用 display:inline-block 或 position:relative 配合 top:0 保证从上边缘开始。
行号和 bounding box 若是绝对定位，需要改成相对竖排坐标的定位（例如使用 top/right 而不是 bottom）。可以把它们放在一个相对定位的 wrapper 内，让它也服从 writing-mode。
如果仍出现“基线在底部”的情况，可尝试在文本节点外包裹一个标准 LTR 容器，将 writing-mode 套在更高层，让内容从顶部开始；或给文本容器加 padding-top 抵消浏览器默认的 baseline 补偿。
另外，编号组件可在竖排模式下切换到专用布局（例如 CSS Grid），避免继承横排定位参数。
这样可以让 Han vertical 的文本块从屏幕顶部出现，行号也不再跑到底部，滚动条只用于真正超出屏幕的内容。


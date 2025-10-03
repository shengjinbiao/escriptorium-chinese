# Utility Scripts

## sort_pagexml_basic.py

`sort_pagexml_basic.py` 保留了最初的行排序脚本，只按“列→行→右到左”排序，便于
快速对比或回滚到第一版逻辑。

## Understanding and Fixing Line Ordering in eScriptorium

Digitising historical Chinese sources often exposes weaknesses in the default
line-order logic: mixed single and double columns, embedded vertical pairs, and
nested annotations confuse a pipeline that assumes left-to-right sequences.
During this investigation we traced how eScriptorium decides reading order and
built an external XML post-processor to restore right-to-left, top-to-bottom
layouts before re-importing data for proofreading.

### Where the Core Application Handles Ordering
- `app/apps/core/models.py` — `DocumentPart.recalculate_ordering` is the central
  routine. It clusters lines by geometry (columns by X, rows by Y) and writes
  back sequential `line.order` values, with a fallback `enforce_line_order` that
  normalises stored integers.
- `app/apps/api/serializers.py` — `LineOrderListSerializer` validates drag/drop
  requests from the UI, sorts them by the requested order, and calls the model
  helpers so the database remains consistent.
- `app/apps/api/views.py` — viewset actions like `recalculate_ordering` and
  `lines/move` expose the ordering APIs that the front-end consumes.
- `front/src/editor/store/lines.js` — Vuex mutations/actions keep the editor’s
  state aligned with the server by sorting the line array client-side after
  each response.
- `front/src/baseline.editor.js` — legacy baseline tooling still sorts selected
  lines left-to-right before merging, showing how geometry had been handled in
  older workflows.

Together these files explain the default behaviour: the backend relies on
geometric heuristics and per-line order integers, while the frontend expects
already-sorted arrays when rendering.

### Our XML Sorting Strategy
The new `scripts/sort_pagexml.py` script operates on exported PAGE or ALTO XML
and mirrors the backend logic with tweaks for right-to-left reading:
1. **Column clustering** — group lines by X centre using a median-based
   threshold, then sort columns from right to left.
2. **Row banding** — within each column, band lines by overlapping Y ranges,
   attach `default` notes to their nearest (usually right-hand) `DoubleLine`
   neighbours, then visit the resulting sequence from right to left.
3. **Linearisation** — flatten the column/row tree to a single order, update the
   physical `<TextLine>` sequence under their parent block/region, and refresh
   stored ordering metadata: `readingOrder {index:…;}` for PAGE, `READING_ORDER`
   attributes for ALTO.
4. **Batch processing** — optional directory mode walks every `.xml` file and
   reproduces the directory structure under a new output root, enabling quick
   re-import into eScriptorium.

These heuristics require only the coordinates already present in exported XML,
so they can be applied offline without touching the database.

### CLI Usage
```bash
# Single file → new file
python3 scripts/sort_pagexml.py input.xml -o sorted.xml

# Overwrite one file in place
python3 scripts/sort_pagexml.py input.xml --inplace

# Process an entire export directory into a mirror tree
python3 scripts/sort_pagexml.py exported_xml/ -o reordered_xml/

# Batch overwrite in place (be sure to keep a backup)
python3 scripts/sort_pagexml.py exported_xml/ --inplace
```

After running, inspect a few reordered files to ensure `readingOrder index`
values (PAGE) or `READING_ORDER` attributes (ALTO) increment correctly before
uploading the XML back into eScriptorium for manual review.

Metadata wrappers such as `METS.xml` and non-XML assets (PNG images, OCR logs,
etc.) are copied straight through so the export bundle stays importable.

---

## eScriptorium 行排序问题与解决思路

在处理传统汉文文献时，eScriptorium 的默认行排序往往会失败：单、双栏混排，
以及嵌套的双行结构都会导致阅读顺序错乱。本节总结了代码排查的关键位置，并
记录了我们编写的 XML 排序脚本如何修复这些问题。

### 核心源码中的排序实现
- `app/apps/core/models.py` — `DocumentPart.recalculate_ordering` 负责按几何信息
  重排行，并写入顺序整数；`enforce_line_order` 则用于最后的顺序归一化。
- `app/apps/api/serializers.py` — `LineOrderListSerializer` 校验前端拖拽提交的
  行顺序，排序后调用模型层，保证数据库数据合法。
- `app/apps/api/views.py` — `recalculate_ordering`、`lines/move` 等接口暴露了排
  序相关的 API，供前端调用。
- `front/src/editor/store/lines.js` — Vuex 模块在收到后端响应后重新根据 `order`
  排序，以保证编辑界面中的行列表与服务器一致。
- `front/src/baseline.editor.js` — 旧版基线编辑器在合并行之前也会按 X 坐标
  左右排序，展示了几何排序逻辑的历史沿革。

这些模块共同决定了默认行为：后端使用几何启发式生成 `order`，前端假设数据
已经按顺序返回。

### XML 排序脚本的算法
`scripts/sort_pagexml.py` 可处理 PAGE 和 ALTO 导出文件，其核心步骤为：
1. **列聚类**：按行的 X 中心点聚类，得到右到左的列序。
2. **行分组**：在每一列中按 Y 范围聚类，将 `default` 标签的标注吸附到最近
   （通常是右侧）的 `DoubleLine` 正文行之前，再整体按右到左遍历，可兼容双栏
   或嵌套结构。
3. **顺序展开**：将列/行结构展平成一维序列，调整 `<TextLine>` 的实际顺序，
   并刷新 `readingOrder {index:…;}`（PAGE）或 `READING_ORDER` 属性（ALTO）。
4. **批量处理**：目录模式会遍历所有 `.xml` 文件，保持目录结构输出到新目录，
   便于重新导入校对。

算法只依赖导出文件中已有的坐标信息，可在不修改数据库的情况下离线运行。

### 命令行用法示例
```bash
# 单个文件输出到新文件
python3 scripts/sort_pagexml.py 输入.xml -o 排序后.xml

# 直接覆盖单个文件
python3 scripts/sort_pagexml.py 输入.xml --inplace

# 将整个导出目录排序并拷贝到新目录
python3 scripts/sort_pagexml.py 导出目录/ -o 排序目录/

# 批量就地覆盖（请先做好备份）
python3 scripts/sort_pagexml.py 导出目录/ --inplace
```

脚本会自动跳过 `METS.xml` 等清单文件；若指定了输出目录，会直接复制这些
文件以及 PNG 图像等其它附件，以便重新导入时保持完整的包结构。

排序完成后，建议抽样查看 PAGE 文件中的 `readingOrder index` 或 ALTO 文件中
的 `READING_ORDER` 是否从 0 开始递增，再将结果导入 eScriptorium 进行人工
核对。

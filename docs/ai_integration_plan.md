# eScriptorium × yjxz AI 能力整合计划

## 1. 背景与目标
- **现状**：eScriptorium 负责项目（Project）→文档（Document）→页面（DocumentPart/Element）→行（Line）的图文处理；yjxz 项目已实现断句、翻译、实体等 AI 服务。
- **整合目标**：在 eScriptorium 内直接调用 yjxz 的 AI 能力，让校对人员在原有工作流里完成标点断句、现代汉语翻译以及后续的导读、提要、知识抽取等任务。
- **优先级策略**：先完成对用户价值最高、技术改动相对集中的页面级断句/翻译，再逐步向更大范围（整篇、整项目、跨项目）和更深的知识层级扩展。

## 2. 第一阶段（当前实施）：页面级断句与翻译

### 2.1 功能范围
- 用户在页面列表中选择一组页面（例如第 5 页到第 15 页）。
- 系统读取这些页面的手工或 OCR 转录文本，调用 AI 生成标点断句和现代汉语翻译。
- 结果拆分回页面级转录层，保留原始文本以便对比；可导出合并文本用于外部复核。

### 2.2 具体任务
1. **依赖与配置**
   - 在 eScriptorium 虚拟环境中安装 `wz-gazetteer` 包或通过 `pip install -e` 方式加载。
   - 将 `config/providers.yml` 与 OpenAI、spaCy 推理服务等凭据或配置项纳入 eScriptorium 设置（建议放置于 `BASE_DIR / config/`，由环境变量注入）。
   - 为 AI 缓存指定新的持久路径（如 `MEDIA_ROOT / "ai_cache"`），确保权限与备份策略。
2. **后端开发**
   - 在 Django 中新增服务封装（例如 `apps/core/services/ai_text.py`），复用 `PunctuationService` 与 `TranslationService`。
   - 在 `DocumentPart` 对应的 ViewSet 添加批处理 action，支持一次传入多个页面 ID：
      - 聚合页面文本 → 调用 AI → 将结果按页面拆分 → 使用 `LineTranscription` bulk API 写入新的转录层（如 “AI 断句”、“AI 翻译”）。
      - 标点结果在写入前与原始字符逐一对齐，只注入新增标点，避免破坏手工转录的字数和排序。
   - 使用 Celery 异步处理，返回任务 ID，避免大文本阻塞请求。
   - 断句请求自动携带相邻页面的参考行；单页调用时拉取上一页/下一页首尾行，多页调用时仅在队列首尾补充上下文，模型据此理解语境但仍仅写入目标页结果。
   - 翻译保持整页一次性请求，以保留上下文；若模型返回结构化 JSON，则直接按行写回，否则根据原文每行字符权重与中文标点进行比例切分，保证所有行都有译文且字符数与原行大致匹配。
   - 与 `wz-gazetteer` 旧版兼容：若后端尚不支持上下文参数，则自动回退到无上下文调用，确保部署阶段不需要同步升级。
3. **前端集成**
   - 在页面选择界面的 “AI Tools” 操作面板中提供 “标点断句”、“现代译文”、“生成语义向量” 三个动作，后者触发段落抽取与向量索引任务，支持以 Document/Project 为单位发起。未来切换到本地模型，只需在服务层把调用 OpenAI 的部分替换成本地推理；如果要自动化，可以让导入流程在完成后自动排队同一 Celery 任务，实现“导入即建索引”。
   - 调用新 API 后显示进度、状态反馈（借用现有 Toast/任务面板组件），任务完成后刷新相关转录层。
   - 支持并排对比（原始 vs AI）以及导出整段翻译文本。
4. **权限与审计**
   - 遵循与手工转录相同的权限模型，仅对具有编辑权的用户开放。
   - 记录触发者与时间，便于成本追踪与流程审计。
5. **验证与上线**
   - 在测试数据集上进行断句/翻译的准确性抽检。
   - 设计失败情况下的回退策略（保留原文、不覆盖）。
   - 编写操作文档并培训用户。

## 3. 第二阶段：整篇与整项目批量处理
- **整篇文档**：在 Document 仪表盘提供“一键断句/翻译整篇”，对所有页面排队处理，并生成新的转录层。
- **项目批量**：允许在 Project 级别选中多个 Document，组合 Celery 批次任务统一处理。
- **跨项目扩展**（如温州各县志的组合分析）：提供批量调度入口或脚本，以指定项目集合运行同一流程。

## 4. 第三阶段：导读、提要与深度研究支持
- **导读/提要生成**：在页面或文档级别调用摘要模型，生成导读、提要、关键词列表；存为附件或新的元数据字段。
- **主题聚类与专题分析**：根据整篇断句/翻译文本进行主题模型、时间线梳理，为深度研究提供可视化分析入口。
- **版本比较**：利用多层转录对比 AI 版本与人工校对，评估自动化质量。

## 5. 第四阶段：命名实体、知识库与知识图谱

### 5.1 目标与闭环定位
- 在“大闭环”流程（图像分割→OCR→人工校对→标点翻译→段落结构化→语义检索/问答）的末端补齐“实体→知识库→知识图谱”能力，使产出的结构化知识反哺前端检索、专题研究与可视化。
- 建立“小闭环”抽取循环：自动识别实体/关系→人工审核→知识库入库→模型反馈训练，实现持续提质与规模化。

### 5.2 数据资产盘点与空缺
- 以《光绪永嘉县志》目录（如“舆地志”“建置志”“人物志”等门类）为纲，梳理现有卷/章/段落、版面坐标、人工标注等基础数据。
- 统计已有词表、Gazetteer、年号与公历对照、地名标准化成果，记录缺失部分，为后续规范库建设提供任务清单。
- 制作“知识建模需求表”，列出每类实体的属性、来源字段、预期应用（检索、可视化、问答）。

### 5.3 本体与规范库设计
- 以总目门类建立顶层 schema：如“舆地志”涵盖地理单元/空间关系，“人物志”聚焦人物生平事件，“列女志”记录性别特定的事迹，“庶政志”梳理制度与设施。
- 对重点实体（年号、公历纪年、地名、人物、灾害、起义等）设计属性与关系模板，明确必填字段、别名、时间/空间约束。
- 建立公共规范库（Authority Files）：年号↔公历对照表、地名字典、官职体系、事件分类；提供唯一 ID，供所有门类复用与跨文献链接。

### 5.4 抽取流程与人机协同
- 组建多源实体抽取流水线：以 spaCy NER 管线为核心，叠加词典/规则匹配与必要的 LLM 复核，针对年号识别、地名结尾词、官职模式等场景做自动校正。
- 在 eScriptorium 内新增实体审核界面，支持批量确认、合并、打回；记录出处（卷、页、段落、坐标）和审校人。
- 建立主动学习闭环：对高置信度样本自动入库，低置信度样本推送审核；审核结果反向标记训练集，利用 spaCy CLI 定期在 CPU 环境微调模型并滚动部署。

### 5.5 知识库与知识图谱落地
- **知识库层**：使用 PostgreSQL/JSONB 保存实体属性、版本、来源；在 Elasticsearch 建立实体索引支持别名检索；提供 REST/GraphQL API 供内部功能与外部合作调用。
- **图谱层**：规划节点/边类型（人物↔事件、事件↔地点、年号↔公历、制度↔设施）；评估 Neo4j 或 JanusGraph 作为分析存储，定期或实时从知识库增量同步。
- 设计前端展示：实体详情页、关系探索视图、时空地图/时间线，让研究者快捷浏览、导出和引用。

### 5.6 里程碑规划
1. **M1 — 建模基线**：完成知识建模需求表、规范库初版（年号、地名、人物字段），确定接口契约。
   - **需求梳理**：访谈业务方与标注团队，提取年号/地名/人物的字段清单、取值范围、数据来源、更新频率与使用场景，沉淀成统一需求表。
   - **模型设计**：输出概念/逻辑模型，定义实体、属性、枚举值、关联关系及质量规则，并确定字段命名与标准化策略。
   - **规范库落地**：整理县志原文与现有资料源，搭建清洗→去重→标准化→版本管理流程，产出可复用的基线数据集（支持县志专项字段）。
   - **接口契约**：界定服务边界，给出请求/响应结构、错误码、性能指标及鉴权方式，并起草 Swagger/OpenAPI 文档供开发联调。
   - **字段框架（永嘉縣志總目映射）**：以志书→卷→门类→条目四层结构搭建通用 schema，既保留县志特色又适配 9k+ 志书的抽取与对照需求；并对照现有资料表（温州古旧方志目录.xlsx、乾隆温州府志结构.xlsx、明清地名志数据表.xlsx）校准字段与枚举。

     | 层级 | 实体类型 | 核心字段 | 说明 |
     | --- | --- | --- | --- |
     | 志书 | `GazetteerWork` | `gazetteer_id`, `title`, `alt_titles[]`, `edition_year`, `dynasty`, `compiled_year_range`, `compilers[]`(ref 人物), `sponsor`, `volume_count`, `source_archive`, `collection_location`, `call_number`, `edition_note`, `text_source` | 对应《永嘉縣志》本体信息，结合馆藏目录表补充馆藏位置、索书号与版本备注。 |
     | 卷 | `GazetteerVolume` | `volume_number`, `volume_title`, `canonical_category`(枚举：輿地志、建置志、人物志等), `subheading`, `page_range`, `era_scope`, `notes`, `subject_terms[]`, `responsible_editors[]` | 映射卷一至卷三十八等，并引入结构化表中的主题词与责任者信息。 |
     | 门类/子目 | `GazetteerSection` | `section_id`, `section_title`, `parent_volume_id`, `section_type`(如沿革、敘山、義塾), `ordering`, `keywords`, `cross_refs[]`, `summary`, `topic_tags[]` | 对应“沿革”“人物志五 文苑”等目录节点，可保留摘录与主题标签。 |
     | 条目/正文 | `GazetteerEntry` | `entry_id`, `entry_title`, `entry_type`(人物/地名/制度/事件/文献等), `source_section_id`, `text_pointer`, `abstract`, `responsible_persons[]`, `related_entities[]`, `tags[]`, `quality_status`, `source_refs[]` | 对应人物传、地理描述、艺文条等，可细分为专用实体，并记录条目责任者与原文引用。 

     人物条目：`name`, `courtesy_name`, `aliases[]`, `gender`, `birth_year`, `death_year`, `origin_place_id`, `positions[]`, `works[]`, `related_events[]`, `biography_summary`, `source_volume`, `source_page_range`, `catalog_ref`。  
     地名条目：`place_name`, `standard_code`, `hierarchy_level`, `parent_place_id`, `location_type`, `latitude`, `longitude`, `boundary_east`, `boundary_west`, `boundary_south`, `boundary_north`, `neighboring_places[]`, `historical_changes`, `defense_installations[]`, `reference_sources[]`。  
     年号/时代条目：`era_name`, `dynasty`, `start_year`, `end_year`, `emperor`, `alternate_names[]`, `applicable_regions[]`, `source_refs[]`。  
     制度/事件条目：`system_name`, `category`(贡赋/武備/庶政等), `time_span`, `responsible_offices[]`, `impact_summary`, `policy_scope`, `related_documents[]`, `source_refs[]`。  
     文献条目：`document_title`, `author_id`, `document_type`(詩/奏議/祭文等), `creation_year`, `excerpt_pointer`, `original_source`, `tags[]`, `subject_terms[]`, `source_refs[]`。
   - **馆藏目录 PoC（基于三份 Excel）**：先把温州古旧方志目录、乾隆温州府志卷首结构、明清地名志数据导入 eScriptorium，验证数据层与最小界面。
     - 数据导入：编写脚本将 Excel → CSV/JSON → `library_catalog`/`gazetteer_structure`/`place_reference` 表，支持重复运行与去重。
       - 操作命令示例（Docker 部署）：  
         ```bash
         docker compose exec web python manage.py migrate knowledge
         docker compose exec web python manage.py import_catalog_data \
           --catalog /usr/src/app/docs/"Copy of 温州古旧方志目录.xlsx" \
           --structure /usr/src/app/docs/"Copy of (乾隆)溫州府志三十卷首一卷_1.xlsx" \
           --places /usr/src/app/docs/"Copy of 明清地名志数据表.xlsx"
         ```
     - 后端 API：在 `knowledge` 模块暴露列表/搜索接口（分页、关键字、来源过滤），必要时对接 Elasticsearch 做全文检索。
     - 前端展示：复用 eScriptorium 现有列表组件，增加“馆藏目录”入口；短期可由 Django Admin 先行，确保用户可浏览与导出。
     - 交付物：导入脚本、数据库结构文档、API 示例、界面原型或截图。
   - **资料映射与字段验证**：以上字段初稿需对照三份 Excel 表逐列校验，沉淀成《字段字典 v0.1》，说明每列与原始资料的映射关系（是否必填/可选、枚举来源、转换规则），并在 M1 内完成首轮评审。
   - **评审验收**：召集业务、数据、研发团队对需求表、模型与接口进行评审，确认交付物与验收标准后进入开发迭代。
2. **M2 — 抽取试点**：选取《永嘉县志》若干卷跑通候选抽取→审核→入库流程，评估准确率与人工成本。
3. **M3 — 知识库服务化**：上线实体查询 API、别名检索、引用追溯；接入语义检索，将实体信息嵌入问答流程。
4. **M4 — 图谱原型**：搭建图数据库试验环境，展示人物-事件-地理关系，收集学者反馈。
5. **M5 — 闭环迭代**：引入主动学习、质量监控仪表板、版本管理与回滚；制定跨文献扩展计划。

> 注：本阶段侧重规划与原型验证，具体实施任务将在后续迭代拆解执行。

## 6. 运维与资源规划
- **计算与费用**：监控 OpenAI 调用与 spaCy 推理/训练任务的资源消耗，设置限流、队列与预估预算。
- **任务监控**：利用 Celery/Prometheus 指标跟踪任务成功率、平均用时。
- **权限控制**：为 AI 功能设置角色开关，可按项目或用户组启用。
- **可扩展性**：预留替换模型或增加第三方接口的配置结构，避免硬编码。

## 7. 里程碑建议
1. **M1（当前 Sprint）**：完成页面级断句/翻译的后端接口、前端按钮、结果写回与最小测试。
2. **M2**：扩展到整篇/整项目批处理，完善队列与导出工具。
3. **M3**：上线导读/提要与 NER，打通实体校对和知识库导出。
4. **M4**：构建知识图谱与跨项目研究支持，形成统一的研究门户。

## 8. 语义检索与问答增强（ES 8 × OpenAI）

### 8.1 目标
- 将地方志内容升级为“关键词 + 语义”双通道检索，支持自然语言提问。
- 搜索结果包含：OpenAI 生成的回答、引用出处、关键词匹配结果清单。
- 保留可溯源性，所有生成内容附带段落级证据链接。

### 8.2 技术路线
1. **Elasticsearch 升级**
   - Docker 镜像：`docker.elastic.co/elasticsearch/elasticsearch:8.x.y`，继续安装 `analysis-smartcn`。
   - Python 依赖：`elasticsearch>=8,<9` 与 `elastic-transport`；清理 7.x API（无 `_type`、替换 `body=` 调用）。
   - 集群配置：开启安全（TLS/用户），准备证书与运行凭证，评估节点内存/存储满足向量索引要求。
   - 数据迁移：在测试集群完成快照恢复→索引重建→验证，再滚动升级生产。
2. **索引设计**
   - 字段：`raw_content`/`context`（BM25）、`embedding` (`dense_vector`, HNSW)、`source` 元数据（书名、卷、页、URL）。
   - 管道：地方志段落切分→生成 OpenAI embedding（`text-embedding-3-large` 预设）→批量写入 ES 8 索引。
   - 混合检索：BM25 + 向量 KNN 并行，再用 RRF/加权融合。
3. **后端服务**
   - 新增 `apps/core/services/search_semantic.py`：封装查询流程、缓存 embedding、落地引用信息。
   - 调整 REST API：新增 `/api/search/semantic/`，返回 `{answer, citations[], keyword_hits[]}`。
   - 答案生成：采用 GPT-4o mini，对检索片段进行提示工程，强制引用格式 `[1]` 并回传证据 ID。
4. **前端 UI**
   - 搜索框支持自然语言，结果页上方展示回答+引用；下方是证据卡片与关键词列表。
   - 交互：点击引用定位证据，允许用户反馈“答案有用/有误”。
5. **运维与成本**
   - 嵌入生成走异步 Celery 任务，使用批量接口减少 OpenAI 调用成本。
   - 对热门问答做结果缓存，监控延迟与 API 费用；设置速率限制与告警。

### 8.3 实施步骤
1. **Sprint A — 基础升级与 PoC**
   - 任务包
     - 构建 ES 8.x 测试集群（Dockerfile、Compose、证书配置）。
     - 升级 Python 依赖，替换/适配 `index.py`、`search.py` API 调用；实现 7.x/8.x 双兼容或直接切换。
     - 准备迁移脚本：快照、索引重建、回滚方案。
     - 以小样本文档验证 BM25 搜索结果一致性。
   - 交付物：升级说明文档、测试记录、可运行的 ES 8 索引 PoC。
   - 前置条件：OpenAI 凭证可选（非必须）、测试环境资源到位。
2. **Sprint B — 向量索引与混合检索**
   - 任务包
     - 设计段落切分与 metadata 模型，编写嵌入生成 Celery 任务（OpenAI Embedding）。
     - 为 ES 索引新增 `dense_vector` 字段与 HNSW 设置；批量导入试点数据。
     - 实现混合检索服务（BM25+KNN）及结果融合策略；输出结构化证据。
     - 增加检索 API（返回候选片段、分数、metadata）。
     - 辅助工作：
       - 规范化数据切分：按“卷→章节→段落”落表，生成唯一 `passage_id`、原始文本、清洗文本、页码、链接。
       - 嵌入生成流水线：新增 `apps/core/services/embedding.py`（OpenAI 请求/重试/缓存）、Celery 任务 `generate_embeddings_for_passages`、批量 upsert。
       - ES 索引定义：`embedding` 字段类型 `dense_vector`（1536 维，`index: true`, `similarity: cosine`），设置 HNSW 参数（`m=16`, `ef_construction=128`）以及 `metadata` 字段（keyword）。
       - 混合检索策略：先并发执行 `BM25` + `knn` 查询 -> `reciprocal rank fusion` 融合，`topK`=50；按段落粒度返回。
       - API 设计：新建 `SearchSemanticViewSet` (`/api/search/semantic/`)；请求参数包含 `query`, `project/document` 过滤、`weights`；响应包含 `hits`（段落文本+metadata+BM25/KNN 分数）、`debug` 信息。
       - 成本控制：在 Celery 任务中加入批处理（例如 512 段落/批），并记录调用配额；配置 OpenAI API key、速率限制。
       - 测试计划：为嵌入生成、索引写入、混合检索编写单元测试；准备集成测试脚本比较召回质量与延迟。
   - 代码改动建议
     - `apps/core/services/embedding.py`: 统一封装 OpenAI Embedding、重试、缓存。
     - `apps/core/models.py`: 新增 `DocumentPassage` 模型/表（或利用现有结构扩展 metadata），配合管理命令生成段落。
     - `apps/core/management/commands/index_embeddings.py`: 用于一次性/增量生成向量并写入 ES。
     - `apps/core/search.py`: 拆分当前函数，添加 `semantic.py` 模块用于混合检索逻辑。
     - `apps/api/serializers.py` / `views.py`: 暴露新的搜索接口。
     - `celery.py` & `tasks.py`: 注册嵌入生成与索引刷新任务。
     - 配置：在 `settings.py` 添加 OpenAI API key、批处理大小、ES 索引名称等可配置项。
   - 验证与验收
     - 指标：向量导入成功率（>99%）、嵌入任务平均耗时、混合检索响应时间、召回质量（人工抽检或 MAP）。
     - 工具：`pytest` 单元测试、`pytest-django` 集成测试、命令行脚本比较 BM25 与混合检索差异。
   - 验收步骤：
      1. 在测试环境生成试点索引，确保 API 返回结构与 schema 符合预期。
      2. 通过前端或 Postman 发起查询，验证 top-k 结果中的引用与 metadata 正确。
      3. 监控 Celery 与 OpenAI 调用日志，确认速率/成本在预算内。
      4. 输出验收报告，记录成功案例、问题清单与下一阶段需求。
   - 短期待办（当前阶段）
     - 运行迁移，确认 `DocumentPassage` 表创建成功。
     - 编写段落抽取脚本，将现有文档抽样写入新模型。
     - 为 `generate_passage_embeddings_task` 添加最小化单元测试（验证空列表、常规列表返回值）。
     - 确认 Celery worker 能加载新的任务与服务模块。
   - 交付物：后端服务模块、Celery 任务、混合检索接口及单元/集成测试。
   - 前置条件：Sprint A 完成并通过回归；OpenAI API 凭证、速率/成本评估。
3. **Sprint C — 答案生成与前端体验**
   - 任务包
     - 集成 GPT-4o mini（或同档 LLM），设计 Prompt 和引用格式。
     - 构建答案生成服务层，加入缓存/失败回退；落盘引用映射。
     - 前端改版：自然语言搜索框、答案卡片、证据列表、关键词结果并行展示。
     - 用户反馈与埋点：满意度、引用点击、查询延迟。
   - 交付物：API 响应结构 v1、前端展示页、引用跳转和反馈交互。
   - 前置条件：Sprint B 接口稳定；前端设计稿/组件库更新同步。
4. **Sprint D — 灰度上线与调优**
   - 任务包
     - 选择试点项目上线，配置灰度开关与权限控制。
     - 监控指标：召回率、答案准确率、响应时延、OpenAI 成本。
     - 针对反馈优化检索权重、Prompt、缓存策略；完善报警与限流。
     - 规划规模化推广与与旧检索共存方案。
   - 交付物：上线运行报告、监控与告警仪表、优化清单与后续路线。
   - 前置条件：Sprint C 功能通过验收；运维监控管道就绪。

### 8.4 风险与对策
- **升级风险**：7→8 跨版本需停机窗口 → 先在影子环境完整跑通索引重建与回滚脚本。
- **成本控制**：OpenAI 调用按量计费 → 引入缓存/阈值预警，必要时准备开源 embedding 备选。
- **性能**：向量索引内存压力大 → 评估节点规格，必要时引入冷热分层或独立向量节点。
- **准确性**：生成答案需可追溯 → 强制引用输出，QA 脚本抽检回答质量。

---
通过上述阶段性推进，可以让 eScriptorium 在保持现有编辑体验的基础上，逐步引入 AI 增强功能，最终形成从 OCR、校对到深度研究的一体化工作平台。

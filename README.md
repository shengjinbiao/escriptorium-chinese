
# eScriptorium 中文汉化版介绍

eScriptorium 是 [Scripta](https://www.psl.eu/en/scripta)、[RESILIENCE](https://www.resilience-ri.eu) 和 [Biblissima+](https://projet.biblissima.fr/) 项目的一部分，并获得了巴黎文理大学（Université PSL）以及欧盟 [Horizon 2020 研究与创新计划](https://ec.europa.eu/programmes/horizon2020/en/what-horizon-2020)（资助协议编号：871127）、法国国家研究署（[Agence Nationale de Recherche](https://anr.fr/fr/france-2030/france-2030/)）“未来投资计划”（资助参考编号：ANR-21-ESRE-0005）等资助，以及其他下方列出的合作机构的支持。  
本项目旨在为人文研究者提供一个整合化的工具集合，用于识别、标注、翻译和发布历史文献。

eScriptorium 应用本身是整个系统的“核心”。该项目仍在开发中，已实现或计划实现的功能包括：通过 Kraken 进行自动转写、面向复杂搜索与筛选的索引、文献标注、以及如共享与版本管理等基本的协作功能。

[eScriptorium安装使用笔记](docs/eScriptorium-历史手稿数字化平台.md)
---


## 最新特性

- **2025-10-13 可复用转层**：新版“批量识别”对话框新增“Existing Layer”下拉框，可直接选择文档内已有的未归档转录层，避免重复输入复杂名称并让分批识别结果自动写入同一转录层。
- **2025-10-20 语义问答搜索**：在搜索页输入自然语言查询时，系统会并行执行关键词检索与向量检索，自动调用 OpenAI 生成可引用的答案，并展示语义匹配段落与分数。目前支持 `/api/search/semantic/` API 以及 Web UI 顶部的“AI Answer”“Semantic Matches”卡片。
- **竖排古籍复杂版面阅读顺序算法**：本版本新增了对繁体汉字、右起竖排页面的专用排序逻辑，可自动识别页眉掩模造成的宽行以及双列/双行混排，给出更符合原文习惯的阅读顺序。其他语言脚本或横排文稿仍沿用既有算法。
- **中文界面与提示信息**：补全前端中文本地化词条，主要操作提示、对话框与协作指引均可切换为中文显示，显著提升中文用户体验。这只在传统（Legacy）模式下有效。默认仓库里的 variables.env_example 只启用英文，所以要看到中文界面，需要在自己的 variables.env（运行环境变量）里加 ESC_LANGUAGES=en,cn手动开启，然后在界面右上角语言菜单中切换到中文。
- **Elasticsearch 中文分词优化**：Docker 现在内置并默认启用 Elastic 官方 `analysis-smartcn` 分词插件，`app/apps/core/management/commands/index.py` 也随之调整为使用中文分词器建索引，从而显著改善中文多音节词的匹配准确度。部署后请执行 `docker compose up -d --build elasticsearch` 重新构建 ES，再在 web 容器里跑 `python manage.py index --drop` 以重建索引。

---

### 语义问答快速启用

1. **安装依赖**  
   - 在 Docker 容器（`web`、`celery-main`、`celery-low-priority`、`celery-gpu`）内执行 `pip install -e /usr/src/yjxz` 与 `pip install faiss-cpu`。  
   - 确保环境变量 `OPENAI_API_KEY` 可用、`config/providers.yml` 中已配置 OpenAI 相关模型。

2. **准备索引数据**  
   ```bash
   docker compose exec web python manage.py generate_passages --reset
   # 批量生成段落向量（可在 shell 中调用 generate_embeddings_for_passages）
   docker compose exec web python manage.py index_semantic --drop
   ```

3. **使用方式**  
   - 在文档详情或图片列表的“AI Tools”面板中点击“生成语义向量”，即可自动执行段落抽取、向量生成和索引写入；支持针对单个 Document 或整个 Project 触发。  
   - 访问 Web 搜索页输入问题，界面会并行展示“AI Answer”“Semantic Matches”“Keyword Results”。答案卡片引用落在新建的语义索引，支持跳转至原文段落。  
   - 开发者可调用 `POST /api/documents/<id>/semantic/vectorize/` 或 `POST /api/projects/<id>/semantic/vectorize/` 生成索引，也可直接访问 `POST /api/search/semantic/`，请求体示例：`{"query": "永嘉县志记载的主要灾害？", "limit": 5, "with_answer": true}`。

4. **常见问题**  
   - 若提示缺少依赖，请确认上述 pip 安装步骤已在所有相关容器执行；使用自定义镜像时需包含 `faiss-cpu`、`wz-gazetteer` 等向量服务依赖。  
   - 若返回 400/503，可检查 Elasticsearch 索引是否重建成功、向量生成任务在 Celery 中是否完成，以及 OpenAI 凭证是否有效。  
   - 导入大量文档后建议重新触发“生成语义向量”，以保证新的段落已经纳入索引。

## 技术栈

- nginx
- uwsgi
- [django](https://www.djangoproject.com/)
- [daphne](https://github.com/django/daphne)（WebSocket 通道服务器）
- [celery](http://www.celeryproject.org/)
- postgres（PostgreSQL 数据库）
- [elasticsearch](https://www.elastic.co/)
- redis（用于缓存、celery 通信和其他临时数据）
- [kraken](http://kraken.re)（OCR 引擎）
- [docker](https://www.docker.com/)（部署环境）

---

## 安装方式

你有两个选择：

- [使用 Docker 安装](https://gitlab.com/scripta/escriptorium/-/wikis/docker-install)
- [完整本地安装（Full Install）](https://gitlab.com/scripta/escriptorium/-/wikis/full-install)

eScriptorium 可运行于 Linux、macOS 或 Windows（需启用 WSL）。

---

## 如何参与贡献

详见：[参与 eScriptorium 贡献指南](https://gitlab.com/scripta/escriptorium/-/wikis/contributing)

---

## 指导委员会成员

- Daniel Stoekl Ben Ezra（巴黎高等实践学院，UMR AOROC 8546）
- Peter Stokes（巴黎高等实践学院，UMR AOROC 8546）
- Benjamin Kiessling（巴黎高等实践学院，UMR AOROC 8546）
- Robin Tissot（巴黎高等实践学院，UMR AOROC 8546）
- Mathew Barber（阿迦汗大学，穆斯林文明研究所）
- David Smith（美国东北大学）
- Thibault Clérice（法国国家信息与自动化研究院 Inria）
- Hassen Aguili（法国国家信息与自动化研究院 Inria）

---

## 当前资金与技术支持机构包括：

- [巴黎高等实践学院（EPHE）](https://www.ephe.psl.eu)
- [Biblissima+ 项目](https://projet.biblissima.fr/)
- [RESILIENCE 欧洲研究基础设施](https://www.resilience-ri.eu)
- [巴黎文理大学 Scripta](https://scripta.psl.eu/en/)
- [法国国家信息与自动化研究院（Inria）](https://inria.fr/en)
- [法国国家档案馆](https://www.archives-nationales.culture.gouv.fr/)
- [法国文献与文献学研究所](https://www.irht.cnrs.fr/)
- [伊斯兰文献开放计划（OpenITI）](https://openiti.org/)
- [安德鲁·W·梅隆基金会](https://mellon.org/grants/)

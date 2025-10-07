
# eScriptorium 中文汉化版介绍

eScriptorium 是 [Scripta](https://www.psl.eu/en/scripta)、[RESILIENCE](https://www.resilience-ri.eu) 和 [Biblissima+](https://projet.biblissima.fr/) 项目的一部分，并获得了巴黎文理大学（Université PSL）以及欧盟 [Horizon 2020 研究与创新计划](https://ec.europa.eu/programmes/horizon2020/en/what-horizon-2020)（资助协议编号：871127）、法国国家研究署（[Agence Nationale de Recherche](https://anr.fr/fr/france-2030/france-2030/)）“未来投资计划”（资助参考编号：ANR-21-ESRE-0005）等资助，以及其他下方列出的合作机构的支持。  
本项目旨在为人文研究者提供一个整合化的工具集合，用于识别、标注、翻译和发布历史文献。

eScriptorium 应用本身是整个系统的“核心”。该项目仍在开发中，已实现或计划实现的功能包括：通过 Kraken 进行自动转写、面向复杂搜索与筛选的索引、文献标注、以及如共享与版本管理等基本的协作功能。

---


## 最新特性

- **竖排古籍复杂版面阅读顺序算法**：本版本新增了对繁体汉字、右起竖排页面的专用排序逻辑，可自动识别页眉掩模造成的宽行以及双列/双行混排，给出更符合原文习惯的阅读顺序。其他语言脚本或横排文稿仍沿用既有算法。
- **中文界面与提示信息**：补全前端中文本地化词条，主要操作提示、对话框与协作指引均可切换为中文显示，显著提升中文用户体验。这只在传统（Legacy）模式下有效。默认仓库里的 variables.env_example 只启用英文，所以要看到中文界面，需要在自己的 variables.env（运行环境变量）里加 ESC_LANGUAGES=en,cn手动开启，然后在界面右上角语言菜单中切换到中文。

---

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

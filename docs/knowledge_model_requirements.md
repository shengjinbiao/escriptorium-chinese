# 知识建模需求表（M1 基线）

本文件定义《永嘉县志》等样本在 M1 阶段需要交付的核心实体与字段，为后续抽取、导入与服务接口提供一致的 Schema 参考。

## 1. 年号（EraReference）

| 字段 | 类型 | 说明 | 是否必填 | 示例 |
| --- | --- | --- | --- | --- |
| `era_id` | string | 全局唯一标识，推荐 `era_<dynasty>_<start_year>` 命名 | ✅ | `era_ming_1368` |
| `era_name` | string | 年号中文名称 | ✅ | 洪武 |
| `dynasty` | string | 所属朝代 | ✅ | 明 |
| `emperor` | string | 采用该年号的皇帝 | ✅ | 朱元璋 |
| `start_year_ce` | integer | 公元起始年（含） | ✅ | 1368 |
| `end_year_ce` | integer | 公元结束年（含） | ✅ | 1398 |
| `start_year_cn` | string | 农历纪年起点描述 | ❌ | 洪武元年 |
| `end_year_cn` | string | 农历纪年终点描述 | ❌ | 洪武三十一年 |
| `applicable_regions` | string | 适用范围（全国/地区） | ❌ | 全国 |
| `source_refs` | string[] | 参考文献、链接 | ✅ | `["《明史·太祖本纪》", "中国历史纪年表"]` |
| `notes` | text | 备注（异名、换算注意事项等） | ❌ | 与“太祖高皇帝”并用 |

> 数据来源建议：中华书局《中国历史纪年表》、中央研究院年号数据库、Wikipedia “List of Chinese era names”等权威对照表。

## 2. 地名（PlaceReference）

| 字段 | 类型 | 说明 | 是否必填 | 示例 |
| --- | --- | --- | --- | --- |
| `place_id` | string | 全局唯一标识，建议 `place_<name>_<dynasty>` | ✅ | `place_yongjia_ming` |
| `standard_name` | string | 标准化地名 | ✅ | 永嘉县 |
| `dynasty` | string | 所属朝代或时期 | ✅ | 明 |
| `admin_level` | string | 行政层级（府/州/县等） | ✅ | 县 |
| `parent_place_id` | string | 上级行政区（可为空） | ❌ | `place_wenzhou_fu` |
| `alt_names` | string[] | 异名、别称 | ❌ | `["永嘉"]` |
| `start_year_ce` | integer | 设立或沿革起始年份 | ❌ | 1368 |
| `end_year_ce` | integer | 结束年份（若持续则留空） | ❌ | 1735 |
| `latitude` | decimal | 中心经纬度（度） | ❌ | 28.002 |
| `longitude` | decimal | 中心经纬度（度） | ❌ | 120.706 |
| `boundary_east` | decimal | 东界经度 | ❌ | 120.92 |
| `boundary_west` | decimal | 西界经度 | ❌ | 120.43 |
| `boundary_south` | decimal | 南界纬度 | ❌ | 27.78 |
| `boundary_north` | decimal | 北界纬度 | ❌ | 28.24 |
| `neighbors` | string[] | 四至邻接（含方向提示） | ❌ | `["东：乐清县", "西：青田县"]` |
| `jurisdiction` | string[] | 辖区下属乡镇或附属区域 | ❌ | `["七都", "上戍"]` |
| `evolution_notes` | text | 沿革说明 | ❌ | 雍正十三年析置瓯海县 |
| `source_refs` | string[] | 数据来源 | ✅ | `["明清地名志数据表", "《温州府志》"]` |
| `notes` | text | 备注（质量标记、疑义） | ❌ | 永嘉在明清属温州府 |

## 3. 人物（PersonReference）

| 字段 | 类型 | 说明 | 是否必填 | 示例 |
| --- | --- | --- | --- | --- |
| `person_id` | string | 全局唯一标识，建议 `person_<name>_<birth_year>` | ✅ | `person_huang_zongxi_1610` |
| `name` | string | 姓名 | ✅ | 黄宗羲 |
| `courtesy_name` | string | 字号 | ❌ | 太冲 |
| `aliases` | string[] | 别名、号 | ❌ | `["南雷"]` |
| `gender` | string | 性别（可用枚举） | ❌ | 男 |
| `dynasty` | string | 活跃朝代/时期 | ✅ | 明末清初 |
| `birth_year` | integer | 出生年份 | ❌ | 1610 |
| `death_year` | integer | 去世年份 | ❌ | 1695 |
| `origin_place_id` | string | 籍贯（关联 Place） | ❌ | `place_yongjia_ming` |
| `positions` | string[] | 官职、社会角色 | ❌ | `["南京国子监祭酒", "东林学者"]` |
| `works` | string[] | 代表著作 | ❌ | `["明儒学案"]` |
| `related_events` | string[] | 重大事件或参与活动 | ❌ | `["反清复明运动"]` |
| `biography_summary` | text | 简要传记 | ❌ | 永嘉学派领军人物 |
| `source_refs` | string[] | 参考文献/链接 | ✅ | `["《清史稿·儒林传》", "CTP"]` |
| `notes` | text | 备注（版本差异、校对情况） | ❌ | 需核对与地方志原文差异 |

## 4. 交付与校验

- **数据模板**：使用 CSV/JSON Schema 或 Django Fixture 形式，字段命名与上表保持一致，可附带示例行用于导入测试。仓库已提供 `docs/data/era_references_sample.csv` 与 `docs/data/person_references_sample.csv` 作为基线模板。  
- **导入脚本**：运行 `python manage.py import_catalog_data --places ... --eras ... --persons ...` 可一次性导入地名、年号与人物数据；`--format csv` 参数适用于上述模板。  
- **实体抽取**：执行 `python manage.py annotate_entities --part <PART_ID> --transcription-name manual`，即可用 HanLP 自动生成实体注释层（命名实体 AI），供用户在 eScriptorium 前端校对。  
- **质量检查**：对必填字段执行非空校验，并在导入脚本中校验 ID 唯一性、年份范围、经纬度取值。  
- **接口契约**：在生成的 OpenAPI/Swagger 文档中引入上述字段定义，保证 REST API 与前端表单保持一致。  
- **版本管理**：数据文件与 Schema 文档纳入仓库，后续调整通过 PR 评审并更新版本号。

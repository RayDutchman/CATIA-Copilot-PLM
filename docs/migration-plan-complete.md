# Payara → FastAPI 完整迁移计划

> **最后更新**：2026-07-07（迁移阶段全部完成，进入审计修复阶段）
> **追踪表**：`docs/migration-tracker.csv`（523 已完成 + 1 不适用 = **524/524 ✅**）
> **方法论**：`docs/migration-methodology.md`
> **文档索引**：`docs/DOCS_INDEX.md`

---

## 一、当前完成度评估（2026-07-07 最新）

### 追踪表状态

| 指标 | 值 |
|------|-----|
| 总条目 | 524 |
| 已完成 | 523 |
| 不适用 | 1 |
| 待新建 | **0** |
| 待拆分 | **0** |

### 里程碑

| 日期 | 批次 | 内容 | 提交 |
|------|------|------|------|
| 07-07 | P2B | 30 服务文件（Configuration+Listeners+Products+Documents+Indexer+Validation+GCM） | 39476fb, bd571da |
| 07-07 | P3B-A | 8 路由端点（attributes/lov/effectivity/tags/template_files） | 42a1820 |
| 07-07 | P3B-B | 15 文件（file/util + file_export + 3 导出端点） | 8c24d97 |
| 07-07 | P4B | 29 文件（WebSocket 全栈 + Extension converters/importers） | 4796f96 |
| 07-07 | 收尾 | CSV tracker 16 条状态修正 → 全量清零 | 58c3fbb |
| 07-07 | 审计 | 5 步验收审计（NotImplementedError/空函数/TODO/HTTP对拍/代码质量） | e7024ea |
| 07-07 | 审计 | HTTP 对拍 V2 升级 (144→162 端点) | e0dbb3b |
| 07-07 | 审计 | full_compare_v2.py V3 统一版 (种子数据+全方法+字段diff) | e7b4725 |
| 07-07 | 文档 | DOCS_INDEX.md + 归档过时 superpowers 文件 | 本次 |

### 测试状态

```
176 passed, 1 skipped — 全绿
```

### 当前阶段：审计修复

迁移全部完成，进入**审计修复**阶段。主要发现（来自 `docs/audit-report.md`）：

| 维度 | 发现 |
|------|------|
| HTTP 对拍 V2 | 162 端点: 73 MATCH / 42 PARTIAL / 47 MISMATCH |
| full_compare V3 | 138 端点: 81 MATCH / 11 PARTIAL / 44 MISMATCH |
| 代码质量 | 12 方法中发现 🔴17 严重 + 🟡10 中等差异 |
| TODO 残留 | 25 项（已记录 REMINDERS） |

修复计划：`docs/audit-report.md` → 分批执行（B1~B7），每批 pytest → commit。

---

## 二、历史评估（迁移前，2026-07-07 初版，保留供参考）

> 以下数据为迁移**开始前**的快照，当前实际完成度见上方。

### 按功能性 vs 按文件映射

| 维度 | 完成度 | 说明 |
|------|--------|------|
| **功能可用性**（用户感知） | **~90%** | 前端 CRUD 全流程通，Nginx 90% 路由已切到 FastAPI |
| **1:1 文件映射**（源码对齐） | **14.9%** | 523 个目标文件仅 78 个对齐，其余逻辑压缩在 85 个大文件中 |
| **API 字段对齐**（HTTP 对拍） | **~65%** | 133 端点：37 MATCH / 41 PARTIAL / 55 MISMATCH |
| **资源文件** | **~12%** | 34 个 i18n/模板/字体仅 6 个已迁移 |
| **单元测试覆盖** | **良好** | 144 tests passed，但未逐文件对拍 |

### 一句话评估

> **功能性上已可替代 Payara 90%（用户看不出来），但代码结构上只完成 14.6%。** 剩余的 85.4% 工作是"拆大文件 + 补边缘功能 + 资源迁移 + 全量审计"，目标是从"能跑"到"1:1 与 Java 源码对齐"。

### 按类型明细

| 类型 | 目标 | 已完成 | 待拆分 | 待新建 | 完成率 | 优先级排序 |
|------|------|--------|--------|--------|--------|-----------|
| **Core** | 13 | 13 | 0 | 0 | **100%** | - |
| **Python 特有** | 8 | 8 | 0 | 0 | **100%** | - |
| **Model** | 167 | 1 | 47 | 119 | **0.6%** | P0A ✂️ → P0B 🆕 |
| **Resource** | 34 | 6 | 0 | 28 | **17.6%** | P0B 🆕 |
| **Schema** | 125 | 0 | 63 | 62 | **0%** | P1A ✂️ → P1B 🆕 |
| **Service** | 84 | 10 | 6 | 68 | **11.9%** | P2A ✂️ → P2B 🆕 |
| **Router** | 63 | 40 | 0 | 23 | **63.5%** | P3B 🆕 |
| **WebSocket + Extension** | 29 | 0 | 0 | 29 | **0%** | P4B 🆕 |
| **合计** | **523** | **78** | **116** | **329** | **14.9%** | |

---

## 二、完整迁移 Plan（5 阶段，预估 15-22 天）

```
 S0: 基础设施准备（1天）
  │
  ├─ S1A: Model 层拆分（P0A, 47✂️, ~3天）  ← 先拆，不碰新建
  │   └─ pytest 全绿后进入 S1B
  ├─ S1B: Model 层补齐（P0B, 119🆕, ~4天）
  │
  ├─ S2A: Schema 层拆分（P1A, 63✂️, ~2天）
  ├─ S2B: Schema 层补齐（P1B, 62🆕, ~3天）
  │
  ├─ S3A: Service 层拆分（P2A, 6✂️, ~1天）
  ├─ S3B: Service 层补齐（P2B, 68🆕, ~4天）
  │
  ├─ S4: Router + 资源补齐（P3B, ~2天）
  │
  └─ S5: 全量审计 + 验收（~2天）
```

---

### S0：基础设施准备（1 天，不改代码）

**目标**：生成所有审计工具，为后续阶段提供"对照标准"。

| 步骤 | 产出 | 方法 |
|------|------|------|
| S0.1 | **migration-tracker.csv** | ✅ 已自动生成（515 行） |
| S0.2 | **throw-matrix.md** | `grep -rn "throw new"` 扫描所有 Java Bean，生成异常对照表 |
| S0.3 | **method-coverage.md** | `grep "public "` 提取每个 Bean 的 public 方法清单 |
| S0.4 | **复制资源文件** | 从 Java 项目直接复制 28 个 `.properties` + 3 个 `.json` 模板 → `app/resources/` |
| S0.5 | **目录骨架创建** | 预创建所有目标目录结构（`models/product/`, `services/events/` 等） |

**验证门**：`throw-matrix.md` 生成完毕 + 资源文件 md5 校验通过。

---

### S1：Model 层拆分 + 补齐（5-7 天，P0）

**目标**：将 9 个大 Model 文件拆为 167 个 1:1 文件，补 102 个新文件。

**分批策略**（按域 + 按依赖，每批 ≤20 文件）：

| 批次 | 域 | 文件数 | 依赖 | 风险 |
|------|-----|--------|------|------|
| S1.1 | `models/product/` | 32 | 无（其他域不依赖 product） | 低 |
| S1.2 | `models/common/` + `models/security/` | 23 | 无 | 低 |
| S1.3 | `models/configuration/` | 21 | 依赖 product | 中 |
| S1.4 | `models/document/` | 13 | 无 | 低 |
| S1.5 | `models/change/` | 8 | 无 | 低 |
| S1.6 | `models/workflow/` | 19 | 无 | 低 |
| S1.7 | `models/meta/` + `models/query/` + `models/sharing/` + `models/hooks/` + `models/admin/` + `models/log/` + `models/notification/` | 44 | 低（大部分为新文件） | 低 |
| S1.8 | `models/gcm/` + `models/util/` | 7 | 无 | 低 |

**每批次工作流**：
1. AI agent 读取 Java 源文件（ground truth）
2. 拆分：从大文件提取对应 class → 独立文件
3. 新建：参考 Java entity 字段 + JPA 注解 → SQLAlchemy model
4. 更新 `from models.xxx import *` 到 `from models.product.part_master import PartMaster`
5. 运行 `pytest tests/ -q --tb=short` 验证
6. 标记 tracker 行为 ✅

**关键风险**：`relationship()` 外键断裂 — 拆分后需要保证跨文件引用正确。

**验证门**：`pytest tests/ -q` 全部 144 通过 + `python -c "from app.models import *"` 不报错。

---

### S2：Schema 层拆分 + 补齐（3-5 天，P1）

**目标**：将 9 个大 Schema 文件拆为 125 个 1:1 Pydantic 文件。

| 批次 | 域 | 文件数 | 说明 |
|------|---|--------|------|
| S2.1 | `schemas/` 根包 — part 相关 | 20 | 从 `part.py` 拆出 CADInstanceDTO 等 |
| S2.2 | `schemas/` 根包 — document 相关 | 7 | 从 `document.py` 拆 |
| S2.3 | `schemas/` 根包 — workflow 相关 | 10 | 从 `workflow.py` + `misc.py` 拆 |
| S2.4 | `schemas/` 根包 — admin + user + misc | 25 | 从 `admin.py` + `user_mgmt.py` + `misc.py` 拆 |
| S2.5 | `schemas/baseline/` + `schemas/change/` + `schemas/product/` | 21 | 全新建 |
| S2.6 | `schemas/` 根包 — 其余杂项 | 12 | webhook, shared, tag, lov 等 |

**验证门**：`pytest tests/ -q` 通过 + `scripts/full_compare_v2.py` 无回归。

---

### S3：Service 层补齐（3-5 天，P2）

**目标**：补齐 67 个缺失的 Service 文件 + 拆分 4 个大文件。

| 批次 | 域 | 文件数 | 优先级 |
|------|---|--------|--------|
| S3.1 | 拆 `product_manager.py`（1184 行）→ task + cascade | 2 | 高 |
| S3.2 | `services/events/` | 15 | 中 |
| S3.3 | `services/configuration/`（spec + filter） | 12 | 中 |
| S3.4 | `services/` 根包 Bean（workspace, share, webhook 等） | 20 | 高 |
| S3.5 | `services/products/` + `services/documents/` | 5 | 中 |
| S3.6 | `services/hooks/` + `services/listeners/` + `services/storage/` | 10 | 低 |
| S3.7 | `services/indexer/` + `services/validation/` + `services/gcm/` | 8 | 低 |

**验证门**：`pytest tests/ -q` 通过 + import 检查通过。

---

### S4：Router + 资源补齐（2-3 天，P3）

**目标**：补齐 23 个缺失的 Router + 迁移剩余资源文件。

| 批次 | 内容 | 文件数 |
|------|------|--------|
| S4.1 | 补齐 Router：`tags.py`, `lov.py`, `attributes.py`, `files.py`, `workspace_workflow.py` 等 | 10 |
| S4.2 | 补齐 Router util + writer 套件 | 12 |
| S4.3 | 迁移 ES 索引模板 3 个 JSON | 3 |
| S4.4 | 迁移字体 3 个 TTF | 3 |
| S4.5 | 迁移 mime.types | 1 |

**验证门**：`scripts/full_compare_v2.py` — 所有端点 HTTP 对拍。

---

### S5：全量审计 + 验收 + 下线 Payara（2 天）

**目标**：最终确认所有 515 行为 ✅，下线 Payara。

| 步骤 | 方法 |
|------|------|
| S5.1 | **7 维审计**：按 `file-mapping.md` prompt 模板，AI agent 逐对审计 515 个文件对 |
| S5.2 | **throw-matrix 清理**：所有异常 raise 已对齐（i18n 无 bypass） |
| S5.3 | **HTTP 对拍**：`full_compare_v2.py` 全端点 PASS |
| S5.4 | **浏览器实测**：前端 Backbone.js 逐模块功能验证 |
| S5.5 | **Nginx 全量切**：所有路由指向 FastAPI，关闭 Payara |
| S5.6 | **周观察期**：监控错误日志，快速回滚 Payara 如遇问题 |

---

## 三、执行纪律（来自历史教训）

| 规则 | 来源 |
|------|------|
| **先读 Java → 再写 Python** | 禁止"先写代码后审计"（产出 stub） |
| **每批 ≤20 文件** | AI agent 上下文窗口限制 |
| **每批后跑 `pytest` + import check** | 防止拆分破坏现有功能 |
| **以 Java 源码为验收标准** | HTTP 200 ≠ 对齐完成 |
| **每批后更新 tracker CSV** | 进度可视化 |
| **不按功能域分期切 Nginx** | 全量对齐后一次性切（S5） |

---

## 四、已知风险（需要 S1-S4 解决）

| 风险 | 当前状态 | S 阶段解决 |
|------|----------|-----------|
| 3D 预览 GLB 不加载（Three.js r90 代理差异） | 已知未解决 | S5 浏览器实测排查 |
| 装配同步未迁移（BOM 更新仍在 Payara） | 已知未解决 | S3 product_manager 拆分后 |
| ES 搜索空缺（用 DB ilike 替代） | 暂时替代 | S3.7 indexer 补齐 |
| 转换回调 JWT 过期 | 已知未解决 | S3.4 service补齐 |
| REST API BasicAuth 401 | 已知未解决 | S5 排查 |

---

## 五、文档索引

| 文档 | 用途 |
|------|------|
| `docs/migration-tracker.csv` | **唯一数据源** — 523 行可排序/筛选的进度追踪表（← 替代 `proposed-file-mapping.md`） |
| `docs/migration-plan-complete.md` | 本文档 — 完整迁移计划 |
| `docs/migration-methodology.md` | 7 维审计方法论 |
| `docs/superpowers/fastapi-migration-roadmap.md` | 历史路线图（P0-P5 执行记录） |
| `docs/file-mapping.md` | 当前业务映射（55 对 + 22 基建对） |
| `docs/throw-matrix.md` | 待生成 — 异常对照表 |

---

## 附录 A：目标目录结构

```
app/
├── main.py                              # RestApplication.java
├── core/                                # 基础设施
│   ├── config.py                        # ServerConfig + AuthConfig + IndexerConfig
│   ├── database.py                      # EntityManagerProducer
│   ├── security.py                      # JWTokenManager
│   ├── exceptions.py                    # 86 个 Java 异常类
│   ├── exception_handlers.py            # 19 个 ExceptionMapper
│   ├── deps.py                          # RequestFilter 依赖注入
│   └── i18n.py                          # PropertiesLoader
├── models/                              # JPA Entity → SQLAlchemy ORM
│   ├── admin/        common/        configuration/
│   ├── change/       document/      hooks/
│   ├── gcm/          log/           meta/
│   ├── notification/ product/       query/
│   ├── security/     sharing/       util/
│   └── workflow/
├── services/                            # EJB Beans
│   ├── accounts/     configuration/  documents/
│   ├── events/       factory/        hooks/
│   ├── indexer/      listeners/      products/
│   ├── storage/      validation/     gcm/
│   └── *.py（根包 Bean）
├── routers/                             # REST Resources
│   ├── converters/   file/           util/
│   └── *.py（根包 Resource）
├── schemas/                             # DTO → Pydantic
│   ├── baseline/     change/         product/
│   └── *.py（根包 DTO）
├── ws/                                  # WebSocket（低优先级）
└── resources/                           # 静态资源
    ├── i18n/（.properties 国际化）
    ├── es/（.json 索引模板）
    ├── fonts/（.ttf 字体）
    ├── templates/（邮件通知模板）
    └── mime.types
```

## 附录 B：Java 路径锚定规则

| tracker CSV 中的 Java 路径前缀 | 实际 Maven 模块根目录 |
|-------------------------------|----------------------|
| `core/xxx/` | `docdoku-plm-server-core/src/main/java/com/docdoku/plm/server/core/` |
| `ejb/xxx/` | `docdoku-plm-server-ejb/src/main/java/com/docdoku/plm/server/` |
| `rest/xxx/` | `docdoku-plm-server-rest/src/main/java/com/docdoku/plm/server/` |
| `config/xxx/` | `docdoku-plm-server-config/src/main/java/com/docdoku/plm/server/` |
| `ext/xxx/` | `docdoku-plm-server-ext/src/main/java/com/docdoku/plm/server/` |

## 附录 C：Key 类 + Dozer 处理原则

- **Key 类**：Java 的 `*Key.java`（JPA `@Embeddable` 复合主键）在 SQLAlchemy 中直接作为模型主键字段定义，**不单独创建 Python 文件**。CSV 中部分 `*Key.java` 标记为 `🆕` 的可在执行时合并到父模型。
- **Dozer 转换器**（8 个 `*DozerConverter.java`）：由 Pydantic `@field_validator` / `model_validator` 替代，无需独立文件。CSV 中未列出这些行。

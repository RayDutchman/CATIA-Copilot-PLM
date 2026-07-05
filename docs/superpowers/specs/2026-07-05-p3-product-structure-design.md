# 设计：P3 产品结构（ConfigurationItems/Baselines/Configurations/Instances）

日期：2026-07-05
状态：设计已确认，待写实现计划
路线图阶段：P3（见 `docs/superpowers/fastapi-migration-roadmap.md`）

## 背景

P0-P2 已完成（基础设施→零件→文档/文件夹）。P3 迁移产品结构模块，包含 ConfigurationItem、ProductBaseline、ProductConfiguration、ProductInstance。

## 目标

在 FastAPI 实现产品结构核心功能，行为与 Payara 一致，前端零改动。

## 范围

**In scope（约 35 端点，4 功能域）**：

| 域 | 内容 |
|---|---|
| ConfigurationItem | CRUD + filterProductStructure（递归组件树）+ decodePath + 搜索 |
| ProductBaseline | CRUD + 创建路径选项 + 版本选项 |
| ProductConfiguration | CRUD |
| ProductInstance | CRUD + 迭代 + 文件上传下载 |

**Out of scope（记入"后续补做"清单，见末尾）**：

| 不做 | 理由 | 补做时机 |
|------|------|----------|
| path-to-path links（6 端点） | 独立高级功能，非产品结构核心 CRUD | 需要时 |
| cascade checkout/checkin/undocheckout（3 端点） | 遍历树调已有零件端点，foreach 模式 | 结构树完成后再做 |
| import/export（3 端点） | 批量工具，非核心读写 | 需要时 |
| path-data CRUD（10 端点） | 产品实例的 3D 装配路径数据，依赖实例已存在 | 实例功能稳定后 |

## 架构

### 新建文件

| 文件 | 职责 |
|------|------|
| `app/models/product.py` | configurationitem/baseline/config/instance/pathdata ORM |
| `app/routers/products.py` | ProductResource + ConfigurationsResource + BaselinesResource |
| `app/routers/product_instances.py` | ProductInstancesResource |
| `app/routers/product_files.py` | ProductInstanceBinaryResource（文件上传下载） |
| `app/services/product_structure_service.py` | filterProductStructure 递归 ComponentDTO 组装 + decodePath |

### 修改文件

| 文件 | 改动 |
|------|------|
| `app/main.py` | 注册 3 个新路由 |
| `docdoku-plm-docker/front/nginx.conf` | 新增 products/configurations/baselines/instances/files 路由块（5 个） |

### Nginx 路由变更

产品结构路径 `/workspaces/{ws}/products` 不会被 P1a 的 parts 正则 `^/.../workspaces/[^/]+/parts` 误匹配：`products` ≠ `parts`。新增路由块放在 P2 之后、Payara 兜底之前。

### 核心难点：filterProductStructure 递归 ComponentDTO

`ProductManagerBean.filterProductStructure()` 返回递归 `ComponentDTO`，每节点含 30+ 字段（`partNumber`、`version`、`amount`、`path`、`cadInstances[]` 位置矩阵、`components[]` 递归子节点等）。这是 P0-P5 所有阶段中最复杂的数据结构。

## i18n 对齐基线

| 场景 | i18n key |
|------|----------|
| CI 已存在 | `ConfigurationItemAlreadyExistsException` |
| CI 未找到 | `ConfigurationItemNotFoundException` |
| 删除 CI — 有基线 | `EntityConstraintException4` |
| 删除 CI — 有实例 | `EntityConstraintException13` |
| 删除 CI — 有配置 | `EntityConstraintException23` |
| 基线未找到 | `BaselineNotFoundException` |
| 实例已存在 | `ProductInstanceAlreadyExistsException` |
| 实例未找到 | `ProductInstanceNotFoundException` |
| 配置未找到 | `ProductConfigurationNotFoundException` |
| 路径解码循环装配 | `EntityConstraintException12` |

i18n 基础设施复用 P1a-align 的 `app/core/exceptions.py` + `i18n.py`，不新建。

## 测试策略

1. 单元/集成测试（真实 DB，现有 assembly 数据 partusagelink 21行 + cadinstance 102行可用于结构树测试）
2. Payara 对拍（空 DB 下也能对比端点状态码/格式）
3. 前端实测清单（交用户验收）

## 执行顺序（遵循标准每阶段工作流）

1. ORM 建模（`app/models/product.py`）
2. ConfigurationItem CRUD + 搜索
3. filterProductStructure（递归 ComponentDTO）+ decodePath
4. ProductBaseline CRUD + 创建路径选项
5. ProductConfiguration CRUD
6. ProductInstance CRUD + 文件上传下载
7. **对齐审计**：逐方法对照 Java `filterProductStructure` 等关键方法 + 补齐 i18n
8. **Payara 对拍**：无 diff 后进入下一步
9. **前端实测清单** 交用户验收
10. **通过后** 切 Nginx 产品结构路由（5 个路由块）
11. 更新 REMINDERS（"后续补做"清单）+ CHANGELOG + 路线图

## 后续补做清单

以下端点 P3 不做，在 REMINDERS 中追踪，后续单独补做：

| 端点 | 路径 | 补做时机 |
|------|------|----------|
| path-to-path links CRUD | `/products/{ciId}/path-to-path-links` | 需要时 |
| path-to-path links query | `/products/{ciId}/path-to-path-links/source/{sp}/target/{tp}` | 需要时 |
| path-to-path links types | `/products/{ciId}/path-to-path-links-types` | 需要时 |
| cascade-checkout | `/products/{ciId}/cascade-checkout` | 结构树完成后 |
| cascade-checkin | `/products/{ciId}/cascade-checkin` | 结构树完成后 |
| cascade-undocheckout | `/products/{ciId}/cascade-undocheckout` | 结构树完成后 |
| import attributes | `/products/import` | 需要时 |
| export files | `/products/{ciId}/export-files` | 需要时 |
| path-data CRUD | `/products/{ciId}/instances/{sn}/pathdata/...` | 实例功能稳定后 |

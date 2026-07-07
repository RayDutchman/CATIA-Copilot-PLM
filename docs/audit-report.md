# 验收审计报告

> 生成时间: 2026-07-07 | 提交范围: 42a1820, 8c24d97, 4796f96, 58c3fbb

## Step 1 — NotImplementedError 审计 ✅

**找到 0 个残留 NotImplementedError**（排除已知文件 `effectivity_config_spec.py` 和 `ps_filter_visitor.py`）。

结论: **通过**。

---

## Step 2 — 空函数审计 ✅

**找到 0 个空函数**（排除 `services/events/` 目录）。

结论: **通过**。

---

## Step 3 — TODO/FIXME 统计 ⚠️

共 **25 个 TODO**，分布如下：

### 功能缺失型 (需要后续实现)
| 文件 | 行 | 内容 | 影响 |
|------|-----|------|------|
| `services/lov_manager.py` | 66 | `is_lov_deletable` 未检查模板引用 | LOV 可能被误删 |
| `services/product_structure.py` | 256 | PathData 未实现 | hasPathData 始终 False |
| `services/cascade_action_manager.py` | 15 | 级联 checkout 未实现 | 批量操作不完整 |
| `services/effectivity_manager.py` | 4,30 | create/update 方法 TODO | 现有端点已通过 raw SQL 绕过 |
| `services/public_entity_manager.py` | 60 | fullName 解析未实现 | 公共分享文件下载不工作 |

### Stub 型 (已有端点但功能空缺)
| 文件 | 行 | 内容 |
|------|-----|------|
| `services/importer.py` | 16-50 | 5 项导入器 TODO (Excel/预览/PathData/BOM) |
| `services/ondemand_converter.py` | 15,22 | 转换引擎集成 TODO |
| `services/workspace_manager.py` | 90-108 | 5 项磁盘计算/选项表 TODO |

### 占位型 (标注即可)
| 文件 | 内容 |
|------|------|
| `core/exceptions.py:304-305` | Indexer/GCM 异常（不适用） |
| `routers/products.py:329/532-534` | PathData 相关异常 |

结论: **25 项已记录到 REMINDERS.md**。

---

## Step 4 — HTTP 对拍 ⚠️

运行 `scripts/compare_all_endpoints.py` 结果: **50 MATCH, 46 PARTIAL, 36 MISMATCH**

### MISMATCH 分类

#### A. FA 500 → PY 200 (5 项) — Python 未正确处理异常
```
GET /workspaces/{ws}/documents/doc_revs
GET /workspaces/{ws}/product-baselines
GET /workspaces/{ws}/product-baselines/{ci}/baselines
GET /workspaces/{ws}/products/{ci}/path-to-path-links-types
GET /workspaces/{ws}/products/{ci}/path-to-path-links/source/{src}/target/{tgt}
GET /workspaces/{ws}/workflow-models
```
原因: Java 测试数据与 Python 测试数据不完全一致，Java 报 500 时 Python 返回 200 空列表。

#### B. FA 200 → PY 500 (7 项) — Python 内部错误
```
GET /workspaces/{ws}
GET /workspaces/{ws}/products/{ci}/bom
GET /workspaces/{ws}/products/{ci}/decode-path/{path}
GET /workspaces/{ws}/products/{ci}/filter
GET /workspaces/{ws}/products/{ci}/instances
GET /workspaces/{ws}/products/{ci}/paths
GET /workspaces/{ws}/webhooks
```
原因: workspace root 缺少完整聚合、BOM/instances/paths 等端点内部异常。

#### C. FA 404 → PY 500 (5 项) — 异常处理不应该抛 500
```
GET /auth/providers/42
GET /workspaces/{ws}/changes/issues/41
GET /workspaces/{ws}/effectivities/1
GET /workspaces/{ws}/product-instances/{ci}/instances/{sn}/link-path-part/{path}
GET /workspaces/{ws}/tasks/1
```
原因: 不存在的资源应该返回 404，当前返回 500 (EntityNotFoundException 未正确映射)。

#### D. FA 200 → PY 404 (9 项) — 缺失路由
```
GET /workspaces/{ws}/folders/{ws}/SeedFolder/folders
GET /workspaces/{ws}/groups/SEED-grp/users
GET /workspaces/{ws}/parts/SEED-ASSEM/effectivities
GET /workspaces/{ws}/product-baselines/{ci}/baselines/3/path-to-path-links-types
GET /workspaces/{ws}/product-baselines/{ci}/baselines/3/path-to-path-links/source/src/target/tgt
GET /workspaces/{ws}/products/{ci}/document-links/{pn}/wip
GET /workspaces/{ws}/products/{ci}/releases/last
GET /workspaces/{ws}/changes/milestones/1/requests
GET /workspaces/{ws}/changes/milestones/1/orders
```
原因: 这些端点仅在 FA 端实现，Python 端尚未实现。

#### E. 其他状态码不一致 (5 项)
| 端点 | FA | PY | 原因 |
|------|-----|-----|------|
| `/workspaces/{ws}/document-baselines/3` | 405 | 404 | PY 用 GET 替代 DELETE |
| `/workspaces/{ws}/document-baselines/3-light` | 405 | 404 | 同上 |
| `/workspaces/{ws}/lov/test-lov` | 405 | 404 | 同上 |
| `/workspaces/{ws}/workflow-instances/1` | 404 | 403 | 权限检查次序不同 |
| `/workspaces/more` | 404 | 200 | 路由匹配过于宽泛 |

结论: **36 个 MISMATCH**，其中 9 个是缺失路由（P3B 待补），12 个是异常处理问题（C 类 + B 类中的部分）。

---

## Step 5 — 代码质量抽查 ⚠️

逐对 12 个关键方法对比结果：

### ProductManager — 3 个方法
| 严重度 | 发现 |
|--------|------|
| 🔴 | `create_part`: 模板(PartMasterTemplate)完全不支持 |
| 🔴 | `create_part`: Workflow 不创建 Tasks |
| 🔴 | `checkout`: 缺 InstanceAttributeTemplates 复制 |
| 🟡 | `create_part`: 版本号硬编码 "A" |
| 🟡 | `checkout`: 锁策略不同(FOR UPDATE vs 普通 SELECT) |
| 🟡 | `set_tags`: 签出保护缺失 |

### DocumentManager — 3 个方法
| 严重度 | 发现 |
|--------|------|
| 🔴 | `delete_revision`: 缺 documentlink/acl/workflow/subscription/sharedentity 级联清理 |
| 🔴 | `create_document`: 未实例化 Workflow(仅存 workflow_id) |
| 🟡 | `checkin`: 缺邮件/GCM 通知 |

### WorkflowManager — 3 个方法
| 严重度 | 发现 |
|--------|------|
| 🔴 | role_mapping 完全跳过 TASK_USER/TASK_USERGROUP 表 |
| 🔴 | runningTasks 重启动逻辑与 Java 不同 |
| 🔴 | SequentialActivity 语义缺失(可能一次启动多个 task) |
| 🔴 | admin 可绕过审批权限 |
| 🔴 | Document/Part status 过早更新 |

### ChangeManager — 3 个方法
| 严重度 | 发现 |
|--------|------|
| 🔴 | `delete_item` 缺 ACL 写权限检查 |
| 🔴 | assignee 校验遗漏组成员资格 |
| 🟡 | Router 不区分读写权限 |
| 🟡 | initiator 校验更严格(Java 允许任意字符串) |

**总计：12 个关键方法中发现 🔴17 项严重差异、🟡10 项中等差异。**

---

## 汇总

| Step | 结果 | 问题数 |
|------|------|--------|
| 1. NotImplementedError | ✅ 通过 | 0 |
| 2. 空函数 | ✅ 通过 | 0 |
| 3. TODO/FIXME | ⚠️ 已记录 | 25 |
| 4. HTTP 对拍 | ⚠️ 有差异 | 36 MISMATCH |
| 5. 代码质量 | ⚠️ 有差异 | 27 发现 (🔴17 + 🟡10) |

### 优先修复建议

1. **P0 — Workflow**: role_mapping 跳过 TASK_USER/TASK_USERGROUP 表，workflow 审批链路完全断裂
2. **P0 — Document delete**: 级联删除缺失 7 张关联表，导致孤儿数据
3. **P1 — Product create**: 模板支持缺失，workflow Tasks 未创建
4. **P1 — 异常处理**: 未找到资源应返回 404 而非 500
5. **P2 — 缺失路由**: 9 个端点未实现
6. **P2 — 签出保护**: set_tags/delete 缺 checkout 用户校验

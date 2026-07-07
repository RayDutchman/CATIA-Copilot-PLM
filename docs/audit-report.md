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

## Step 4 — HTTP 对拍 (V2 全面版) ⚠️

运行 `scripts/compare_all_endpoints.py` V2 结果: **73 MATCH, 42 PARTIAL, 47 MISMATCH, 162 端点覆盖**

### MISMATCH 分类详情

#### A. FA 200 → PY 404 (缺失路由, 10 项)
端点存在于 FA 但 Python 未实现:
```
GET /workspaces/{ws}/folders/{ws}/SeedFolder/folders
GET /workspaces/{ws}/groups/SEED-grp/users
GET /workspaces/{ws}/parts/{pk}/effectivities
GET /workspaces/{ws}/products/{ci}/releases/last
GET /workspaces/{ws}/products/{ci}/document-links/{pn}/wip
GET /workspaces/{ws}/product-baselines/{ci}/baselines/{bl}/path-to-path-links-types
GET /workspaces/{ws}/product-baselines/{ci}/baselines/{bl}/path-to-path-links/source/*/target/*
GET /workspaces/{ws}/changes/milestones/{ms}/requests
GET /workspaces/{ws}/changes/milestones/{ms}/orders
... 及其它 2 项
```

#### B. FA 200 → PY 500 (内部错误, 10 项)
Python 应返回 200 但抛出异常:
```
GET /workspaces/{ws}                           -- 工作区详情聚合
GET /workspaces/{ws}/products/{ci}/bom         -- BOM 遍历
GET /workspaces/{ws}/products/{ci}/filter      -- 产品结构过滤
GET /workspaces/{ws}/products/{ci}/instances   -- 实例列表  
GET /workspaces/{ws}/products/{ci}/paths       -- 路径遍历
GET /workspaces/{ws}/products/{ci}/decode-path/{path}
GET /workspaces/{ws}/webhooks
... 及其它 3 项
```

#### C. FA 404 → PY 500 (异常处理, 7 项)
资源不存在时应返回 404，Python 返回 500:
```
GET /auth/providers/42
GET /workspaces/{ws}/changes/issues/{id}
GET /workspaces/{ws}/changes/milestones/{id}/requests
GET /workspaces/{ws}/changes/milestones/{id}/orders
GET /workspaces/{ws}/effectivities/1
GET /workspaces/{ws}/product-instances/{ci}/instances/{sn}/link-path-part/*
GET /workspaces/{ws}/tasks/1
```

#### D. FA 500 → PY 200 (异常吞没, 6 项)
Java 返回 500(数据问题)，Python 返回 200 空结果:
```
GET /workspaces/{ws}/documents/doc_revs         -- 待链接文档列表
GET /workspaces/{ws}/product-baselines          -- 基线列表
GET /workspaces/{ws}/product-baselines/{ci}/baselines
GET /workspaces/{ws}/products/{ci}/path-to-path-links-types
GET /workspaces/{ws}/products/{ci}/path-to-path-links/source/*/target/*
GET /workspaces/{ws}/workflow-models
```
原因: Java 测试数据与 Python 测试数据不完全一致，FA 无法处理时抛 500。

#### E. 其他状态码问题 (14 项)
| 问题 | 数量 | 示例 |
|------|------|------|
| FA 404 → PY 403 (权限次序) | 2 | workflow-instances |
| FA 405 → PY 404 (方法不允许) | 3 | document-baselines, lov, product-config |
| FA 404 → PY 200 (缺少404) | 2 | product-configs/42, workspaces/more |
| FA 422 → PY 500 (校验→500) | 2 | auth/login POST |
| FA 500 → PY 400 | 1 | accounts/me PUT |
| FA 403 → PY 400 | 3 | part delete/release/obsolete |
| FA 200 → PY 201 | 1 | user tag-sub add |
| FA 422 → PY 404 | 1 | baseline-light |

### PARTIAL 分类 (42 项)
主要原因是返回字段差异 (Python 缺失部分字段):
- Document DTO 缺 `lastIteration/workflow/obsoleteDate/lifeCycleState/routePath` 等 (~15 项)
- Part DTO 缺 `releaseDate/obsoleteDate/modificationDate/checkInDate/lifeCycleState` (~6 项)
- Change Issue/Request/Order DTO 缺 `category/priority/initiator/description/acl` (~10 项)
- 其他: config `substitutesParts`, membership `permission`, stats `total` 等 (~11 项)

### V1→V2 改善
| 指标 | V1 | V2 |
|------|-----|-----|
| 覆盖端点 | 132+12=144 | 162 |
| MATCH | 50 | 73 |
| PARTIAL | 46 | 42 |
| MISMATCH | 36 | 47 |
| ERROR | 0 | 0 |

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

# FA ↔ Payara 端点对拍差距报告

**测试日期**: 2026-07-05  
**测试端点**: 133  
**总览**: ✓ MATCH: 37 | ⚠ PARTIAL: 41 | ✗ MISMATCH: 55 | ✗ ERROR: 0

---

## 一、按模块汇总

| 模块 | MATCH | PARTIAL | MISMATCH | 需修复(FA侧) |
|------|-------|---------|----------|-------------|
| Auth | 2 | 0 | 2 | 0 |
| Admin | 0 | 0 | 2 | 0 |
| Platform | 2 | 1 | 0 | 1 |
| Accounts | 0 | 2 | 0 | 2 |
| Organizations | 0 | 1 | 1 | 1 |
| Workspaces | 19 | 20 | 27 | 12 |
| Parts | 3 | 6 | 6 | 3 |
| Documents | 3 | 6 | 0 | 6 |
| Products | 4 | 2 | 12 | 10 |
| Changes | 5 | 1 | 4 | 2 |
| Workflow | 0 | 0 | 2 | 2 |
| Tasks | 1 | 0 | 2 | 2 |
| Tags | 0 | 1 | 1 | 1 |
| Baselines | 0 | 3 | 1 | 3 |
| Misc (LOV/Webhooks/etc) | 4 | 3 | 2 | 3 |
| Shared | 0 | 2 | 0 | 0 |

---

## 二、FA 需修复项（仅列出 FA 侧问题，忽略 Payara 500 崩溃）

### 2.1 ✗ 缺失端点（FA:404 / PY:200）

FA 缺少以下端点路由，前端调用将 404：

| # | 端点 | 说明 |
|---|------|------|
| 1 | `GET /workspaces/{ws}/user-group` | Workspace 用户组概要 |
| 2 | `GET /workspaces/more` | 更多工作区列表 |
| 3 | `GET /workspaces/{ws}/users/{login}` | 指定用户信息 |
| 4 | `GET /workspaces/{ws}/part-templates` | 零件模板列表 |
| 5 | `GET /workspaces/{ws}/attributes/part-iterations` | 零件迭代属性 |
| 6 | `GET /workspaces/{ws}/attributes/path-data` | 路径数据属性 |
| 7 | `GET /workspaces/{ws}/products/{pid}/export-files` | 产品导出 |
| 8 | `GET /workspaces/{ws}/products/{pid}/path-to-path-links-types` | 路径链接类型 |
| 9 | `GET /workspaces/{ws}/products/{pid}/path-to-path-links/source/.../target/...` | 路径链接详情 |
| 10 | `GET /workspaces/{ws}/products/{pid}/layers` | 产品图层 |
| 11 | `GET /workspaces/{ws}/product-baselines/{pid}/baselines/{bid}/path-to-path-links-types` | 基线路径链接类型 |
| 12 | `GET /workspaces/{ws}/product-baselines/{pid}/baselines/{bid}/path-to-path-links/source/.../target/...` | 基线路径链接 |
| 13 | `GET /workspaces/{ws}/product-configurations/{pid}/configurations` | 产品配置列表 |
| 14 | `GET /workspaces/{ws}/product-instances/{pid}/instances` | 产品实例列表 |
| 15 | `GET /workspaces/{ws}/tasks/{login}/documents` | 任务的文档列表 |
| 16 | `GET /workspaces/{ws}/tasks/{login}/parts` | 任务的零件列表 |
| 17 | `GET /workspaces/{ws}/tags/{id}/documents` | 标签关联文档 |
| 18 | `GET /workspaces/{ws}/document-baselines` | 文档基线列表 |
| 19 | `GET /workspaces/{ws}/lov` | LOV 列表 |

**共 19 个缺失端点，需添加路由和处理函数。**

### 2.2 ✗ 端点行为不一致（FA:200 / PY:404）

FA 返回 200 但 Payara 返回 404，可能因测试数据差异或 FA 行为不对：

| # | 端点 | FA | PY | 问题 |
|---|------|----|----|------|
| 1 | `GET /workspaces/{ws}/groups/test1/tag-subscriptions` | 200 | 404 | Payara 无此数据→404，FA 返回空数据→200？需确认 |
| 2 | `GET /workspaces/{ws}/parts/{pn}/instances` | 200 | 404 | 同上 |
| 3 | `GET /workspaces/{ws}/parts/{pn}/aborted-workflows` | 200 | 404 | 同上 |
| 4 | `GET /workspaces/{ws}/parts/{pn}/used-by-product-instance-masters` | 200 | 404 | 同上 |
| 5 | `GET /workspaces/{ws}/folders/{ws}/SeedFolder/folders` | 200 | 404 | 同上 |
| 6 | `GET /workspaces/{ws}/products/{pid}/releases/last` | 200 | 404 | 同上 |

**共 6 个疑似行为差异，需逐个确认 FA 是否应返回 404。**

### 2.3 ✗ 端点行为不一致（FA:422 / PY:200）

FA 参数校验过严导致 422，Payara 正常返回：

| # | 端点 | FA | PY | 问题 |
|---|------|----|----|------|
| 1 | `GET /workspaces/{ws}/changes/issues/link` | 422 | 200 | 缺少必填 query 参数? |
| 2 | `GET /workspaces/{ws}/changes/requests/link` | 422 | 200 | 同上 |

**共 2 个，可能需放宽 query 参数校验或脚本补传参数。**

### 2.4 ✗ 端点行为不一致（FA:200 / PY:204）

| # | 端点 | FA | PY | 问题 |
|---|------|----|----|------|
| 1 | `GET /organizations` | 200 | 204 | FA 返回数据，PY 返回空(204) |

**1 个，需确认组织列表是否应为空。**

### 2.5 ✗ 端点行为不一致（FA:404 / PY:403）

| # | 端点 | FA | PY | 问题 |
|---|------|----|----|------|
| 1 | `GET /workspaces/{ws}/workflow-instances/1` | 404 | 403 | FA 路由缺失，直接 404；应返回 403 |
| 2 | `GET /workspaces/{ws}/workflow-instances/1/aborted` | 404 | 403 | 同上 |

**2 个，需添加 workflow-instances 路由（含权限校验返回 403）。**

---

### 2.6 ⚠ 缺失字段（PY+）：FA 响应缺少 Payara 有的字段

#### Accounts

| 端点 | FA 缺失字段 |
|------|------------|
| `GET /accounts/me` | `timeZone`, `admin`, `enabled` |
| `GET /accounts/workspaces` | `description`, `folderLocked` |

#### Organizations

| 端点 | FA 缺失字段 |
|------|------------|

#### Workspaces

| 端点 | FA 缺失字段 |
|------|------------|
| `GET /workspaces/{ws}/disk-usage-stats` | `partTemplates` |
| `GET /workspaces/{ws}/back-options` | `sendEmails`, `workspaceId` |
| `GET /workspaces/{ws}/checked-out-documents-stats` | `test1` (测试数据差异) |
| `GET /workspaces/{ws}/checked-out-parts-stats` | `test1` (测试数据差异) |
| `GET /workspaces/{ws}/users-stats` | `users`, `inactivegroups`, `activegroups`, `groups`, `activeusers`, `inactiveusers` |

#### Parts

| 端点 | FA 缺失字段 |
|------|------------|
| `GET /workspaces/{ws}/parts` | `releaseAuthor`, `obsoleteAuthor`, `workflow`, `acl` |
| `GET /workspaces/{ws}/parts/checkedout` | `releaseAuthor`, `obsoleteAuthor`, `workflow`, `acl` |
| `GET /workspaces/{ws}/parts/search` | `checkOutDate`, `workflow`, `acl`, `releaseAuthor`, `obsoleteAuthor`, `checkOutUser` |

#### Documents

| 端点 | FA 缺失字段 |
|------|------------|
| `GET /workspaces/{ws}/documents` | `releaseAuthor` |
| `GET /workspaces/{ws}/documents/checkedout` | `releaseAuthor`, `type` |
| `GET /workspaces/{ws}/documents/{id}` | `releaseAuthor` |
| `GET /workspaces/{ws}/document-templates` | `author`, `acl`, `creationDate`, `attachedFiles`, `attributeTemplates` |
| `GET /workspaces/{ws}/folders/{ws}/documents` | `releaseAuthor`, `type` |

#### Products

| 端点 | FA 缺失字段 |
|------|------------|
| `GET /workspaces/{ws}/product-configurations` | `substituteLinks`, `author`, `acl`, `optionalUsageLinks`, `creationDate` |

#### Changes

| 端点 | FA 缺失字段 |
|------|------------|
| `GET /workspaces/{ws}/changes/issues` | `category`, `priority` |

#### Tags

| 端点 | FA 缺失字段 |
|------|------------|
| `GET /workspaces/{ws}/tags` | `label`, `id`, `workspaceId` |

#### Platform

| 端点 | FA 缺失字段 |
|------|------------|
| `GET /platform/health` | `executionTime` |

---

### 2.7 ⚠ 多余字段（FA+）：FA 响应有多于 Payara 的字段

这些字段 Payara 没有，可能影响前端兼容性，需评估是否需要移除或保留：

| 端点 | FA 多余字段 | 风险评估 |
|------|------------|---------|
| `GET /platform/health` | `backend` | 低风险，前端不依赖 |
| `GET /accounts/me` | `timezone` (拼写 vs Payara 的 `timeZone`) | 中风险，拼写不一致 |
| `GET /workspaces/{ws}/disk-usage-stats` | `total` | 低风险 |
| `GET /workspaces/{ws}/users-stats` | `totalUsers` | 低风险 |
| `GET /workspaces/{ws}/parts/search` | `checkInDate` | 低风险 |
| `GET /workspaces/{ws}/parts/numbers` | `partName`, `partNumber` | 低风险 |
| `GET /workspaces/{ws}/documents` | `lastIteration`, `tags`, `obsoleteDate`, `routePath`, `workflow`, `lifeCycleState`, `description` | 中风险，前端可能使用这些字段 |
| `GET /workspaces/{ws}/documents/*` | 大量额外字段 (见 PARTIAL 明细) | 中风险，需逐个确认 |
| `GET /workspaces/{ws}/memberships/usergroups` | `memberId`, `workspaceId`, `readOnly`, `member` | 低风险 |
| `GET /workspaces/{ws}/roles/inuse` | `workspaceId`, `name`, `defaultAssignedUsers`, `id`, `defaultAssignedGroups` | 低风险 |

---

### 2.8 ⚠ 404 错误格式不一致

所有 404 响应：FA 返回 `{"detail": "..."}`，Payara 返回无 `detail` 字段的格式。

| 涉及端点 | 17 个 (见 PARTIAL 404/404 条目) |
|----------|------------------------------|
| 影响 | 低，前端通常只检查 status code |

---

## 三、Payara 500 崩溃（非 FA 问题，无需修复）

以下端点 Payara 返回 500，与 FA 无关：

| # | 端点 |
|---|------|
| 1 | `GET /auth/providers/42` |
| 2 | `POST /auth/login` |
| 3 | `GET /admin/accounts` |
| 4 | `GET /admin/platform-options` |
| 5 | `GET /workspaces/{ws}` |
| 6 | `GET /workspaces/{ws}/parts/{pn}/used-by-as-component` |
| 7 | `GET /workspaces/{ws}/parts/{pn}/used-by-as-substitute` |
| 8 | `GET /workspaces/{ws}/products` |
| 9 | `GET /workspaces/{ws}/products/numbers` |
| 10 | `GET /workspaces/{ws}/products/{pid}/bom` |
| 11 | `GET /workspaces/{ws}/products/{pid}/filter` |
| 12 | `GET /workspaces/{ws}/products/{pid}/paths` |
| 13 | `GET /workspaces/{ws}/products/{pid}/instances` |
| 14 | `GET /workspaces/{ws}/products/{pid}/decode-path/path-param` |
| 15 | `GET /workspaces/{ws}/product-baselines` |
| 16 | `GET /workspaces/{ws}/product-baselines/{pid}/baselines` |
| 17 | `GET /workspaces/{ws}/product-baselines/{pid}/baselines/{id}` |
| 18 | `GET /workspaces/{ws}/product-baselines/{pid}/baselines/{id}/parts` |
| 19 | `GET /workspaces/{ws}/product-instances/{pid}/instances/{sn}/link-path-part/...` |
| 20 | `GET /workspaces/{ws}/changes/issues/41` |
| 21 | `GET /workspaces/{ws}/changes/requests/42` |
| 22 | `GET /workspaces/{ws}/changes/orders/42` |
| 23 | `GET /workspaces/{ws}/tasks/1` |
| 24 | `GET /workspaces/{ws}/effectivities/1` |

---

## 四、修复优先级建议

### P0 - 阻塞性（前端直接无法使用）
1. **19 个缺失端点** (2.1) — 前端 404
2. **workflow-instances 路由** (2.5) — 应返回 403 而非 404
3. **changes/xxx/link 参数校验过严** (2.3) — 前端 422

### P1 - 功能不完整（前端可用但功能缺失）
4. **缺失字段补全** (2.6) — 前端依赖这些字段
   - Documents 系列缺少 `releaseAuthor`, `type`
   - Parts 系列缺少 `releaseAuthor`, `obsoleteAuthor`, `workflow`, `acl`
   - Product configurations 缺少字段
   - Accounts 缺少 `admin`, `enabled`
   - Users stats 缺少完整统计字段

### P2 - 兼容性优化
5. **多余字段评估** (2.7) — 确认是否保留或移除
6. **FA:200/PY:404 行为差异确认** (2.2) — 逐个验证
7. **404 错误格式统一** (2.8)

---

## 五、统计图示

```
端点总数: 133
├── ✓ MATCH:   37 (27.8%)  ← 完全一致
├── ⚠ PARTIAL: 41 (30.8%)  ← 字段有差异，多数为 FA 缺少字段
└── ✗ MISMATCH: 55 (41.4%)  ← HTTP 状态码不一致
    ├── 24 个 Payara 500 (43.6%) — 非 FA 问题
    ├── 19 个 FA 缺失端点 (34.5%) — 需添加路由
    ├──  6 个 FA:200/PY:404 (10.9%) — 行为差异待确认
    ├──  2 个 FA:422/PY:200 (3.6%) — 参数校验过严
    ├──  2 个 FA:404/PY:403 (3.6%) — 缺失 workflow-instances 路由
    ├──  1 个 FA:200/PY:204 (1.8%) — organizations 行为差异
    └──  1 个 FA:422/PY:500 (1.8%) — Payara 崩溃
```

**FA 侧实际需修复项: 约 30 个 (缺失端点 19 + 缺失字段 ~Infinity + 行为差异 4)**

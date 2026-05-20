# DocdokuPLM REST API 使用笔记

> 基于源码分析（docdoku-plm-server），记录客户端对接时的关键发现。

---

## GET /workspaces/{workspaceId}/parts/{partNumber}-{version}

### 正常返回结构（200）

```json
{
  "partKey": "PART-001-A",
  "number": "PART-001",
  "version": "A",
  "name": "零件名称",
  "lastIterationNumber": 1,
  "status": "WIP",
  "workspaceId": "Workspace_0",
  "standardPart": false,
  "publicShared": false,
  "attributesLocked": false,
  "checkOutUser": {
    "login": "admin",
    "name": "John Doe",
    "email": "admin@example.com",
    "workspaceId": "Workspace_0"
  },
  "checkOutDate": "2026-05-20T10:00:00Z",
  "author": { "login": "admin", "name": "John Doe" },
  "creationDate": "2026-05-01T00:00:00Z",
  "partIterations": [ "..." ],
  "acl": null,
  "workflow": null,
  "tags": [],
  "notifications": []
}
```

### 关键字段名对照

| 含义 | 实际 JSON key | 备注 |
|---|---|---|
| 版本号 | `version` | 字符串，如 `"A"` |
| 最新迭代号 | `lastIterationNumber` | 整数 |
| 检出用户对象 | `checkOutUser` | 嵌套 UserDTO，未检出时为 `null` |
| 检出用户登录名 | `checkOutUser.login` | **不存在** `checkOutLogin` 顶级字段 |
| 检出时间 | `checkOutDate` | 未检出时为 `null` |

> `PartRevisionDTO.java` 没有任何 `@JsonbProperty` 自定义改名，所有 JSON key 与 Java 字段名完全一致。

### 零件不存在时

返回 **HTTP 404**。`getPartRevision()` 抛出 `EntityNotFoundException`，由 JAX-RS 异常映射器转为 404。

---

## URL 编码注意事项

路径模板为：
```
@Path("{partNumber: [^/].*}-{partVersion:[A-Z]+}")
```

`partNumber` 正则 `[^/].*` 能匹配含空格的字符串，但：

- HTTP 路径中空格**必须** encode 为 `%20`（不是 `+`，`+` 只用于 query string）
- 客户端示例（Python）：

```python
import urllib.parse
encoded = urllib.parse.quote(part_number, safe='')
url = f"/api/workspaces/{workspace_id}/parts/{encoded}-{version}"
```

---

## 服务端 Bug：`isCheckoutByAnotherUser` / `isCheckoutByUser` NPE（已修复）

### 现象

访问某些零件时，服务端日志报：

```
NullPointerException at ProductManagerBean.java:3509
```

### 根因

`ProductManagerBean.java` 第 3504–3510 行，两个方法都对 `getCheckOutUser()` 直接调用 `.equals()`，而 `checkOutUser` 在数据不一致时可能为 null（如 checkout 中途失败、数据迁移不完整）：

```java
// 修复前（有 bug）
private boolean isCheckoutByUser(User user, PartRevision partRevision) {
    return partRevision.isCheckedOut() && partRevision.getCheckOutUser().equals(user);
}

private boolean isCheckoutByAnotherUser(User user, PartRevision partRevision) {
    return partRevision.isCheckedOut() && !partRevision.getCheckOutUser().equals(user);
}
```

### 修复方案

将调用方翻转为 `user.equals(...)`。`user` 来自登录上下文，保证非 null；`user.equals(null)` 在 Java 中返回 `false`，无需额外 null 判断，改动最小：

```java
// 修复后
private boolean isCheckoutByUser(User user, PartRevision partRevision) {
    // 使用 user.equals() 避免 checkOutUser 为 null 时的 NPE
    return partRevision.isCheckedOut() && user.equals(partRevision.getCheckOutUser());
}

private boolean isCheckoutByAnotherUser(User user, PartRevision partRevision) {
    // 使用 user.equals() 避免 checkOutUser 为 null 时的 NPE
    return partRevision.isCheckedOut() && !user.equals(partRevision.getCheckOutUser());
}
```

**已于 2026-05-20 修复，文件：`docdoku-plm-server-ejb/.../ProductManagerBean.java:3504–3510`**

### 客户端防御性读取（仍建议保留）

```python
check_out_login = (data.get("checkOutUser") or {}).get("login")
```

---

## 相关源码位置

| 文件 | 作用 |
|---|---|
| `docdoku-plm-server-rest/.../PartsResource.java:98` | 路径路由注册 |
| `docdoku-plm-server-rest/.../PartResource.java:89` | `@GET` 实现 |
| `docdoku-plm-server-rest/.../dto/PartRevisionDTO.java` | 响应体 DTO 字段定义 |
| `docdoku-plm-server-rest/.../Tools.java:146` | PartRevision → DTO 映射逻辑 |
| `docdoku-plm-server-ejb/.../ProductManagerBean.java:3504` | `isCheckoutByUser` / `isCheckoutByAnotherUser`（NPE bug **已修复**） |

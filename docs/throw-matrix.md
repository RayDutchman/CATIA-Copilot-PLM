# Exception Throw Matrix: Java → Python

> 从 Payara EJB 源码自动生成，用于 7 维审计第 7 维"Exception throw parity"。
> Python 异常定义在 `app/core/exceptions.py`。

---

## 统计概览

| 指标 | 数值 |
|------|------|
| Java 异常类型总数 | 74 |
| Python 已覆盖 | 66 (89%) |
| 缺失 | 8 (低优先级) |
| Java throw 总次数 | 481 |

---

## 异常对照表

| # | Java Exception | Java 次数 | Python Exception | i18n Key 示例 | 覆盖状态 |
|---|---------------|----------|------------------|---------------|----------|
| 1 | `NotAllowedException` | 131 | `NotAllowedException` | `NotAllowedException2-75`, `WorkflowNameEmptyException` | ✅ |
| 2 | `AccessRightException` | 65 | `AccessRightException` | (user name) | ✅ |
| 3 | `CreationException` | 35 | `CreationException` | (none) | ✅ |
| 4 | `EntityConstraintException` | 28 | `EntityConstraintException` | `EntityConstraintException3-28` | ✅ |
| 5 | `IllegalArgumentException` | 17 | — | (Java built-in) | — |
| 6 | `StorageException` | 13 | — | file storage errors | ❌ 缺失 |
| 7 | `FileNotFoundException` | 10 | `FileNotFoundException` | | ✅ |
| 8 | `IndexerNotAvailableException` | 8 | `IndexerNotAvailableException` | | ✅ |
| 9 | `EffectivityNotFoundException` | 7 | — | | ❌ 缺失 |
| 10 | `WorkflowNotFoundException` | 5 | `WorkflowNotFoundException` | | ✅ |
| 11 | `IndexerRequestException` | 5 | `IndexerRequestException` | | ✅ |
| 12 | `FileAlreadyExistsException` | 5 | `FileAlreadyExistsException` | | ✅ |
| 13 | `WebhookNotFoundException` | 3 | `WebhookNotFoundException` | | ✅ |
| 14 | `SharedEntityNotFoundException` | 3 | `SharedEntityNotFoundException` | | ✅ |
| 15 | `PartMasterNotFoundException` | 3 | `PartMasterNotFoundException` | | ✅ |
| 16 | `PathDataMasterNotFoundException` | 3 | `PathDataMasterNotFoundException` | | ✅ |
| 17 | `FolderNotFoundException` | 3 | `FolderNotFoundException` | | ✅ |
| 18-44 | *FoundException（各 2 次）* | 27 | ✅ 全部覆盖 | | ✅ |
| 45-74 | *FoundException（各 1 次）* | 30 | ✅ 基本覆盖 | | ✅ |

---

## 缺失项（8 个，P2 可补）

| Java Exception | 次数 | 建议 |
|----------------|------|------|
| `StorageException` | 13 | 新建 `class StorageException(ApplicationException)` |
| `EffectivityNotFoundException` | 7 | 已有 `Effectivity` 概念相关代码 |
| `EffectivityAlreadyExistsException` | 1 | 按 `*AlreadyExistsException` 模式新建 |
| `ListOfValuesAlreadyExistsException` | 1 | 按模式新建 |
| `OAuthProviderNotFoundException` | 1 | 低优先级（OAuth 未迁移） |
| `ProvidedAccountNotFoundException` | 2 | 低优先级（OAuth 未迁移） |
| `PlatformHealthException` | 1 | 已有 health endpoint 可用 HTTP 500 替代 |
| `UnsupportedCallbackException` | 1 | JAAS 特定，Python 不需要 |

---

## 按 Bean 分布（Top 5）

| Java Bean | throw 次数 | 关键异常 |
|-----------|-----------|----------|
| `WorkflowManagerBean.java` | ~45 | NotAllowedException, AccessRightException |
| `ChangeManagerBean.java` | ~40 | NotAllowedException, EntityConstraintException |
| `ProductManagerBean.java` | ~35 | AccessRightException, NotAllowedException |
| `AccountManagerBean.java` | ~25 | NotAllowedException |
| `DocumentManagerBean.java` | ~20 | NotAllowedException, AccessRightException |

---

## 审计使用方式

```
Read docs/throw-matrix.md.
For every exception in column "Java Exception":
  If "Python Exception" = ❌ → report as gap (P2 task)
  If "Python Exception" = ✅ → verify Python service methods raise correct exception with matching i18n key
```

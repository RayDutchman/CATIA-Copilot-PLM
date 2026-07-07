# Java → Python 审计维度参考

> **用于 AI 逐文件对比检查时参考**。7 维审计 Prompt 已迁至 `docs/ai-execution-rules.md`。
> 业务映射表已被 `docs/migration-tracker.csv` 完全覆盖，不在此重复。
> 审计历史已迁至 `docs/audit-report.md`。

---

## 一、基础设施映射（无直接 Java 对应文件，但有关联 Java 组件）

| # | Python 文件 | 相关联的 Java 组件 |
|---|-----------|-------------------|
| C1 | `app/core/config.py` | `ConversionServiceConfig.java`，`Back.env` 环境变量 |
| C2 | `app/core/database.py` | `EntityManagerProducer.java` (JPA) |
| C3 | `app/core/deps.py` | `RequestFilter.java` + `JWTokenManager.java` |
| C4 | `app/core/exceptions.py` | `com/docdoku/plm/server/core/exceptions/*.java` (86 文件) |
| C5 | `app/core/exception_handlers.py` | `AccessRightsExceptionMapper.java` 等 |
| C6 | `app/core/i18n.py` | `PropertiesLoader.java` |
| C7 | `app/core/security.py` | `JWTokenManager.java`，`Credential.java` (MD5) |
| C8 | `app/main.py` | `RestApplication.java` (JAX-RS Application) |
| C9 | `app/models/auth.py` | `Account.java`, `Credential.java`, `UserGroupMapping.java` |
| C10 | `app/models/part.py` | `PartMaster.java`, `PartRevision.java`, `PartIteration.java` 等 |
| C11 | `app/models/document.py` | `DocumentMaster.java`, `DocumentRevision.java` 等 |
| C12 | `app/models/product.py` | `ConfigurationItem.java`, `ProductBaseline.java` 等 |
| C13 | `app/models/change.py` | `ChangeIssue.java`, `ChangeRequest.java` 等 |
| C14 | `app/models/workflow.py` | `WorkflowModel.java`, `Workflow.java`, `Activity.java` 等 |
| C15 | `app/models/security.py` | `ACL.java`, `AclUserEntry.java`, `Role.java` |
| C16 | `app/models/user_mgmt.py` | `UserGroup.java`, `Workspace.java` (部分字段) |
| C17 | `app/models/notification.py` | `ModificationNotification.java` |
| C18 | `app/schemas/auth.py` | `AccountDTO.java` |
| C19 | `app/schemas/part.py` | `PartRevisionDTO.java`, `PartIterationDTO.java` 等 (~20 DTO) |
| C20 | `app/services/acl_helper.py` | `ACLFactory.java` (抽象) |
| C21 | `app/services/security_service.py` | `RoleManagerBean.java` (间接) |
| C22 | `app/services/kafka_producer.py` | `ConverterBean.java` (Kafka 部分) |

## 二、文件夹结构

```
app/
├── core/           # 基础设施（config/DB/auth/i18n/异常）— 对应 Java core + i18n 包
├── models/         # ORM 模型 — 对应 Java JPA Entity 类
├── schemas/        # Pydantic 模型 — 对应 Java DTO 类
├── services/       # 业务逻辑 — 对应 Java EJB
└── routers/        # REST 端点 — 对应 Java Resource
```

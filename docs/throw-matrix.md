# Throw Matrix — Payara 异常 → Python 对齐状态

> 生成方式：`grep -rn "throw new"` Payara EJB + REST → 去重 → 逐条检查 Python 是否有等价 `raise` 和异常类。

| Payara 异常 | Bean 抛出次数 | Python 异常类 | Python raise | 状态 |
|---|---|---|---|---|
| `NotAllowedException` | 148 | ✅ | ✅ | ✅ |
| `AccessRightException` | 65 | ✅ | ✅ | ✅ |
| `CreationException` | 35 | ✅ | ✅ | ✅ |
| `EntityConstraintException` | 28 | ✅ | ✅ | ✅ |
| `StorageException` | 13 | ❌ | ❌ | **缺** |
| `FileNotFoundException` | 10 | ✅ | ✅ | ✅ |
| `EffectivityNotFoundException` | 7 | ❌ | ❌ | **缺** |
| `WorkflowNotFoundException` | 5 | ✅ | ❌ | 缺 raise |
| `FileAlreadyExistsException` | 5 | ✅ | ✅ | ✅ |
| `WebhookNotFoundException` | 3 | ✅ | ❌ | 缺 raise |
| `SharedEntityNotFoundException` | 3 | ✅ | ✅ | ✅ |
| `PathDataMasterNotFoundException` | 3 | ✅ | ❌ | 缺 raise（TO DO） |
| `PartMasterNotFoundException` | 3 | ✅ | ✅ | ✅ |
| `FolderNotFoundException` | 3 | ✅ | ✅ | ✅ |
| `WorkspaceNotEnabledException` | 2 | ✅ | ✅ | ✅ |
| `UserGroupNotFoundException` | 2 | ✅ | ❌ | 缺 raise |
| `TagNotFoundException` | 2 | ✅ | ❌ | 缺 raise |
| `ProductInstanceIterationNotFoundException` | 2 | ✅ | ✅ | ✅ |
| `PathToPathLinkAlreadyExistsException` | 2 | ✅ | ❌ | 缺 raise（TO DO） |
| `PartUsageLinkNotFoundException` | 2 | ✅ | ✅ | ✅ |
| `PartRevisionNotFoundException` | 2 | ✅ | ✅ | ✅ |
| `OrganizationNotFoundException` | 2 | ✅ | ❌ | 缺 raise |
| `MilestoneNotFoundException` | 2 | ✅ | ✅ | ✅ |
| `MarkerNotFoundException` | 2 | ✅ | ✅ | ✅ |
| `DocumentRevisionNotFoundException` | 2 | ✅ | ❌ | 缺 raise |
| `ConfigurationItemNotFoundException` | 2 | ✅ | ❌ | 缺 raise |
| `BaselineNotFoundException` | 2 | ✅ | ❌ | 缺 raise |
| `WorkspaceAlreadyExistsException` | 1 | ✅ | ❌ | 缺 raise |
| `WorkspaceNotFoundException` | 1 | ✅ | ✅ | ✅ |
| `WorkflowModelNotFoundException` | 1 | ✅ | ❌ | 缺 raise |
| `WorkflowModelAlreadyExistsException` | 1 | ✅ | ✅ | ✅ |
| `UserNotActiveException` | 1 | ✅ | ✅ | ✅ |
| `UserGroupAlreadyExistsException` | 1 | ✅ | ❌ | 缺 raise |
| `UserAlreadyExistsException` | 1 | ✅ | ✅ | ✅ |
| `UserNotFoundException` | 1 | ✅ | ✅ | ✅ |
| `TaskNotFoundException` | 1 | ✅ | ❌ | 缺 raise |
| `TagAlreadyExistsException` | 1 | ✅ | ❌ | 缺 raise |
| `RoleNotFoundException` | 1 | ✅ | ❌ | 缺 raise |
| `RoleAlreadyExistsException` | 1 | ✅ | ❌ | 缺 raise |
| `QueryAlreadyExistsException` | 1 | ✅ | ❌ | 缺 raise |
| `ProductInstanceMasterNotFoundException` | 1 | ✅ | ❌ | 缺 raise |
| `ProductConfigurationNotFoundException` | 1 | ✅ | ❌ | 缺 raise |
| `PlatformHealthException` | 1 | ✅ | ✅ | ✅ |
| `PathToPathLinkNotFoundException` | 1 | ✅ | ❌ | 缺 raise（TO DO） |
| `PathToPathCyclicException` | 1 | ✅ | ❌ | 缺 raise（TO DO） |
| `PasswordRecoveryRequestNotFoundException` | 1 | ✅ | ❌ | 缺 raise（TO DO） |
| `PartRevisionAlreadyExistsException` | 1 | ✅ | ✅ | ✅ |
| `PartMasterTemplateAlreadyExistsException` | 1 | ✅ | ✅ | ✅ |
| `PartMasterTemplateNotFoundException` | 1 | ✅ | ✅ | ✅ |
| `PartMasterAlreadyExistsException` | 1 | ✅ | ❌ | 缺 raise |
| `PartIterationNotFoundException` | 1 | ✅ | ✅ | ✅ |
| `OrganizationAlreadyExistsException` | 1 | ✅ | ❌ | 缺 raise |
| `MilestoneAlreadyExistsException` | 1 | ✅ | ✅ | ✅ |
| `ListOfValuesNotFoundException` | 1 | ✅ | ✅ | ✅ |
| `ProductInstanceAlreadyExistsException` | 1 | ✅ | ❌ | 缺 raise |
| `LayerNotFoundException` | 1 | ✅ | ✅ | ✅ |

**统计**：55 个 Payara 异常 ➔ 32 已对齐 ➔ 17 有类无 raise ➔ 2 完全缺（Storage / Effectivity）➔ 4 不可实现（TODO）

**不可实现项**（Payara 基础设施依赖，Python 无对应组件）：
- `StorageException` — 文件存储异常（Python 用 vault 直写，无中间层）
- `EffectivityNotFoundException` — Effectivity 域完全未实现（stub）
- `PathDataMasterNotFoundException` — PathData 域未实现（TODO）
- `PathToPathLinkNotFoundException / AlreadyExists / Cyclic` — P2P 链接 CRUD 未实现（TODO）
- `PasswordRecoveryRequestNotFoundException` — 邮件恢复流程未实现（TODO）
- `IndexerNotAvailableException / IndexerRequestException` — 无 ES 索引器（TODO）

**回生清单**（有异常类但代码从未抛出，需补 raise）：
`WorkflowNotFoundException`, `WebhookNotFoundException`, `UserGroupNotFoundException`, `TagNotFoundException`, `OrganizationNotFoundException`, `DocumentRevisionNotFoundException`, `ConfigurationItemNotFoundException`, `BaselineNotFoundException`, `WorkspaceAlreadyExistsException`, `WorkflowModelNotFoundException`, `UserGroupAlreadyExistsException`, `TaskNotFoundException`, `TagAlreadyExistsException`, `RoleNotFoundException`, `RoleAlreadyExistsException`, `QueryAlreadyExistsException`, `ProductInstanceMasterNotFoundException`, `ProductConfigurationNotFoundException`, `PartMasterAlreadyExistsException`, `OrganizationAlreadyExistsException`, `ProductInstanceAlreadyExistsException`

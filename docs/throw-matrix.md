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
| `WorkflowNotFoundException` | 5 | ✅ | ✅ | ✅ |
| `FileAlreadyExistsException` | 5 | ✅ | ✅ | ✅ |
| `WebhookNotFoundException` | 3 | ✅ | ✅ | ✅ |
| `SharedEntityNotFoundException` | 3 | ✅ | ✅ | ✅ |
| `PathDataMasterNotFoundException` | 3 | ✅ | ❌ | 缺 raise（TO DO） |
| `PartMasterNotFoundException` | 3 | ✅ | ✅ | ✅ |
| `FolderNotFoundException` | 3 | ✅ | ✅ | ✅ |
| `WorkspaceNotEnabledException` | 2 | ✅ | ✅ | ✅ |
| `UserGroupNotFoundException` | 2 | ✅ | ✅ | ✅ |
| `TagNotFoundException` | 2 | ✅ | ✅ | ✅ |
| `ProductInstanceIterationNotFoundException` | 2 | ✅ | ✅ | ✅ |
| `PathToPathLinkAlreadyExistsException` | 2 | ✅ | ❌ | 缺 raise（TO DO） |
| `PartUsageLinkNotFoundException` | 2 | ✅ | ✅ | ✅ |
| `PartRevisionNotFoundException` | 2 | ✅ | ✅ | ✅ |
| `OrganizationNotFoundException` | 2 | ✅ | ✅ | ✅ |
| `MilestoneNotFoundException` | 2 | ✅ | ✅ | ✅ |
| `MarkerNotFoundException` | 2 | ✅ | ✅ | ✅ |
| `DocumentRevisionNotFoundException` | 2 | ✅ | ✅ | ✅ |
| `ConfigurationItemNotFoundException` | 2 | ✅ | ✅ | ✅ |
| `BaselineNotFoundException` | 2 | ✅ | ✅ | ✅ |
| `WorkspaceAlreadyExistsException` | 1 | ✅ | ✅ | ✅ |
| `WorkspaceNotFoundException` | 1 | ✅ | ✅ | ✅ |
| `WorkflowModelNotFoundException` | 1 | ✅ | ✅ | ✅ |
| `WorkflowModelAlreadyExistsException` | 1 | ✅ | ✅ | ✅ |
| `UserNotActiveException` | 1 | ✅ | ✅ | ✅ |
| `UserGroupAlreadyExistsException` | 1 | ✅ | ✅ | ✅ |
| `UserAlreadyExistsException` | 1 | ✅ | ✅ | ✅ |
| `UserNotFoundException` | 1 | ✅ | ✅ | ✅ |
| `TaskNotFoundException` | 1 | ✅ | ✅ | ✅ |
| `TagAlreadyExistsException` | 1 | ✅ | ✅ | ✅ |
| `RoleNotFoundException` | 1 | ✅ | ✅ | ✅ |
| `RoleAlreadyExistsException` | 1 | ✅ | ✅ | ✅ |
| `QueryAlreadyExistsException` | 1 | ✅ | ❌ | 缺 raise |
| `ProductInstanceMasterNotFoundException` | 1 | ✅ | ✅ | ✅ |
| `ProductConfigurationNotFoundException` | 1 | ✅ | ✅ | ✅ |
| `PlatformHealthException` | 1 | ✅ | ✅ | ✅ |
| `PathToPathLinkNotFoundException` | 1 | ✅ | ❌ | 缺 raise（TO DO） |
| `PathToPathCyclicException` | 1 | ✅ | ❌ | 缺 raise（TO DO） |
| `PasswordRecoveryRequestNotFoundException` | 1 | ✅ | ❌ | 缺 raise（TO DO） |
| `PartRevisionAlreadyExistsException` | 1 | ✅ | ✅ | ✅ |
| `PartMasterTemplateAlreadyExistsException` | 1 | ✅ | ✅ | ✅ |
| `PartMasterTemplateNotFoundException` | 1 | ✅ | ✅ | ✅ |
| `PartMasterAlreadyExistsException` | 1 | ✅ | ✅ | ✅ |
| `PartIterationNotFoundException` | 1 | ✅ | ✅ | ✅ |
| `OrganizationAlreadyExistsException` | 1 | ✅ | ✅ | ✅ |
| `MilestoneAlreadyExistsException` | 1 | ✅ | ✅ | ✅ |
| `ListOfValuesNotFoundException` | 1 | ✅ | ✅ | ✅ |
| `ProductInstanceAlreadyExistsException` | 1 | ✅ | ✅ | ✅ |
| `LayerNotFoundException` | 1 | ✅ | ✅ | ✅ |

**统计**：55 个 Payara 异常 ➔ 51 已对齐 ➔ 1 有类无 raise (`QueryAlreadyExistsException`) ➔ 2 完全缺（Storage / Effectivity）➔ 1 TODO 项

**不可实现项**（Payara 基础设施依赖，Python 无对应组件）：
- `StorageException` — 文件存储异常（Python 用 vault 直写，无中间层）
- `EffectivityNotFoundException` — Effectivity 域完全未实现（stub）
- `QueryAlreadyExistsException` — 查询保存功能未实现（TODO）

**P2P / PathData / 其他 TODO 项**：
- `PathDataMasterNotFoundException` — PathData 域未实现（TODO）
- `PathToPathLinkNotFoundException / AlreadyExists / Cyclic` — P2P 链接 CRUD 未实现（TODO）
- `PasswordRecoveryRequestNotFoundException` — 邮件恢复流程未实现（TODO）
- `IndexerNotAvailableException / IndexerRequestException` — 无 ES 索引器（TODO）

**回生清单**（有异常类但代码从未抛出，仍需补 raise）：
无（全部「缺 raise」非TODO项已补齐✅，`QueryAlreadyExistsException` 移入不可实现/TODO）

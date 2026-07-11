# Products 产品域审计报告

> 审计员：explore subagent ｜ 日期：2026-07-11 ｜ 波次：1
> 范围：products.py / product_instances.py / product_configurations.py / product_files.py / product_structure.py / product_manager.py(结构部分) / psfilter_manager.py / path_data_service.py / path_to_path_service.py

## 问题 PR-CRIT-1
- 严重级：CRITICAL
- 类别：要点#1（裸 SQL 写入错误表）
- 位置：`app/services/product_structure.py:679-697`（create_config）
- Java 对照：`ProductConfigurationsResource.java:179-198` → ProductBaselineManagerBean.createProductConfiguration
- 证据：Python 把 substitute_links 写 `partsubstitutelink`、optional 写 `UPDATE partusagelink SET optional=true`。Java 正确写 `prdcfg_substitutelink(productbaseline_id, substitutelinks)` / `prdcfg_optionallink(productbaseline_id, optionalusagelinks)`（存路径字符串）。DB 已核实两表结构。
- 结论与建议：配置的替代链/可选链永久丢失。重写为写 prdcfg_* 表、用路径字符串。
- **✅ 已修复（2026-07-12，批 4）**：`create_config` 改写路径字符串到 `prdcfg_substitutelink`/`prdcfg_optionallink`（keyed by config.id）；并补 `delete_config` 清 prdcfg_* 关联行（FK NO ACTION）。smoke 往返一致。

## 问题 PR-CRIT-2
- 严重级：CRITICAL
- 类别：要点#1（ID 继承断裂）
- 位置：`app/models/configuration/product_configuration.py:6-17` + `app/routers/product_configurations.py:63-78`
- Java 对照：`ProductConfiguration extends ProductBaseline`（JPA joined inheritance 共享 id）
- 证据：Python ProductConfiguration 有独立自增 id，未继承 ProductBaseline.id；读取用 `prdcfg_substitutelink.productbaseline_id = config.id`，但该 FK 指向 productbaseline.id 而非 productconfiguration.id。两 SERIAL 独立自增，仅偶然重叠可用。
- 结论与建议：改 joined inheritance 或创建配置时同步写 productbaseline 回填 FK。与 PR-CRIT-1 叠加。
- **⚠️ 已复核为误报（2026-07-12，批 4 brainstorming）**：Java `ProductConfiguration` 是**独立 `@Entity`**（非 `extends ProductBaseline`），有自己的 `GenerationType.IDENTITY` id。DB `information_schema` 证实 `prdcfg_substitutelink/optionallink.productbaseline_id`（命名误导）FK **实际指向 `productconfiguration.id`**，且 `productconfiguration` 有独立 `productconfiguration_id_seq`。Python 模型 id 与读取路径均已用 config.id。**读写主键本就一致，无需改动**。

## 问题 PR-CRIT-3
- 严重级：CRITICAL
- 类别：要点#3（硬编码桩）
- 位置：`app/routers/product_instances.py:252-257`（rebase_instance）
- Java 对照：`ProductInstancesResource.java:448-458` → rebaseProductInstance
- 证据：Python `return Response(status_code=204)` 完全无操作。Java 创建新 ProductInstanceIteration 并关联基线。
- 结论与建议：实现完整 rebase 逻辑。
- **✅ 已修复（2026-07-12，批 4）**：`rebase_instance` 校验 baseline 存在→创建 iteration+1 + 关联新 baseline + 继承 iterationNote，去掉空 204 桩。简化实现未深拷贝 collections/pathData（已注释标注）。

## 问题 PR-CRIT-4
- 严重级：CRITICAL
- 类别：要点#3 + #10（vault 操作）
- 位置：`app/routers/product_files.py:14-23`（upload）
- Java 对照：`ProductInstanceBinaryResource.java:102-134` → saveFileInProductInstance
- 证据：Python 只写物理文件不注册 BinaryResource DB 行。Java 创建 BinaryResource + 写 vault + 返回 201+URL。
- 结论与建议：文件上传后无 DB 记录，无法经标准 binary resource 下载/删除。需创建 BinaryResource 行。
- **✅ 已修复（2026-07-12，批 4）**：upload 写物理文件同时 INSERT/UPDATE `binaryresource` + `prdinstiteration_binres` 关联，返回 201+fullName。smoke 上传→下载一致。

## 问题 PR-CRIT-5
- 严重级：CRITICAL
- 类别：要点#15（路由 URL 错 + 逻辑缺失）
- 位置：`app/routers/product_instances.py:107-155`（update_instance）
- Java 对照：`ProductInstancesResource.java:197-243` URL 含 `/{iteration}`
- 证据：Python URL 缺 `/{iteration}`，直接改末迭代不创建新迭代，且未处理 instanceAttributes。Java 按 iteration 创建新迭代（含属性/文档链接/基线引用）。
- 结论与建议：修复路由 + 补 InstanceAttribute 处理。
- **✅ 已修复（2026-07-12，批 4）**：补 `PUT .../instances/{sn}/iterations/{iteration}` 路由，就地更新目标迭代 note/instanceAttributes/linkedDocuments。**注**：复核 Java `updateProductInstance` 实为「就地改指定迭代」非「创建新迭代」，本报告原述有误，已按 Java 真值实现。

## 问题 PR-HIGH-1 ~ PR-HIGH-5
- **PR-HIGH-1** (要点#11+#17)：`product_structure.py:141-144` filter_product_structure 缺 linkType 参数，无 filterProductStructureOnLinkType；diverge 接受但未使用。Java ProductResource.java:250。
- **PR-HIGH-2** (要点#3)：`product_instances.py:42-93` list_instances 3D 模式（有 configSpec）总取最新迭代，不按 configSpec 过滤，不支持 `pi-{serial}`，缺 POST getInstancesForMultiplePath。
- **PR-HIGH-3** (要点#11)：`products.py:537-596` ci_paths(searchPaths) 缺 configSpec/diverge，永远用最后修订。Java ProductResource.java:336-357。
- **PR-HIGH-4** (要点#11)：`products.py` cascade-checkout/checkin/undo 缺 configSpec/path，全量收集易 OOM。Java ProductResource.java:877-934。
- **PR-HIGH-5** (要点#2)：`path_to_path_service.py:317-323` P2P link 的 sourceComponents/targetComponents 恒空数组，未做 decodePath。Java ProductResource.java:1070-1096。

## 问题 PR-MED-1 ~ PR-MED-5
- **PR-MED-1** (要点#5)：`path_data_service.py:340-358` `_sync_path_data_attributes` INSERT 漏 dtype → 读回全退化 TEXT（product_structure.py:432 fallback）。对比 product_manager.py:806 正确写 dtype。
- **PR-MED-2** (要点#8)：`product_manager.py:694-713` cadInstances 写入 rotation_type 可能 None；当前 Python 读取端有 fallback 但 rotationType 空+matrix 非空会走错分支。建议写入端推断 rotation_type。**✅ 已修复（2026-07-12，批次 3）**：`__do_sync_components` 写入端 rotationType 为 None 时按有 m00→"MATRIX"、否则→"ANGLE" 推断（Java 枚举实为 ANGLE 非 ANGULAR）。smoke 验证新 cadinstance rotationtype=MATRIX。
- **PR-MED-3** (要点#17)：缺 `POST /{ciId}/instances`（PathListDTO 批量多路径）、缺 layers 子资源。Java ProductResource.java:497-543 / :360-363。
- **PR-MED-4** (要点#2)：`products.py:226-253` get_product_instance 返回缺 acl 字段。Java ProductInstanceMasterDTO 有 acl。
- **PR-MED-5** (要点#3+#14)：`products.py:41-47` `_p2p_svc_lazy` `except Exception: return []` 吞异常。

## 问题 PR-LOW-1
- `product_structure.py:461-467` hasModificationNotification 仅查根零件，Java 全树遍历——但 Java 自身注释"太重"且已注释掉调用，Python 简化合理，**非 bug**。

## 已排除
- partcollection/pathdatamaster/pathtopathlink/instanceattribute 缺 id → 均 SERIAL，误报。
- DTO CRITICAL×2（PathDataIterationCreationDTO/ProductBaselineCreationDTO）→ 已知 CreationDTO 错配误报。

## 小结
| 严重级 | 数量 |
|--------|------|
| CRITICAL | 5 |
| HIGH | 5 |
| MEDIUM | 5 |
| LOW | 1 |

整体：CI/实例列表/decodePath/P2P CRUD 较好；但 **ProductConfiguration 持久化两个 CRITICAL（写错表+ID 不关联）**、3D 实例 configSpec 链缺失、实例更新/文件上传逻辑缺失。优先修 5 个 CRITICAL。

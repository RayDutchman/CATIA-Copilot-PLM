# [Products] 审计报告（域2）

> 第二轮迁移代码审计 ｜ 只读代码对比 ｜ 基准 workspace = GD50

**总体结论**：框架完整（CI/P2P/PathData CRUD 覆盖齐全，SQL 基本一致）。1 CRITICAL / 5 HIGH / 4 MED / 3 LOW（经独立复核修订）。

---

## 问题 P2-01
- 严重级：HIGH（原 CRITICAL，复核调整）
- 复核：SEVERITY-ADJUST→HIGH。delete_instance 未清 7 张子表 FK（NO ACTION）属实，但 GD50 这 7 张子表当前全 0 行，仅用户创建 PathData/属性/文档链接后触发，属潜在缺陷。
- 类别：清单#4（级联删除）+ #5
- 文件：`app/services/product_structure.py:822-826`（delete_instance）
- Java对照：`ProductInstanceManagerBean.deleteProductInstance()` JPA 级联
- 证据：先 `DELETE FROM productinstanceiteration` 再删 master，但 iteration 被 7 张表 FK 引用（NO ACTION）：`prdinstiteration_attribute`/`_binres`/`_documentlink`/`_p2plink`/`_pathdatamstr`/`prdinstanceiteration_optlink`/`_sublink`。有数据时 FK 违约 → 500。
- 建议修复：先清 7 张子表，或 master 设 ON DELETE CASCADE。

## 问题 P2-02
- 严重级：CRITICAL
- 复核：CONFIRMED。_ci_to_dict(db,c) 参数错序（签名 (ci,db)），第 53 行 ci.partmaster_partnumber 在 Session 上 AttributeError，所有 /products/numbers?q= 搜索必 500。维持 CRITICAL。
- 类别：清单#15（接线正确性）
- 文件：`app/routers/products.py:97`（search_ci_numbers）
- Java对照：`ProductResource.searchConfigurationItemId()` (143-144)
- 证据：`_ci_to_dict(db, c)` 参数错序（签名是 `_ci_to_dict(ci, db)`），c 是 str 被当对象访问 → AttributeError → 500。
- 建议修复：改 `_ci_to_dict(c, db)`。

## 问题 P2-03
- 严重级：HIGH
- 复核：CONFIRMED。getPathData 的 partLinksList/partAttributes/partAttributeTemplates 全空，Java 三步填充（decodePath+PSFilter+属性）。
- 类别：清单#8/#3
- 文件：`app/services/products/path_data_service.py:443-451`（_build_master_dict）
- Java对照：`ProductInstancesResource.getPathData()` (511-533)
- 证据：PathDataMasterDTO 的 `partLinksList=None`、`partAttributes=[]`、`partAttributeTemplates=[]` 三项从未填充；Java 通过 decodePath + PSFilter + partIteration 属性/模板填充。前端 3D 路径解析与属性模板失效。
- 建议修复：补 decodePath + PSFilter 查询。

## 问题 P2-04
- 严重级：HIGH
- 复核：CONFIRMED。get_product_instance iteration 仅 5 字段，Java 15+（缺 substituteLinks/optionalUsageLinks/pathDataMasterList/basedOn/instanceAttributes 等 11 项）。
- 类别：清单#8（字段来源贯穿）
- 文件：`app/routers/products.py:383-...`（get_product_instance）
- Java对照：`ProductInstancesResource.getProductInstance()` (256-309)
- 证据：Python 每个 iteration 仅 5 字段；Java 填充 15+ 字段（substituteLinks/optionalUsageLinks/substitutesParts/optionalsParts/pathDataMasterList/pathDataPaths/pathToPathLinks/basedOn/instanceAttributes/linkedDocuments/attachedFiles）。
- 建议修复：逐 iteration 填充上述字段。

## 问题 P2-05
- 严重级：HIGH
- 复核：CONFIRMED（影响收窄）。CI ID 含连字符计算错属实（GD50 33/34 CI 含连字符），但仅影响非 visitor 路径（configSpec=None）；正常带 configSpec 的 3D 浏览走 visitor 路径不受影响。维持 HIGH。
- 类别：清单#8/#11
- 文件：`app/services/product_structure.py:388-406`（_check_has_path_data）
- Java对照：`ProductResource.createComponentDTO()` (1029-1032, getPathAsString)
- 证据：CI ID 含连字符时（GD50 34 个 CI 全含，如 `ACLCI-45ECFC`），`comp_path.find("-")` 定位到 CI 内连字符，构造出 `-1-45ECFC-u4262`（应为 `-1-u4262`）→ hasPathData 永远 False（非 visitor 路径）。
- 建议修复：用 `re.search(r'[-](?:u|s)\d+', comp_path)` 定位第一个 -u/-s。

## 问题 P2-06
- 严重级：HIGH（依 configSpec 覆盖率）
- 复核：CONFIRMED。pi-{serial} configSpec 降级为 latest/wip，绕过产品实例基线解析（substitute/optional/effectivity）。
- 类别：清单#11（查询分支）
- 文件：`app/routers/product_instances.py:147-150`
- Java对照：`ProductInstancesResource.addNewPathDataIteration()` (681)
- 证据：`pi-{serial}` configSpec 被降级为 `"latest"` PSFilter，未真正解析产品实例基线（substitute/optional/effectivity 决策）→ 3D 实例视图可能返回错误零件迭代。
- 建议修复：实现完整 pi- configSpec 解析。

## 问题 P2-07
- 严重级：MED
- 类别：清单#17
- 文件：`app/routers/products.py:216-224`（list_product_instances）
- Java对照：`ProductInstancesResource.getAllProductInstances()`→makeList (1078-1087)
- 证据：Python 仅返回 serialNumber+configurationItemId；Java 返回 ProductInstanceMasterDTO（identifier+迭代+acl）。
- 建议修复：对齐返回格式。

## 问题 P2-08
- 严重级：MED
- 类别：清单#11（linkType 过滤未实现）
- 文件：`app/services/product_structure.py:152`
- Java对照：`ProductResource.filterProductStructure()` (258-263)
- 证据：linkType!=null 时 Java 走 filterProductStructureOnLinkType，Python 注释标注未实现，忽略参数返回完整结构。
- 建议修复：实现 linkType 过滤分支。

## 问题 P2-09
- 严重级：MED
- 类别：清单#8
- 文件：`app/routers/products.py:161-166`（decode_path）
- Java对照：`ProductResource.decodePath()` (802-817)
- 证据：Java 返回 LightPartLinkDTO 列表，Python 直接返回 dict 列表；UserDTO 缺 membership 字段（decode_path 本身不涉及 user，影响轻微）。
- 建议修复：确认前端依赖，必要时补字段。

## 问题 P2-10
- 严重级：MED
- 类别：清单#10（vault 路径）
- 文件：`app/routers/product_files.py:15-63`
- 证据：Java vault 前缀 `product-instances`，Python 用 `products/{ci_id}/instances`，路径前缀不一致。
- 建议修复：统一 vault 路径格式。

## 问题 P2-11
- 严重级：LOW
- 类别：清单#3（吞异常）
- 文件：`app/routers/products.py:41-47`（_p2p_svc_lazy）
- 证据：`except Exception: return []` 吞所有异常，前端无法区分空/错。
- 建议修复：log 或限定 except 类型。

## 问题 P2-12
- 严重级：LOW
- 类别：清单#3
- 文件：`app/routers/product_configurations.py:204`（delete_config）
- 证据：返回 `{"status":"deleted"}` 而非 204 no body（Java noContent）。
- 建议修复：返回 204。

## 问题 P2-13
- 严重级：LOW
- 类别：清单#2
- 文件：`app/schemas/product/product_instance_iteration.py`
- 证据：updateAuthor/updateAuthorName 声明但从未赋值，序列化为 null 冗余。
- 建议修复：填充或移除。

---

## 已核对一致的要点
- #1 裸 SQL：partusagelink/pathdatamaster/pathdataiteration/pathtopathlink/instanceattribute/prdinstiteration_attribute 表名列名与 \d 一致。
- #2 假 CRITICAL 澄清：Java `PathDataIterationCreationDTO` 无 partLinksList；`ProductBaselineCreationDTO` author 亦工具误匹配；Python 端点用 `body: dict` 非 Pydantic，extra=forbid 不触发。**Phase-0 两个 DTO CRITICAL 均为假报。**
- #5 dtype 写入：product_instances._replace_instance_attributes、path_data_service._sync_path_data_attributes 均写 dtype。
- #7 异常：EntityNotFound/NotAllowed/PathToPathCyclic 一致。
- #16 SQL 注入：绑定参数，无风险。
- #6 权限：基本一致（Java canAccess 跳过，Python 设 accessDeny flag 不跳过 → 见 #8 行为差异）。

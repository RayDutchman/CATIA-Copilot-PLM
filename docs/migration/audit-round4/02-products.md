# 域2 Products 产品结构/实例 审计报告（第4轮）

> 生成日期：2026-07-12 ｜ 范围：`docdoku-plm-server-py` 产品/结构/实例迁移代码 vs Java/Payara
> 方法：explore subagent 逐端点对照 + information_schema 核实 + GD50 验证；主 agent 已直接核实 P2-14 列名
> 基准 workspace = GD50 ｜ **只读审计，未做任何修复**

## 结论
**1 CRITICAL / 2 HIGH / 3 MED / 2 LOW**。第3轮重构修复了第2轮绝大部分（P2-01/02/03/04/05/07/09/10）。本轮新发现 **1 个 CRITICAL（PathData 关联表 INSERT 列名错→创建必 500）** 及 2 HIGH。

---

## CRITICAL

### P2-14 prdinstiteration_pathdatamstr INSERT 列名错误 → 创建 PathData 必 500
- 严重级：**CRITICAL**
- 类别：清单#1（裸 SQL 列名真实性）
- 文件：`app/services/products/path_data_service.py:316-323`（`_attach_master_to_instance`） | Java对照：`ProductInstanceManagerBean` addNewPathDataIteration/createPathDataMaster（JPA ORM 写入）
- 证据（**主 agent 已用 psql 直接核实**）：
  - DB 实际 PK 列：`prdinstanceiteration_iteration`（`\d prdinstiteration_pathdatamstr` 确认，NOT NULL，属复合主键）
  - Python INSERT 用的列名：`iteration`
  ```sql
  INSERT INTO prdinstiteration_pathdatamstr
  (workspace_id, configurationitem_id, prdinstancemaster_serialnumber,
   iteration, pathdatamaster_id)              -- ← "iteration" 列不存在
  VALUES (:ws, :ci, :sn, :it, :mid) ON CONFLICT DO NOTHING
  ```
  → PostgreSQL 报 `column "iteration" does not exist`。同文件其他查询（`product_instance_manager.py:364`）正确用 `pipd.prdinstanceiteration_iteration`。
- 影响：所有 `create_path_data_master`/`add_new_path_data_iteration` 写关联表时 500，前端无法创建/编辑路径数据。
- 建议修复：`iteration` → `prdinstanceiteration_iteration`。
- 与前两轮关系：新发现（第2/3轮未覆盖 `_attach_master_to_instance` 写入路径）。

---

## HIGH

### P2-15 product_manager 服务层硬编码 HTTPException（2 处）
- 严重级：HIGH
- 类别：清单#7（异常一致性）
- 文件：`app/services/product_manager.py:1895`（"No native CAD file uploaded"）、`:2007`（"partKey 格式应为..."） | Java对照：Java 在 REST 层判断（`PartResource.retryConversion` null 时返 BAD_REQUEST），Service 不抛 HTTP 异常
- 证据（Phase0 `check_hardcoded_exceptions.py` 命中 + 主 agent 核实）：两处 `from fastapi import HTTPException` 局部导入后 `raise HTTPException(400,...)`，且错误文案含中文与 Java 不一致。第3轮把 router 逻辑迁进 service 时带进来的违规。
- 建议修复：改抛 WrongInputException/领域异常，或将格式校验保留在路由层。
- 与前两轮关系：新发现（第3轮重构引入）。

### P2-06 _resolve_pi_config_spec 缺 configurationitem_id 过滤 → 跨 CI 取错迭代
- 严重级：HIGH（前轮 configSpec 降级问题已改善，但改善引入新缺陷）
- 类别：清单#11（查询分支正确性）
- 文件：`app/services/product_structure.py:1479-1491`（`_resolve_pi_config_spec`） | Java对照：`ProductManagerBean.getConfigSpec()` 用 `ProductInstanceMasterKey(serial, ws, ciId)` 三元组加载
- 证据：`productinstancemaster` PK = `(serialnumber, workspace_id, configurationitem_id)`；Python 查询 ProductInstanceMaster / ProductInstanceIteration 时**仅 filter `workspace_id` + `serialnumber`，漏 `configurationitem_id`** → 同 serial 存在于不同 CI 时返回错误迭代。前轮已把"降级 latest"升级为"基线迭代解析"（`_BaselineBasedPSFilter`），但未真正按基线 collection 解析 substituteLinks/optionalUsageLinks/effectivity。
- 建议修复：两处查询加 `configurationitem_id == ci_id` 条件。
- 与前两轮关系：前轮部分修（configSpec 改善），本轮复核发现新缺陷。

---

## MED

### P2-16 _resolve_pi_config_spec 同源缺 CI 过滤（与 P2-06 同根，独立记录）
- 严重级：MED
- 类别：清单#11
- 文件：`app/services/product_structure.py:1479-1491`
- 证据：见 P2-06。
- 建议修复：同 P2-06。
- 与前两轮关系：新发现。

### P2-08 linkType 过滤仅最小实现
- 严重级：MED
- 类别：清单#11
- 文件：`app/services/product_structure.py:1223-1382`（`_filter_on_link_type`）
- 证据：实现 BFS + P2P 过滤 + 虚拟根节点，代码内注释标注已知限制（未区分 root/path 入口、未用 PSFilterVisitor、返回虚拟根而非节点替换）。最小可用。
- 建议修复：接入 PSFilterVisitor 完整对齐。
- 与前两轮关系：前轮部分修。

### P2-12 delete_config 返回 200+body 而非 204
- 严重级：MED（可视作 LOW，此处保留 MED 以对齐状态码要点）
- 类别：清单#21
- 文件：`app/routers/product_configurations.py:140` `return {"status":"deleted"}` | Java对照：DELETE 返回 `Response.noContent().build()`（204 no body）
- 建议修复：`return Response(status_code=204)`。
- 与前两轮关系：前轮已标未修。

---

## LOW
- **P2-13** updateAuthor/updateAuthorName 声明未赋值（schema/product）。前轮已知。
- （信息）P2-01/02/03/04/05/07/09/10 前轮问题第3轮已修复并本轮确认（delete_instance 清 7 子表 + 孤儿；`_ci_to_dict` 参数错序已移除改 `svc.search_numbers`/`build_ci_dto`；getPathData 三项填充；get_product_instance iteration 全字段；hasPathData 正则精准定位 `-u/-s`；vault 用 product-instances 前缀）。

---

## 已核对一致的要点
| 清单# | 结论 |
|-------|------|
| #1 | SELECT/DELETE 列名与 `\d` 一致，**唯 `_attach_master_to_instance` INSERT 列名错（P2-14）** |
| #5 dtype | `_replace_instance_attributes`/`_sync_path_data_attributes` 均写 dtype，`_infer_attr_dtype` 覆盖 7 种 + fallback |
| #4 级联删除 | delete_ci 检查 baseline/config/instance 约束；delete_instance 清 7 子表；delete_path_data 清 P2P link |
| #10 vault路径 | product-instances 前缀，对齐 Java |
| #13 NULL容忍 | `_build_component` 处理 None revision/iteration |
| #16 SQL注入 | 全绑定参数，无风险 |
| #15 状态码 | DELETE 用 204、POST 用 201（P2-12 例外） |

## 冒烟验证
| 端点 | Python(8009) | Payara(8005) | 一致 |
|------|--------------|--------------|------|
| GET /products/numbers?q=ACLCI | 返回 CI 列表 | 同 | ✅ |
| GET /products | 完整 CI DTO | CI DTO | ✅（PY 多 designItemName 等，不阻断） |
| GET /product-instances | `[]`（GD50 无实例） | `[]` | ✅ |

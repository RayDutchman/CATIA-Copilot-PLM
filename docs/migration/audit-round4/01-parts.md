# 域1 Parts 零件 审计报告（第4轮）

> 生成日期：2026-07-12 ｜ 范围：`docdoku-plm-server-py` 零件迁移代码 vs Java/Payara
> 方法：explore subagent 逐端点对照 Java 源 + information_schema 核实 + GD50 验证；主 agent 复核关键项
> 基准 workspace = GD50 ｜ **只读审计，未做任何修复**

## 结论
**0 CRITICAL / 2 HIGH / 3 MED / 2 LOW**。第3轮重构修复了第2轮 5 项（P1-01/03/04/05/09）。本轮新发现 2 个 HIGH（newVersion 描述写错版本、remove_tag 缺 ACL 写权限）。

---

## HIGH

### P1-13 remove_tag 完全缺失 ACL 写权限检查（权限绕过）
- 严重级：HIGH
- 类别：清单#6（权限检查逐行对比）
- 文件：`app/services/product_manager.py:1166-1179`（remove_tag）；`app/routers/part.py` remove_tag handler | Java对照：`PartResource.java` removeTag → `productService.removeTag()` throws AccessRightException（EJB 内 checkWorkspaceWriteAccess）
- 证据（主 agent 已核实）：`add_tag`(1142)/`set_tags`(1118) 均接收 `current_user_login` 并调 `check_write_access`，但 `remove_tag(db, ws, pn, ver, label)` **签名无 `current_user_login`，函数体无任何权限检查**，直接 `db.execute(...delete...)`。任何工作区成员可删任意可见零件标签。
- 建议修复：`remove_tag` 补 `current_user_login` 参数 + `check_write_access` 调用，router 传入 `current_user.login`。
- 与前两轮关系：**新发现**（第2轮"路由接线一致"仅指 Depends 注入，未深入 service 方法级权限）。

### P1-12 create_new_version 描述写到旧版本 + 忽略 workflowModelId/acl/roleMapping
- 严重级：HIGH
- 类别：清单#2（DTO字段对齐/逻辑走样）、#17（端点覆盖缺口）
- 文件：`app/routers/part.py:193-194`；`app/services/product_manager.py:1071-1108`（create_new_version）、`:1990-1995`（set_new_version_description） | Java对照：`PartResource.java:460-489` createPartRevision(revisionKey, description, workflowModelId, userEntries, userGroupEntries, userRoleMapping, groupRoleMapping)
- 证据：`new_version_part` 从 URL 取 `version="A"` → `create_new_version` 生成 "B" → 随后 `set_new_version_description(db, ws, number, "A", body["description"])` 用**旧版本号 A** 调用 → 描述被写到版本 A 而非新版本 B。且 `create_new_version` 仅复制旧 description，忽略 Java 会写入的 workflowModelId/acl/roleMapping。
- 建议修复：`create_new_version` 直接接收 description/workflow_model_id/acl/role_mapping 并写到新版本行。
- 与前两轮关系：新发现（P1-08 的深层子问题）。

---

## MED

### P1-06 status NULL → "WIP" 而非 null
- 严重级：MED
- 类别：清单#2/#8
- 文件：`app/services/part_mapper.py:256`（map_revision）+ schema `status: Optional[str] = "WIP"` | Java对照：`PartRevisionDTO.java:112` `RevisionStatus` + `@JsonbProperty(nillable=true)`，NULL 序列化为 null
- 证据：`STATUS_MAP.get(None, "WIP")` 把 NULL 状态映射为字符串 "WIP"，Java 返回 null。
- 建议修复：status 为 None 时返回 None，不在 mapper/schema 兜底。
- 与前两轮关系：前轮已知，仍未修复。

### P1-14 product_manager 服务层硬编码 HTTPException（2 处）
- 严重级：MED（与域2 P2-15 同源，去重后归域2定级 HIGH，本处仅记录零件视角）
- 类别：清单#7（异常一致性）
- 文件：`app/services/product_manager.py:1895`（retry_conversion, "No native CAD file uploaded"）、`:2007`（get_leaf_instances, "partKey 格式应为..."） | Java对照：Java 该两处在 REST 层判断/校验，Service 不抛 HTTP 异常
- 证据：Phase0 `check_hardcoded_exceptions.py` 命中；两处均 `from fastapi import HTTPException` 局部导入。
- 建议修复：改抛 WrongInputException/领域异常，或将格式校验上移路由层（`part.py` 的 `_split_part_key` 已有）。
- 与前两轮关系：新发现（Phase0 线索确认）。

### P1-08 create_new_version 缺 workflowModelId/acl/roleMapping（并入 P1-12）
- 严重级：MED（功能缺口，已在 P1-12 一并描述）
- 与前两轮关系：前轮已知。

---

## LOW
- **P1-07** tags 始终返回 `[]`（`part_revision.py:28` + `part_mapper.py:263`）；Java 无标签时行为可能一致，影响极小。前轮已知。
- **P1-10** CADInstanceDTO 含额外矩阵字段；向后兼容无害。前轮已知。

---

## 已核对一致的要点
| 清单# | 结论 |
|-------|------|
| #1 裸SQL表名列名 | `partrevision_tag`/`partiteration_attribute`/`instanceattribute`(14列)/`partusagelink`/`modificationnotification`(14列)/`partmaster.partnumber` 全部与 information_schema 吻合 |
| #3 硬编码桩 | 零件路由 `return []`/`return {}` 均为合法空响应，无吞异常 |
| #4 级联删除 | `delete_revision` 清 modificationnotification/partiteration_attribute/conversions/attached_files/geometries + vault；`undo_checkout` 清 5 类 join 表 + 孤儿行，完整 |
| #5 INSERT dtype | PartMaster/Revision/Iteration 无 dtype 判别列（与 instanceattribute 不同），正确 |
| #9 深拷贝 | checkout 对 instanceattribute/partusagelink/cadinstance 均 INSERT...RETURNING 新行，clone 语义正确 |
| #10 vault路径 | `{ws}/parts/{pn}/{ver}/{it}/nativecad|attachedfiles/{file}`，**无 geometry/ 子目录**，正确 |
| #16 SQL注入 | text() 列名/表名走硬编码白名单，值走 :param |
| P1-01/03/04/05/09 | 前轮问题第3轮已修复（set_tags 统一解析 / filter_by_baseline 返回单 DTO / get_latest_revision 补 check_read_access→403 / SubResource DELETE 端点补齐 / add_tag 补 check_write_access） |

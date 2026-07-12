# FastAPI 迁移全量审计总报告

> 生成日期：2026-07-11
> 范围：`docdoku-plm-server`（Java EE Payara）→ `docdoku-plm-server-py`（FastAPI）后端迁移代码
> 方法：以 `docs/full-audit-checklist.md` 22 条要点为准绳，8 个域 explore subagent 逐端点对照 Java 源码 + DB `information_schema` 真值核实
> 交付物：**仅审计报告，不含修复**。修复须另开任务逐条确认。

## 一、审计范围与方法

- **代码规模**：63 router（约 11,365 行）+ 52 service（约 8,137 行），对应 49 个 Java `*Resource.java`
- **环境**：Workspace_2 已删，DB 唯一有数据 workspace=GD50（31 partmaster / 1 configurationitem / 0 documentmaster）。审计以**代码对照**为主，GD50 做在线对拍佐证。
- **关键前提**：tracker.csv 528 项全标"已完成"**不可信**（清单要点19），审计不采信状态列，逐端点核对。
- **主 agent 复核**：对 4 个"运行时必崩"型列名 CRITICAL（B-1/B-2/B-3/X-1）已亲自用 information_schema + 读源码二次核实，**全部属实**。其余 CRITICAL（逻辑类）置信度较高但建议修复前逐条复核。

## 二、问题总览

| 域 | 报告 | CRITICAL | HIGH | MEDIUM | LOW |
|----|------|:--:|:--:|:--:|:--:|
| Parts 零件 | [01-parts.md](01-parts.md) | 1 | 2 | 6 | 3 |
| Products 产品结构/实例/配置 | [02-products.md](02-products.md) | 5 | 5 | 5 | 1 |
| Documents 文档 | [03-documents.md](03-documents.md) | 4 | 4 | 4 | 1 |
| Workspace/用户/权限/管理 | [04-workspace-user-auth.md](04-workspace-user-auth.md) | 3 | 4 | 7 | 3 |
| Baselines/Effectivity | [05-baselines-effectivity.md](05-baselines-effectivity.md) | 5 | 2 | 5 | 3 |
| Workflow/Change/Tasks | [06-workflow-change-tasks.md](06-workflow-change-tasks.md) | 3 | 8 | 8 | 2 |
| Query/Importer 引擎 | [07-query-importer.md](07-query-importer.md) | 3 | 2 | 4 | 2 |
| 横切/其他 | [08-crosscutting.md](08-crosscutting.md) | 2 | 3 | 8 | 1 |
| **合计** | | **26** | **30** | **47** | **16** |

> 机器扫描原始结果见 [00-machine-scan.md](00-machine-scan.md)。注：Q-5 与 P-6 为同一处（post_queries `{"id":0}`），去重后独立问题约 118 个。

## 三、CRITICAL 清单（26 项，按域）

### 已主 agent 二次核实属实（运行时必崩，最高优先级）
| # | 位置 | 问题 | DB 真值 |
|---|------|------|---------|
| B-1 | models/product/effectivity.py:18-20 | ORM `startlot/endlot/creationdate/type_effectivity` 伪列 | 实为 `startlotid/endlotid`，无 creationdate/type_effectivity |
| B-2 | routers/effectivity.py:139-142 | INSERT partrevision_effectivity 用 `workspace_id` | 实为 `partmaster_workspace_id` |
| B-3 | services/effectivity_manager.py:15,98 | effectivity 表 `WHERE workspace_id` | effectivity 表无此列 |
| X-1 | routers/share.py:80 | SELECT sharedentity `expire_date` | 实为 `expiredate`，端点每次 500 |

### 其余 CRITICAL（逻辑/桩/级联/权限，高置信度待复核）
| # | 位置 | 问题 |
|---|------|------|
| P-1 | services/product_manager.py:1283 | checkout 复用 PartUsageLink component_id，更新子件时 FK 违反 500 |
| PR-CRIT-1 | services/product_structure.py:679 | 产品配置写错表（partsubstitutelink 应为 prdcfg_substitutelink） |
| PR-CRIT-2 | models/configuration/product_configuration.py | ProductConfiguration 未继承 ProductBaseline.id，读写主键不一致 |
| PR-CRIT-3 | routers/product_instances.py:252 | rebase_instance 完全空操作桩 |
| PR-CRIT-4 | routers/product_files.py:14 | 产品实例文件上传不注册 BinaryResource DB 行 |
| PR-CRIT-5 | routers/product_instances.py:107 | update_instance URL 缺 /{iteration}，不创建新迭代、不处理属性 |
| D-1 | services/document_manager.py:366 | 文档 checkout 缺 linkedDocuments/instanceAttributes 深拷贝 |
| D-2 | document.py / document_template_files.py | 缺 4 个文件 rename/remove 端点 |
| D-3 | services/document_manager.py:672 | update_iteration 忽略 instanceAttributes + 缺 checkout/末迭代校验 |
| D-4 | routers/documents.py:200 | create_document 丢弃 description/templateId/workflow/acl/roleMapping |
| W-1 | routers/admin.py:208 | admin 删工作区仅删 1 行，无级联（workspaces.py 有正确版） |
| W-2 | routers/admin.py:138 | admin 删账户遗漏 ~9 张 FK 关联表 |
| W-3 | services/workspace_manager.py:55 | delete_workspace 单行 stub（定时炸弹） |
| B-4 | services/product_structure.py:652 | delete_baseline 缺 7 张关联表级联 |
| B-5 | routers/document_baselines.py:115 | 文档基线创建缺 snapshotDocuments 校验 |
| WF-1 | routers/workflow.py:60 | aborted-workflow-list 端点语义完全错误 |
| TASK-1 | services/task_manager.py:171 | 任务审批不更新文档/零件 lifeCycleState |
| CH-1 | routers/change_common.py:35 | ACL groupEntries 硬编码空字典 |
| Q-1 | services/query_executor.py:312 | 查询结果缺 checkout-by-another-user 隐藏 → 信息泄露 |
| Q-2 | services/query_executor.py:214 | author.* 分支硬编码 acc.name，email/language 查询错列 |
| Q-3 | routers/parts.py:501 | query-export 只有 GET 简化版，缺 POST QueryDTO + 导出已存查询 |
| X-2 | routers/share.py:206 | 公开共享先查成员身份再验 public，非成员无法访问公开资源 |

## 四、HIGH 清单（30 项，摘要）

- **Parts**：P-2 retryConversion 桩（不实发转换）、P-3 newVersion 缺 body/workflow/acl
- **Products**：PR-HIGH-1 filter 缺 linkType、PR-HIGH-2 list_instances 3D 不按 configSpec、PR-HIGH-3 searchPaths 缺 configSpec、PR-HIGH-4 cascade 缺 configSpec/path、PR-HIGH-5 P2P sourceComponents/targetComponents 恒空
- **Documents**：D-5 六端点 204→200、D-6 缺 POST share、D-7 new_version 丢 role_mapping、D-8 模板 update 桩
- **Workspace**：W-4 GCM 空桩、W-5 remove_user 缺 membership/group 清理、W-6 create_workspace 缺 enabled 策略、W-7 add_user group 参数错位（Query vs body）
- **Baselines**：B-6 缺 3 种 effectivity-based 基线类型、B-7 detail 缺 configurationItemLatestRevision
- **Workflow**：WF-2 列表返回类型错、WF-3 currval 风险、WF-4 缺通知、TASK-2 状态码、TASK-3 checkTask 行为差异、CH-2 update 允许改 name、CH-3 多余 /orders/link、CH-4 iteration 硬编码=1、CH-5 缺 ACL 写权限检查
- **Query**：Q-4 PathData/BOM 导入桩、Q-5 post_queries `{"id":0}` 假成功
- **横切**：X-3 share_manager 用 password 列匹配 uuid（死代码）、X-4 conversion 回调 JWT 过期、X-5 删 tag 未清关联表 FK 违规

## 五、MEDIUM / LOW（47 / 16 项）
详见各域报告。主要类型：状态码 204 vs 200+body（多域普遍）、缺权限检查、缺端点、DTO 字段缺失、事务碎片化 commit、时区处理、裸 SQL 列位置索引脆弱、entity-token 格式等。

## 六、修复优先级建议

1. **P0 — 运行时必崩（立即）**：B-1/B-2/B-3（effectivity 完全不可用）、X-1（share 端点 500）。列名类，改动小、风险低、收益确定。
2. **P0 — 数据丢失/损坏**：D-1（checkout 丢数据）、D-3（属性丢失）、P-1（FK 500）、PR-CRIT-1/2（配置持久化错误）、B-4/W-1/W-2（级联删除孤儿数据）。
3. **P1 — 功能桩/权限**：PR-CRIT-3/4/5、D-2/D-4、TASK-1、CH-1、Q-1/Q-2/Q-3、X-2、W-3。
4. **P2 — HIGH 批量**：状态码对齐、configSpec 分支、通知发送、缺失端点。
5. **P3 — MEDIUM/LOW**：分批清理。

## 七、需用户决策项（非纯 bug）

- **状态码 204 vs 200+body**：多域普遍（P-4、D-5、TASK-2、CH-8、X-9）。是否强制对齐 Payara 204？若前端已适配 Python 的 200+body 则可不改。
- **功能增强 vs 偏差**：CH-3（/orders/link）、TASK-3（checkTask 扩展到零件）是 Python 主动增强，需确认保留还是回退。
- **已知限制**：SNS webhook（X-10）、OAuth ProvidedAccount（X-11）、OnDemandConverter——是否本期实现。
- **checklist 更新**：要点#5（dtype 写入不一致）经核实 `_sync_instance_attributes` 已写 dtype，**已解决**，可更新清单。

## 八、误报排除汇总

各域已排除的机器扫描误报：所有 `缺 NOT NULL id` 均为 SERIAL 自增；`validate_sql_columns` 3 个 UPDATE error 均为 `INSERT ON CONFLICT DO UPDATE SET` 解析误报；`validate_dto_fields` 2 CRITICAL 为 CreationDTO 错配响应 DTO；LOV 表名（lov/lov_namevalue）实际正确；中间件 4 个接线顺序正确；WebSocket 注解正确。`part_geometry_path` 缺失为**真实**问题（X-6，非测试过时）。

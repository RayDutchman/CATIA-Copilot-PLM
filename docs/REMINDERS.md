# Reminders

当前待办、已知问题、阻塞事项。**每次会话开始时检查本文件，收尾时更新。**

---

## 待办

> 📋 **后端迁移剩余缺口不在此列**——完整台账见 `docs/migration/loose-ends.md`。2026-07-10 已完成 PathData/P2P 域 + 全量对比修复 + 用户姓名/权限修复合集，并**新增 Query 自定义查询执行引擎 + Importer 属性导入域（分支 feat/py-query-execution-engine）**。**剩余功能域**：① WebSocket /ws 403 修复；② 种子脚本修复（解阻 10 个 pytest 失败）。本文件只保留**跨领域非迁移**待办。

### 🟠 第二轮全量审计 + 独立复核（2026-07-12，见 docs/migration/audit-round2/00-index.md + FIX-PLAN.md）

> **仅审计未修复**。8 域 subagent 逐端点对照 Java + 独立复核（重新定位实际代码 + DB FK + Payara 对拍）。初判 10C/34H → **复核后 6 CRITICAL / 29 HIGH / 40 MED / 24 LOW**。修复路线见 `audit-round2/FIX-PLAN.md`（5 批）。**需用户确认后进入修复流程。**
>
> **6 个确认真 CRITICAL（批 1，均可直接修复）**：
> - P2-02 search_ci_numbers 参数错序 `_ci_to_dict(db,c)`→500
> - P4-01 文档 _doc_to_dict attachedFiles 硬编码 []（GET 唯一序列化路径）
> - P5-01 delete_workspace 漏删 folder（⚠️ 第一轮 W-1 遗漏抽取函数本身，DB 确认 GD50 有 2 行残留）
> - P5-02 workspaces.py 缺 import Path/settings/indexer_manager→NameError
> - P6-02 change 文档 affected 硬编码 iteration=1→FK 500
> - P6-03 WorkflowActivityDTO complete/inProgress/toDo 等全 0
>
> **4 项 CRIT 降级**：P1-01→MED（前端不调 PUT set_tags）、P2-01→HIGH（GD50 子表空）、P6-01→HIGH（核心状态机已对齐）、P6-04→HIGH（relaunch 仍可用）。**2 项证伪**：P6-05（Java 同 null）、P7-02（Java BomImporter 无实现）。
> **HIGH 最紧要**：权限/安全类 P1-04（信息泄露）、P4-02/04/05/06/07/08、P5-07。
> **复核新增独立 bug**：importer.import_into_parts 返回 errors:[] 丢弃 checkout 错误。
>
> **需用户决策**：① 是否按 FIX-PLAN 进入修复；② 状态码 204 vs 200+body 是否强制对齐（多域重复）；③ PathData 导入（P7-01）、workflow 审批邮件（P6-08）是否本期实现。

### 🔴 全量审计发现（2026-07-11，见 docs/migration/audit/00-index.md，共 26 CRITICAL）

> **修复进行中**，按 `docs/migration/audit/FIX-PLAN.md` 分 8 批（0~7）执行。分支 `fix/audit-remediation`。
>
> **✅ 批次 0 已完成（2026-07-11）**：回归测试门禁恢复。
> **✅ 批次 1 已完成（2026-07-11）**：P0-a 列名必崩（effectivity + share 域 6 项 CRITICAL + 1 HIGH 全部修复）。
> **✅ 批次 2 已完成（2026-07-11）**：P0-b 级联删除（重构 cascade_delete_workspace + B-4/D-9/W-2 补级联，消除 4 处危险单行 stub）。pytest 无新增 fail，在线 smoke 全绿。
> **✅ 批次 3 已完成（2026-07-12）**：P0-c 数据完整性（P-1 零件 checkout 深克隆 PartUsageLink+cadinstance + 连带修 __do_sync_components 孤儿清理；PR-MED-2 rotationType 推断；D-1 文档 checkout 深拷贝 links/attrs+flush；D-3 update_iteration instanceAttributes 替换+校验；D-12 target_workspace_id；D-10 list_folders 只返直接子）。pytest 无新增 fail，在线 smoke 全绿。
> **✅ 批次 4 已完成（2026-07-12）**：P0-d 产品配置架构 + 迭代 undo 级联。brainstorming 定 ProductConfiguration 独立实体方案（方案A）；PR-CRIT-1 create_config 写正确 prdcfg_* 表+delete_config 对称清理；PR-CRIT-2 验证为误报；PR-CRIT-3 rebase 真实实现；PR-CRIT-5 update_instance 补 /{iteration} 就地改（Java 真值）；PR-CRIT-4 upload 建 BinaryResource；P-14/D-14 undo_checkout 级联清子表+抽 _delete_orphan_usage_links 共享方法。pytest 278 passed/1 known-fail，smoke 全绿（Assem1/D14TEST checkout→undocheckout HTTP 200 精确回基线零残留）。
> **✅ 批次 5 已完成（2026-07-12）**：P1 语义 CRITICAL（workflow/task/change/query，4 并行 subagent）。WF-1~4（aborted-list 按持有者查+RETURNING id）、TASK-1/2（完成时更新 revision.status + 204）、CH-1/2/4/5（groupEntriesMap 填充 + 真实 iteration + update 白名单静默忽略 + ACL 写检查接线）、Q-1/2/11（他人签出隐藏末迭代 + 动态 author 列 + fallback 白名单）。**主 agent code review 修 2 处 subagent 隐患**：① Q-1 `iterations.pop()` 因 delete-orphan 级联会在 save=true commit 时真删末迭代 → 加 `db.expunge`（对齐 Java em.detach）；② CH-2 subagent 版对 name/author/initiator 抛 WrongInputException 会破坏前端 save（前端 PUT 带 author+initiator）→ 改为静默忽略（对拍 Java ChangeIssuesResource + change_issue_edition.js）。补 WrongInputException→400 映射。pytest 278 passed/1 known-fail，smoke 全绿。
> **✅ 批次 6 已完成（2026-07-12）**：P2 HIGH/MEDIUM 机械类（parts/documents/workspace/crosscutting，4 并行 subagent）。P-2~P-8+Q-3/Q-5、D-2~D-8/D-11/D-13、W-4~W-7/W-9/W-11/W-14、X-5~X-9/X-12。**主 agent 修 2 处 subagent 隐患**：① X-6 subagent 把 converter/binary_storage 的 GLB 路径改成 `geometry/{quality}.glb`，与生产扁平 UUID 存储不符会破坏所有存量零件 3D 预览 → 回退这两文件，仅保留 vault.part_geometry_path 辅助函数（供 test_vault 收集）；② 发现 workspaces.py 有与 tags.py **完全重复的 tag 路由**（先 include 而遮蔽 tags.py，使 O 的 X-5/X-9 成死代码）→ 移除 workspaces.py 5 个重复路由，tags.py 成唯一 owner，delete tag 改裸 SQL 避免 ORM M:N 重新 INSERT 关联行。**顺带清零 test_i18n_bypass 长期 known-fail**（part.py 3 处 + parts.py 2 处硬编码 detail 改 i18n 异常类）。pytest（移除 test_vault ignore）= **282 passed / 1 skipped / 0 failed**，smoke 全绿。
> **✅ 批次 7 已完成（2026-07-12，末批）**：P3 configSpec / 基线类型 / 缺失端点（2 并行 subagent：P products/configSpec，Q baseline 路由，文件不相交）。PR-HIGH-1~5（filter/paths/cascade/3D-instances 贯通 configSpec+diverge+path、P2P decodePath）、PR-MED-1（path-data dtype）、PR-MED-4（instance acl）、B-5/B-10（doc 快照过滤+NotAllowedException66）、B-6（EFFECTIVE_* 三类型 best-effort）、B-7（detail 补 configurationItemLatestRevision 字符串+hasObsolete、删 configurationItemWorkspaceId，对拍 Payara 确认 String）。**B-15 判定为误报**（export-files ZIP 已存在、P2P 路径已对齐），回退 subagent 重复端点。**主 agent 修 2 处预存 bug（对拍 Payara 后）**：① 4 个 PSFilter `filter_links` 访问不存在的 `PartUsageLink.substitutes` → diverge=true 必 500，加 getattr 守卫；② `delete_baseline` 先删 partcollection 后 flush baseline → FK 500，改为先 delete+flush baseline 再删集合。pytest **282 passed / 1 skipped / 0 failed**，在线 smoke + Payara(:8005) 对拍全绿。**🎉 FIX-PLAN 批次 0~7 全部完成。**
> **✅ 批次 7 后续（2026-07-12，用户复核）**：① **baseline `type` 对齐 Payara**——确认产品基线返回 int 而 Payara 返回枚举名字符串（且前端 `isReleased()` 按字符串比较，int 是潜伏 bug），已改为输出枚举名 + DTO type→str（对拍一致）。② **镜像持久化**——批 5~7 均 `docker cp` 热部署，已 `docker build`+`compose up --force-recreate` 重建 back-py 镜像并 recreate 容器，smoke 确认所有修复随镜像持久化（不再受 recreate 回退）。
> **✅ 批次 7 后续②（2026-07-12，effectivity 深化 — 用户选「Payara 对齐/单一入口」）**：将原 dead code 的 config-spec 有效性基线路径**激活**为 EFFECTIVE_DATE/SERIAL/LOT 的实际实现（3 个 create 端点统一走 `product_baseline_service` 单一入口 + `BaselineCallbacks` 对齐 Java 抛 `NotAllowedException49/48/51/50` all-or-error + 移除裸 SQL 兜底 + 补 `PartRevision.effectivities` relationship）。**在线对拍 Payara(:8001) 连带发现并修复两处更深差异**：① **有效性判别值** — EclipseLink 默认 `@DiscriminatorValue`=实体类名，Payara 实测写 `dtype="DateBasedEffectivity"`，FastAPI 原写 `"D"/"S"/"L"` → 两系统互不可读（isinstance 失败），已全端（模型 identity + 写入 + 读取）统一改为全类名；② **异常 HTTP 码** — Java `NotAllowedException`/`EntityConstraintException` Mapper 均返回 **400**，FastAPI 误映射 403，已改（AccessRightException 保持 403）。**对拍结果**：GD50/ceshi 整棵树 10 件挂有效性，date-in 两端 DB 均落 10 件 baselinedpart、date-out 两端均 49。原 decision-point「无匹配→空基线」前提**经对拍证伪**（Payara 是 all-or-error）。pytest 282 passed，已重建镜像持久化。commits 6967c80/f60f6df/f5ed730。

>
> 以下为待修的最高优先级 P0：
> - [x] **B-1/B-2/B-3 effectivity** → ✅ 批 1
> - [x] **X-1/X-2/X-3 share** → ✅ 批 1
> - [x] **B-4/W-1/W-2/W-3 级联删除/账户删除** → ✅ 批 2（含 D-9 模板级联）
> - [x] **P-1 PartUsageLink 浅拷贝**：checkout 复用 component_id，更新子件 FK 500（与已修的 instanceattribute FK 是不同表）→ ✅ 批 3（深克隆 + 孤儿清理）
> - [x] **D-1/D-3 文档 checkout/update 数据丢失** → ✅ 批 3。
> - [x] **PR-CRIT-1/2/3/4/5 产品配置架构 + 实例 rebase/update/upload** → ✅ 批 4（PR-CRIT-2 验证为误报）
> - [x] **P-14/D-14 undo_checkout 级联** → ✅ 批 4
> - [x] **批 5 P1 语义 CRITICAL** → ✅ 批 5：WF-1（aborted-list 语义）、TASK-1（审批完成更新 lifecycle）、CH-1（ACL groupEntriesMap 空）、Q-1（他人签出隐藏末迭代）、Q-2（author.* 硬编码 name）全部修复；连带 WF-2/3/4、TASK-2、CH-2/4/5、Q-11。
> - [x] **功能桩/权限类（批 6 起）**：~~Q-3（query-export POST）、D-2/D-4（缺端点/字段）、状态码 204 批量~~ → ✅ 批 6 完成（parts/documents/workspace/crosscutting 全部 HIGH/MEDIUM 机械类）；~~剩批 7：configSpec 分支（PR-HIGH-1~5/PR-MED）、B-5/B-6/B-7/B-15/B-10 基线类型/快照校验~~ → ✅ **批 7 完成**（B-15 判定误报）。**FIX-PLAN 0~7 全部完成，仅余零散 LOW。**
> - [x] **🆕 批 4 smoke 新发现（独立预存 bug）→ ✅ 已修复（2026-07-12）**：文档删除端点 `delete_revision` 的全局孤儿清理 SQL 未排除 `prdinstiteration_attribute`/`pathdataiteration_attribute`，存在产品实例属性时删文档触发 FK 500。已对拍 Payara（`DocumentIteration` orphanRemoval+CascadeType.ALL 精确级联）后改为**精确删除本 revision 自己的 instanceattribute/documentlink**（逐 id 无其它引用才删）+ 补 LOV 子值 `attribute_namevalue` 清理；documentlink 同款全局 bug 一并修。commit 8457305。
>
> HIGH(30)/MEDIUM(47)/LOW(16) 详见各域报告。需用户决策项：状态码 204 vs 200+body 是否强制对齐、CH-3/TASK-3 功能增强是否保留、SNS/OAuth 是否本期实现。

### 高优先级

- [x] **Workflow role_mapping 结构性修复 (2026-07-07)** — 多对多表已接入
- [ ] **3D 预览不显示** — Three.js r90 交互差异，需升级或抓包
- [x] **3D 预览三根因修复（2026-07-11）** — instances stub / geometryFileURI 逗号拼接 / CADFileView OBJ→GLB，已部署验证 GD50_Frame-A instances 正确返回 + Product1-A 9 子组件递归遍历
- [x] **update_iteration 3 项辅助功能已补齐 (2026-07-07)**

### 中优先级

- [ ] **reindex 邮件通知 i18n** — 基础实现已完成，待补全多语言资源
- [x] **Decimation 减面优化（2026-07-11 以 LOD 生成替代）** — conversion-service-py 已内置三级 LOD（deflection 0.05/0.30/1.00），失败降级
- [ ] **Windows 重启后 Docker 端口失效** — `wsl --shutdown` 恢复
- [x] **WebSocket /ws 403（2026-07-10 已修复）** — 路由路径对齐 `/docdoku-plm-server-rest/ws` + 补 `WebSocket` 类型注解，握手 101 + AUTH_OK
- [x] **Conversion Service Python 化收尾（2026-07-11）** — conversion-service-py 完整接管：docker-compose.yml 本地 build、LOD 三级精度（deflection 0.05/0.30/1.00）失败降级、旧 Java 目录标注废弃。容器已重建部署，Kafka 连接正常。

---

## 用户报出的 Bug（2026-07-10 更新）

| # | 问题 | 状态 | 备注 |
|---|------|------|------|
| 1 | ~~删除工作区"未找到用户 test1"~~ | ✅ Fixed | deps.py 补 admin_login + usergroup_user 组检查 |
| 2 | ~~创建基线 TypeError + 校验缺失~~ | ✅ Fixed | BFS 校验 + response 补 author |
| 3 | 通知设置不持久化 | ⏳ 待确认 | API 实现正确，可能是前端权限问题 |
| 4 | Payara JPA 缓存 8000/8005 权限互相不可见 | ⏳ 已知 | EclipseLink L2 缓存架构问题 |
| 5 | ~~effectivities 500~~ | ✅ Fixed | GET + 写路径全部修复（批 1：B-1/B-2/B-3/B-9/B-12） |
| 6 | ~~用户列表显示 login 而非姓名~~ | ✅ Fixed | tasks/doc_baselines/product_structure 全量补 Account.name |
| 7 | ~~零件创建 422 (camelCase)~~ | ✅ Fixed | PartCreationDTO 补 Field alias |
| 8 | ~~零件列表"显示全部" 422~~ | ✅ Fixed | length ge=1→ge=0 对齐 Payara pMaxResults==0 |
| 9 | ~~admin 账号前端崩溃 (CoWorkersAccessView)~~ | ✅ 已定位 | 前端 bug（4 个 main.js 缺 admin guard），非后端 |
| 10 | ~~export-files 3 端点 500~~ | ✅ Fixed | br.fullname/pi.nativecadfile_fullname/bd.target_docrevision_version |
| 11 | ~~LOV 500~~ | ✅ Fixed | listofvalues→lov 表名修正 |
| 12 | ~~groups 创建 500~~ | ✅ Fixed | create_group 补 db.flush() |

---

## 已知限制

- **CATIA 原生格式不支持转换** — 需预先导出 STEP/STL
- **back 容器 JVM 参数需两次重启** — Payara 特性
- **~~Conversion service Decimation 持续失败~~** — ✅ 已修好（2026-07-11 以 LOD 三级生成替代减面）
- **vault 目录属主问题** — back-py 容器以 root（uid 0）身份运行，往 `docdoku-plm-docker/data/vault` 写新文件/子目录时，落到 host 上属主为 `root:root`，host 用户 chenweibo（uid 1000）无写权限。真实上传/转换回调后新建的 `{ws}/parts/...` 目录会变回 root 属主。**测试已用 `temp_vault` fixture 隔离**（写临时目录，不碰真实 vault），故不影响 pytest；但若手动在 host 侧操作真实 vault 遇到 `Permission denied`，用 `docker exec docdoku-plm-docker-back-py-1 chown -R 1000:1000 /var/lib/docdoku/vault/{ws}` 修属主。
- **ssl-proxy(:8000) 未代理无 ws 前缀路由（2026-07-12 发现）** — `POST /parts/queries`（无 `/workspaces/{ws}` 前缀版）在 FastAPI（直连 :8009）存在且正常返回 400，但经 nginx ssl-proxy(:8000) 返回 502「No backend configured for this path」。属**反向代理路由配置**问题（nginx location 未覆盖该路径），非应用 bug。前端实际使用带 ws 前缀的 `POST /workspaces/{ws}/parts/queries`（正常）。如需暴露无前缀版，需在 ssl-proxy 的 nginx conf 补 location。低优先级。

---

## 已解决（近期）

- [x] **2026-07-11 删除工作区遗漏 binaryresource + vault 文件修复（back-py）**:
  - 症状：删 GD50 工作区→重建→上传附件报 409 `文件已存在`
  - 根因：`delete_workspace` 只按 workspace_id 级联删 DB，遗漏 ① `binaryresource` 表（无 workspace_id 列，主键 fullname，残留 102 行）② vault 磁盘文件夹（从不删）；`save_attached` 查 BinaryResource DB 记录判重 → 409
  - Payara 比对：`deleteWorkspace` = removeWorkspace（BinaryResource 靠 PartIteration JPA orphanRemoval 级联）+ `deleteWorkspaceFolder`(FileUtils.deleteDirectory) + 删 ES 索引；Payara 该操作 `@Asynchronous`
  - 修复 A：级联末尾 `DELETE FROM binaryresource WHERE fullname LIKE '{ws}/%' ESCAPE '\'`（转义对齐 WorkspaceDAO.java:130）
  - 修复 B：commit 后 `shutil.rmtree(VAULT_PATH/ws)`，失败仅记日志（Python 端保持同步）
  - docker cp 部署 back-py + 重启；存量 GD50 用修复后 delete 重删即清净

- [x] **2026-07-11 零件迭代更新 500（实例属性 FK 冲突）修复（back-py）**:
  - 症状：CATIA Copilot 同步更新零件 `PUT .../parts/{pn}-{ver}/iterations/{n}` 报 500 `ForeignKeyViolation fk_partiteration_attribute_instanceattribute_id`
  - 根因：checkout 创建新迭代时实例属性浅拷贝（新迭代复用旧迭代同一 instanceattribute 行），更新时删该行触发 FK 冲突（另一迭代仍引用）
  - 已与 Payara Java 逐条比对确认：Java `checkOutPart` 对每属性 `clone()+persist` 深拷贝独占，更新靠 orphanRemoval 删本迭代行
  - 修复 A（`_copy_iteration_files`）：检出复制实例属性改深克隆（INSERT...SELECT...RETURNING 新 id）
  - 修复 B（`_sync_instance_attributes`）：删孤儿前查是否被其它 partiteration_attribute 引用，共享则跳过，兜底 + 修复存量坏数据（更新后自愈）
  - docker cp 部署 back-py + 重启

- [x] **2026-07-11 SQL 列名/表名批量修复 + DTO 缺字段修复（back-py）**:
  - 修复 `validate_sql_columns.py` 报的 34 处 raw SQL 错误（14 文件）：attributes/document/product_instances/products/tasks/cascade_action/instance_body_writer/notification/subscription/part_notification/organization/product_manager/part_workflow/webhook；均先经 information_schema 核实真实列名/表名
  - 修复 3 个 CRITICAL DTO 缺字段（ConversionResultDTO.partIterationKey / UserDTO.membership / WorkspaceWorkflowCreationDTO.workflow），消除 422
  - docker cp 部署 back-py + 重启，启动无导入错误
  - ⚠️ 遗留：validate_sql_columns.py 3 处 `UPDATE SET` 误报（正则误匹配 `ON CONFLICT DO UPDATE SET`）+ 14 处自增 id NOT NULL 误报，建议后续改进脚本正则
  - ⚠️ validate_dto_fields.py 2 处 CRITICAL（PathDataIterationCreationDTO.partLinksList / ProductBaselineCreationDTO.author）为脚本把请求 CreationDTO 误映射到响应 DTO，缺字段属响应侧，非真实 422，未处理


- [x] **2026-07-10 工作区删除 500 + WebSocket 403 修复**（分支 feat/py-query-execution-engine）:
  - 删除工作区：手写级联补全（对齐 WorkspaceDAO.removeWorkspace，replica 模式关 FK 触发器），保留 account/credential/usergroupmapping，仅删 userdata；对 Workspace_2 真实数据非破坏性验证残留引用全 0
  - WebSocket：路由路径 `/docdoku-plm-server-rest/ws` + 补 `WebSocket` 注解（原 FastAPI 误判 websocket 为必填 query 参数），握手 101 + AUTH_OK
  - 注：`test_query_save` 因用户删除"测试工作区"导致其硬编码依赖（userdata e@测试用工作区）缺失而失败——数据/测试脆弱性，非代码回归；归入种子脚本待办

- [x] **2026-07-10 Importer 属性导入域**（分支 feat/py-query-execution-engine）:
  - Excel 解析器（对齐 ExcelParser.java）+ 属性合并工具（merge/LOV）+ Import 记录 CRUD
  - ImporterService 属性导入编排（checkout→dtype 写入→checkin，错误门控）+ dry-run 预览
  - 5 个 REST 端点接入 `/workspaces/{ws}/parts/...`；仅 .xlsx 属性导入（BOM 保留 stub）
  - 最终评审 3 项 MUST-FIX 修复（列名白名单防注入 / response_model / 记录顺序）
  - pytest 272 passed（+83）；docker cp 部署 + 线上冒烟全链路通过
  - ⚠️ 设计分歧：`_write_iteration_attributes` 写 dtype，`_sync_instance_attributes` 不写（详见 loose-ends 二）

- [x] **2026-07-10 Query 执行引擎**（分支 feat/py-query-execution-engine）:
  - 查询保存（递归 queryrule 树）+ PartRevision 执行器（前缀路由/operator/属性 EXISTS）
  - PathData 执行器（pd-attr-\*）+ context PBS 过滤 + mergeRows + QueryResult 序列化
  - runCustomQuery 端点（run/save/export）；pytest 189 passed（+22）；docker cp 部署 + 线上冒烟通过

- [x] **2026-07-10 全量修复合集**（67 文件，c668d31）:
  - PathData/P2P 域完整实现（18 端点 + Service + DFS 环检测）
  - 全量对比修复：export-files SQL 列名、LOV 表名、effectivities 列名、groups FK、parts length=0
  - 用户姓名全量修复：tasks/doc_baselines/product_structure/products
  - 权限 bug + deps 访问控制对齐 + PartCreationDTO camelCase
  - baseline 完整修复（校验 + 响应 + parts 端点）
  - 4 个 FA 自创端点删除
  - 对比脚本增强（158 端点 + 错误文本对比 + 行为测试）
  - 176 passed / 1 skipped / 行为测试 10/10

- [x] **审计遗留三项处理 (2026-07-08)**:
  - check_write_access null-ACL 全覆盖
  - extra=forbid 静默 500 — 7 项风险修复
  - 176 passed / 1 skipped，线上 5 端点 200/204 无 500

- [x] **审计修复 B1-B7 全量完成 (2026-07-07)** — 12/13 发现已修复（见 audit-report.md）:
  B1: 级联删除 8 表 + 模板 + Workflow Tasks
  B2: ACL 写权限 + 组成员校验 + 签出保护 + InstanceAttributeTemplates
  B3: 39 NotFound→404 + 补全 2 路由
  B4: 文档/零件/变更 DTO 字段补全
  B5: Workflow admin绕过 + SequentialActivity + status移除
  B6: 7 个 raise 补齐（NotAllowed42 + AccessRight × 5 + mask）
  B7: 6 实现 + 12 STUB 标注 + 6 TODO 清理 → 0 TODO 残留
  176 passed, 1 skipped — 全程零回归

- [x] **P4B WebSocket + Extension 全量迁移 (2026-07-07)** — WS /ws 端点 + Chat/Collaborative/Status/WebRTC 模块 + EXT converters/importers DTO

- [x] **P3B Router + Export 迁移 (2026-07-07)** — P3B-A (8 端点) + P3B-B (15 文件 utility/导出)

- [x] **P2B 服务全量迁移 (2026-07-07)** — Configuration 域 + Listeners + Products + Documents + Indexer + Validation + GCM

- [x] **CSV tracker 524/524 清零 (2026-07-07)**

- [x] **Elasticsearch 全文搜索 (2026-07-06)** — 9 个 service 文件（索引管理/查询/映射/提取），ES 优先搜索 + DB fallback

- [x] **文档审计体系搭建 (2026-07-07)** — DOCS_INDEX.md + 归档 17 个过时 superpowers 文件

- [x] **throw-matrix 补齐 + i18n by pass 审计** — 51/55 throw matrix 对齐

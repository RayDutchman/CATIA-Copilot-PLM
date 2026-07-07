# 设计：P1b 零件文件 + 转换回调 + 状态管理 + 搜索

日期：2026-07-04
状态：设计已确认，待写实现计划
路线图阶段：P1b（见 `docs/superpowers/fastapi-migration-roadmap.md`）

## 背景

P0（基础设施）、P1a-core（零件 CRUD）、P1a-align（行为对齐 i18n）已完成。P1a 只覆盖零件的元数据 CRUD 与签出签入，**文件相关功能仍全部走 Payara**。本阶段 P1b 迁移零件的文件与状态管理，完成后 Payara 可退出零件模块全部职责。

## 目标

在 FastAPI 实现零件的 5 个功能域，行为与 Payara 一致，前端零改动：
1. 文件上传/下载（nativecad + 附件 + geometry GLB）
2. CAD 转换回调（含转换触发链路）
3. 状态管理（release / obsolete / newVersion）
4. 标签管理
5. 搜索（DB 查询 MVP）

## 范围

**In scope**：上述 5 域，共 9 个新端点。转换回调迁移到 FastAPI（选项 B，完整迁移）。

**Out of scope**：
- Elasticsearch 全文搜索——P1b 用 DB LIKE 查询做 MVP，ES 集成推迟到 P5 之后作为独立"搜索增强"子项目（工作量大：旧版 ES 6.6.1 客户端兼容、索引映射还原、双向索引维护、全量重建）。
- 替代品（PartSubstituteLink）相关——留待需要时处理。

## 架构

### 新建文件

| 文件 | 职责 | 依赖 |
|------|------|------|
| `app/routers/part_files.py` | 文件上传/下载端点（`/api/files/{ws}/parts/...`） | file_service |
| `app/services/file_service.py` | vault 写入 + BinaryResource DB 记录；vault 读取 + 流式返回 | vault、models.part |
| `app/services/conversion_service.py` | 转换回调处理（写 GLB、结束转换、装配同步） | vault、models.part |

### 修改文件

| 文件 | 改动 |
|------|------|
| `app/routers/parts.py` | 新增 release/obsolete/newVersion/tags/search/conversion-callback 端点 |
| `app/services/product_service.py` | 新增 release/obsolete/create_revision/tags/search 方法 |
| `app/services/kafka_producer.py` | `send_conversion_order` 增加 `user_token` 参数（见下"转换触发"） |
| `docdoku-plm-docker/front/nginx.conf` | 新增 `/api/files/{ws}/parts/` → back-py location 块 |
| `docdoku-plm-docker/env/conversion.env` | `ENDPOINT` 改为 `http://back-py:8000/docdoku-plm-server-rest/api` |

### 新增端点（9 个）

| 方法 | 路径 | 用途 |
|------|------|------|
| POST | `/api/files/{ws}/parts/{pn}/{ver}/{iter}/nativecad` | 上传 CAD → 触发转换 |
| POST | `/api/files/{ws}/parts/{pn}/{ver}/{iter}/attachedfiles` | 上传附件 |
| GET | `/api/files/{ws}/parts/{pn}/{ver}/{iter}/{subType}/{fileName}` | 下载文件/GLB |
| PUT | `/api/workspaces/{ws}/parts/{pn}-{ver}/conversion` | 转换回调 |
| PUT | `/api/workspaces/{ws}/parts/{pn}-{ver}/release` | 发布 |
| PUT | `/api/workspaces/{ws}/parts/{pn}-{ver}/obsolete` | 废弃 |
| PUT | `/api/workspaces/{ws}/parts/{pn}-{ver}/newVersion` | 创建新版本 |
| PUT/POST/DELETE | `/api/workspaces/{ws}/parts/{pn}-{ver}/tags` | 标签增删改 |
| GET | `/api/workspaces/{ws}/parts/search` | 搜索 |

## 文件上传 + 转换触发流程

对齐 Payara `uploadNativeCADFile → saveNativeCADInPartIteration → convertCADFileToOBJ`：

```
POST /api/files/{ws}/parts/{pn}/{ver}/{iter}/nativecad  (multipart, field=upload)
→ 校验：请求用户是签出用户 && 目标是最新迭代，否则 NotAllowedException4
→ 校验：CAD 扩展名白名单 [stp,step,igs,iges,stl,off,ply,obj,dae,ifc]，否则 400 "Unsupported CAD file format"
→ file_service.save_nativecad:
    vault.write_file(part_nativecad_path(ws,pn,ver,iter,filename), data)
    建/更新 BinaryResource(fullname="{ws}/parts/{pn}/{ver}/{iter}/nativecad/{filename}", dtype="Native")
→ 建 Conversion(pending=true, start_date=now)
→ kafka_producer.send_conversion_order(ws, pn, ver, iter, filename, user_token)
→ 返回 201
```

- multipart 用 FastAPI `UploadFile`，form field 名 `upload`（对齐 Payara）。
- 附件上传 (`attachedfiles`) 同理，dtype="Attached"，**不触发转换**。

### 关键：Kafka 消息必须带 userToken

转换服务 `conversion-service-py/main.py:146` 读 `order.get("userToken")`，回调时用 `Authorization: Bearer {token}`。当前 FastAPI `send_conversion_order` **未传 token**（只有 ws/pn/ver/iter/filename）。P1b 必须：
- `send_conversion_order` 增加 `user_token` 参数，写入 Kafka 消息的 `userToken` 字段。
- 上传端点从当前请求的 JWT（`get_current_user` 已解析，或从 Authorization 头透传）取 token 传入。

## 转换回调流程

对齐 Payara `handleConversionResultCallback`，保留全部已知修复：

```
PUT /api/workspaces/{ws}/parts/{pn}-{ver}/conversion   (conversion 服务调用，Bearer token)
  body: {tempDir, convertedFileLODs:{"0":"xxx.glb"}, box:[xMin,yMin,zMin,xMax,yMax,zMax]}
     或 {errorOutput: "..."}
→ conversion_service.handle_callback:
    findPendingConversionForRevision(pr)：查该 revision 下 pending=true 的 Conversion，
       定位真正发起转换的 iteration（避免 race condition，勿用 last_iteration）
    if errorOutput 含 "no geometry generated":
       endConversion(succeed=true)   # 空几何件（运动学约束件），标记成功跳过
    elif errorOutput:
       endConversion(succeed=false)
    else:
       vault.write_file(part_geometry_path(...), glb_bytes)  # 从 tempDir 取 GLB
       建 BinaryResource(dtype="Geometry", box=[...])
       endConversion(succeed=true)
→ 返回 200
```

- `endConversion(succeed)`：设 `Conversion.pending=false, succeed=<值>, end_date=now`。
- 装配同步（updateUsageLinksInConvertedIteration）：若回调带装配结构则同步，循环装配抛 `EntityConstraintException12`。P1b 首版可只做 GLB 保存 + endConversion，装配同步若 conversion 服务不传结构则不实现（记入债务）。

### 切换时序（关键风险）

改 `conversion.env` 的 ENDPOINT 会让**所有**转换回调立即从 Payara 转向 FastAPI。必须严格按序：
1. 实现并测试 FastAPI 回调端点 + 上传端点 + Kafka userToken
2. 重建并部署 back-py
3. 改 `conversion.env` ENDPOINT=`http://back-py:8000/docdoku-plm-server-rest/api`
4. 重启 conversion 服务
5. 端到端验证：上传 stp → 转换 → 回调 → 前端 3D

顺序错误会导致所有 CAD 转换中断。

## 状态管理

对齐 Payara：

| 端点 | 校验 → i18n key |
|------|----------------|
| release | 已签出→`NotAllowedException46`；无迭代→`41`；已废弃→`38`。成功设 status=1(RELEASED)、release_date、release_user |
| obsolete | 未发布→`NotAllowedException36`。成功设 status=2(OBSOLETE)、obsolete_date、obsolete_user |
| newVersion | 原版本已签出→`NotAllowedException40`；无迭代→`41`；工作流无工作者→`56`。建新 PartRevision + 首迭代 |

## 标签管理

- PUT `/tags`：整体替换零件的标签集合（body 为标签列表）
- POST `/tags`：追加标签
- DELETE `/tags/{tagLabel}`：移除单个标签
- 操作 `partrevision_tag` 关联表（P1a 已建 ORM，列名 `partmaster_workspace_id`/`partmaster_partnumber`/`partrevision_version`/`tag_workspace_id`/`tag_label`）。

## 搜索（DB MVP）

GET `/api/workspaces/{ws}/parts/search`，query 参数对齐 Payara（number/name/type 等）。用 SQLAlchemy `ilike` 对 partmaster 表模糊匹配，返回 PartRevisionDTO 列表。不做 ES 全文分词。

## Nginx 路由变更

当前 parts 正则已覆盖 `/workspaces/{ws}/parts` 下所有子路径（conversion/release/obsolete/tags/search）。**文件路径 `/api/files/` 不匹配**，需新增：

```nginx
location ~ ^/docdoku-plm-server-rest/api/files/[^/]+/parts {
    set $backpy "back-py:8000";
    proxy_pass http://$backpy;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_read_timeout 300s;
    proxy_send_timeout 300s;
    client_max_body_size 500m;
}
```

放在兜底规则之前。正则 `files/[^/]+/parts` 只切零件文件，文档/文件夹的 `/api/files/{ws}/documents/...` 仍走 Payara。

**注意**：转换回调 `PUT /workspaces/{ws}/parts/{pn}-{ver}/conversion` 是 conversion 服务**直连 back-py**（改 ENDPOINT 实现），不经 Nginx；Nginx parts 正则对它不起作用。

## i18n 对齐清单（审计基线）

| 方法 | i18n key |
|------|----------|
| saveNativeCAD/saveFile | 非签出用户或非最新迭代 → `NotAllowedException4` |
| uploadNativeCAD | CAD 白名单不匹配 → 400 "Unsupported CAD file format"（Payara 也硬编码，非 i18n） |
| createPartRevision | 已签出→`NotAllowedException40`；无迭代→`41`；工作流无工作者→`56` |
| releasePartRevision | 已签出→`NotAllowedException46`；无迭代→`41`；已废弃→`38` |
| markObsolete | 未发布→`NotAllowedException36` |
| conversion 装配同步 | 循环装配→`EntityConstraintException12` |

异常体系与 handler 复用 P1a-align 批次 0 的 `app/core/exceptions.py` + `i18n.py`，不新建。

## 测试策略

1. **单元/集成测试**（真实 DB + TestClient）：
   - 上传：建 part→上传 stp→断言 vault 有文件 + BinaryResource(Native) + Conversion(pending)
   - 下载：上传→下载→字节比对
   - 回调：模拟 conversion PUT→断言 GLB 写入 + Conversion(succeed=true)；errorOutput "no geometry" → succeed=true
   - 状态：release/obsolete/newVersion 错误路径断言 i18n key 翻译
   - 标签：增删改后查关联表
   - 搜索：建 part→按 number/name 搜到
2. **Payara 对拍**：文件下载响应头、conversion 状态、release 后 DTO。
3. **端到端转换链路**（P1b 最关键验收）：真实上传 stp → Kafka(带 userToken) → 转换服务 → 回调 FastAPI → 前端看 3D 预览。
4. **前端实测清单**（交用户）：上传 CAD 看转换、下载文件、发布/废弃、打标签、搜索。

## 执行顺序（遵循标准每阶段工作流）

1. ORM 确认（Conversion/BinaryResource/tag 关联已建，补缺失字段如 box 列）
2. 实现文件上传下载 + file_service
3. 实现转换回调 + conversion_service + Kafka userToken
4. 实现 release/obsolete/newVersion/tags/search
5. 行为对齐审计（对齐矩阵）
6. Payara 对拍无 diff
7. 前端实测清单交用户验收
8. **通过后**：加 Nginx files 路由 + 改 conversion ENDPOINT + 重启（严格按切换时序）
9. 更新 REMINDERS（对齐债务）+ CHANGELOG + 路线图状态

## 已知约束与债务

- **转换回调切换时序**：必须先部署 FastAPI 回调再改 ENDPOINT，否则所有转换中断。
- **JWT 过期风险**：conversion 服务用上传时的 user token 回调，长时间转换后 token 可能失效（Payara 遗留问题，非 P1b 引入）。记入债务。
- **装配同步**：若 conversion 服务回调不带装配结构，P1b 只做 GLB 保存，装配同步（updateUsageLinks）留待需要时补。
- **搜索**：DB MVP，ES 全文搜索推迟到 P5 后独立子项目。
- **BinaryResource box 字段**：geometry 的包围盒 [xMin..zMax] 存 BinaryResource 表对应列（P1a ORM 已有 x_min..z_max）。

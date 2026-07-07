# P1b 零件文件 + 转换回调 + 状态管理 + 搜索 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 FastAPI 实现零件的文件上传下载、CAD 转换触发与回调、release/obsolete/newVersion 状态管理、标签、DB 搜索，行为与 Payara 一致，前端零改动，完成后 Payara 退出零件模块全部职责。

**Architecture:** 新建 `part_files` 路由 + `file_service`（vault 写读 + BinaryResource DB 记录）+ `conversion_service`（回调处理）。转换触发经 Kafka（消息重构为嵌套结构 + userToken，topic 改 CONVERT）；转换服务改 ENDPOINT 直连 back-py 回调。状态/标签/搜索扩展 `product_service` + `parts` 路由。异常/i18n 复用 P1a-align 批次 0 基础设施。

**Tech Stack:** FastAPI（UploadFile/StreamingResponse）、SQLAlchemy、Pydantic v2、kafka-python、pytest。

## Global Constraints

- API 路径前缀 `/docdoku-plm-server-rest/api` 不变，前端 Backbone.js 零改动。
- 运行测试：`workdir: docdoku-plm-server-py` → `source venv/bin/activate && pytest tests/ -q`（venv 在子目录）。
- 重建容器：`workdir: docdoku-plm-docker` → `docker compose up -d --build back-py`。
- 测试数据：test1/password 是 `Workspace_2` 成员且 language=zh，写零件测试用它。admin 密码也是 password。
- 异常复用 `app/core/exceptions.py`（`NotAllowedException`/`EntityConstraintException` 等），抛 i18n key，禁止硬编码消息。异常→状态码由 `exception_handlers.py` 统一映射（NotAllowed/EntityConstraint→403）。
- Conventional Commits 提交信息。
- vault 真实布局（已核实）：nativecad=`{ws}/parts/{pn}/{ver}/{iter}/nativecad/{filename}`，附件=`.../{iter}/attachedfiles/{filename}`，几何体 GLB=`.../{iter}/{uuid}.glb`（**无 geometry/ 子目录，非 {quality}.glb**）。
- BinaryResource.dtype：nativecad/附件=`BinaryResource`，几何体=`Geometry`。
- Kafka topic 必须是 `CONVERT`（转换服务监听 CONVERT，非 docdoku-conversions）。
- 转换服务消息为嵌套结构：`{partIterationKey:{workspaceId,partMasterNumber,partRevisionVersion,iteration}, binaryResource:{fullName,name}, userToken}`。
- 上传 multipart field 名 `upload`。CAD 白名单 `[stp,step,igs,iges,stl,off,ply,obj,dae,ifc]`，非白名单→400 "Unsupported CAD file format"。
- 切换时序（严格）：先实现+部署 FastAPI 回调+上传+Kafka → 再改 conversion.env ENDPOINT → 重启 conversion。顺序错则所有转换中断。

---

## 文件结构

**新建：**
- `app/services/file_service.py` — vault 写入 + BinaryResource DB 记录（save_nativecad/save_attached）；vault 读取（get_file_bytes）
- `app/services/conversion_service.py` — 转换回调处理（handle_callback + end_conversion）
- `app/routers/part_files.py` — 文件上传/下载端点（`/api/files/{ws}/parts/...`）
- `tests/test_file_service.py`、`tests/test_conversion_service.py`、`tests/test_part_files_api.py`、`tests/test_part_status.py`、`tests/test_part_tags.py`、`tests/test_part_search.py`

**修改：**
- `app/core/config.py` — KAFKA_CONVERSION_TOPIC 默认改 CONVERT；新增 CONVERSIONS_PATH
- `app/services/kafka_producer.py` — send_conversion_order 重构消息为嵌套 + user_token 参数
- `app/services/product_service.py` — 新增 release/mark_obsolete/create_new_version/set_tags/add_tag/remove_tag/search_parts
- `app/schemas/part.py` — 新增 ConversionResultDTO
- `app/routers/parts.py` — 新增 release/obsolete/newVersion/tags/search/conversion-callback 端点
- `app/main.py` — 注册 part_files 路由
- `docdoku-plm-docker/env/back-py.env` — KAFKA_CONVERSION_TOPIC=CONVERT + CONVERSIONS_PATH
- `docdoku-plm-docker/front/nginx.conf` — 新增 files 路由块
- `docdoku-plm-docker/env/conversion.env` — ENDPOINT 改 back-py（最后一步）

---

## Task 1: config + Kafka 消息重构

**Files:**
- Modify: `docdoku-plm-server-py/app/core/config.py`
- Modify: `docdoku-plm-server-py/app/services/kafka_producer.py`
- Modify: `docdoku-plm-docker/env/back-py.env`
- Test: `docdoku-plm-server-py/tests/test_kafka.py`（改现有）

**Interfaces:**
- Produces: `send_conversion_order(workspace_id, part_number, version, iteration, filename, user_token) -> None` — 发嵌套消息到 topic CONVERT。
- `settings.KAFKA_CONVERSION_TOPIC` 默认 `CONVERT`；`settings.CONVERSIONS_PATH` 默认 `/var/lib/docdoku/conversions`。

- [ ] **Step 1: 改现有 test_kafka.py 断言嵌套结构 + userToken**

替换 `tests/test_kafka.py` 的 `test_conversion_order_message_structure`：

```python
def test_conversion_order_message_structure():
    """发送的消息为嵌套结构，含 partIterationKey/binaryResource/userToken。"""
    with patch("app.services.kafka_producer._get_producer") as mock_get:
        mock_producer = MagicMock()
        mock_get.return_value = mock_producer

        send_conversion_order("WS1", "PART-001", "A", 2, "model.stp", "tok123")

        msg = mock_producer.send.call_args[1]["value"]
        key = msg["partIterationKey"]
        assert key["workspaceId"] == "WS1"
        assert key["partMasterNumber"] == "PART-001"
        assert key["partRevisionVersion"] == "A"
        assert key["iteration"] == 2
        assert msg["binaryResource"]["fullName"] == \
            "WS1/parts/PART-001/A/2/nativecad/model.stp"
        assert msg["binaryResource"]["name"] == "model.stp"
        assert msg["userToken"] == "tok123"
```

同步检查 `test_send_conversion_order_calls_producer`（若调用了旧签名，补 `"tok"` 参数）。

- [ ] **Step 2: 运行测试确认失败**

Run: `source venv/bin/activate && pytest tests/test_kafka.py -q`
Expected: FAIL（旧签名少 user_token；消息是扁平结构）。

- [ ] **Step 3: 重构 kafka_producer.py**

替换 `send_conversion_order` 整个函数：

```python
def send_conversion_order(
    workspace_id: str,
    part_number: str,
    version: str,
    iteration: int,
    filename: str,
    user_token: str,
) -> None:
    """
    发送 CAD 转换任务到 Kafka topic CONVERT。
    消息为嵌套结构，与 conversion-service-py handle_order 契约一致：
      partIterationKey{workspaceId,partMasterNumber,partRevisionVersion,iteration}
      binaryResource{fullName(vault相对路径), name}
      userToken(回调 Bearer 认证用)
    """
    full_name = (
        f"{workspace_id}/parts/{part_number}/{version}/{iteration}"
        f"/nativecad/{filename}"
    )
    message = {
        "partIterationKey": {
            "workspaceId": workspace_id,
            "partMasterNumber": part_number,
            "partRevisionVersion": version,
            "iteration": iteration,
        },
        "binaryResource": {
            "fullName": full_name,
            "name": filename,
        },
        "userToken": user_token,
    }
    producer = _get_producer()
    producer.send(settings.KAFKA_CONVERSION_TOPIC, value=message)
    producer.flush()
    logger.info(
        "已发送转换任务：%s/%s-%s iter=%d file=%s",
        workspace_id, part_number, version, iteration, filename,
    )
```

- [ ] **Step 4: 改 config.py**

`config.py` 中 `KAFKA_CONVERSION_TOPIC` 默认值改为 `"CONVERT"`，并在 VAULT_PATH 下方新增：

```python
    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = "kafka:9092"
    KAFKA_CONVERSION_TOPIC: str = "CONVERT"

    # 转换临时目录（与 conversion 服务共享 conversion-volume）
    CONVERSIONS_PATH: str = "/var/lib/docdoku/conversions"
```

- [ ] **Step 5: 改 back-py.env**

`docdoku-plm-docker/env/back-py.env` 中 `KAFKA_CONVERSION_TOPIC=docdoku-conversions` 改为 `KAFKA_CONVERSION_TOPIC=CONVERT`，末尾新增一行 `CONVERSIONS_PATH=/var/lib/docdoku/conversions`。

- [ ] **Step 6: 运行测试确认通过**

Run: `source venv/bin/activate && pytest tests/test_kafka.py -q`
Expected: 全部 passed。

- [ ] **Step 7: Commit**

```bash
git add docdoku-plm-server-py/app/core/config.py docdoku-plm-server-py/app/services/kafka_producer.py docdoku-plm-server-py/tests/test_kafka.py docdoku-plm-docker/env/back-py.env
git commit -m "feat(py): Kafka 转换消息重构为嵌套结构+userToken，topic 改 CONVERT"
```

---

## Task 2: file_service（vault 写读 + BinaryResource）

**Files:**
- Create: `docdoku-plm-server-py/app/services/file_service.py`
- Test: `docdoku-plm-server-py/tests/test_file_service.py`

**Interfaces:**
- Consumes: `vault`（part_nativecad_path/part_attached_path/write_file/read_file）、`BinaryResource`/`PartIteration`/`part_iteration_binres` model。
- Produces:
  - `save_nativecad(db, ws, pn, ver, iter, filename, data) -> BinaryResource` — 写 vault + upsert BinaryResource(dtype=BinaryResource) + 设 PartIteration.native_cad_file_fullname。
  - `save_attached(db, ws, pn, ver, iter, filename, data) -> BinaryResource` — 写 vault + upsert BinaryResource + insert part_iteration_binres 关联（若无）。
  - `get_file_bytes(ws, pn, ver, iter, sub_type, filename) -> bytes` — 从 vault 读；sub_type 为 None 时读 `{iter}/{filename}`（几何体 GLB），否则读 `{iter}/{sub_type}/{filename}`。

- [ ] **Step 1: 写失败测试**

```python
# tests/test_file_service.py
import os
from app.services import file_service
from app.services.product_service import ProductService
from app.models.part import BinaryResource

WS = "Workspace_2"
svc = ProductService()


def _make_part(db, num):
    from app.schemas.part import PartCreationDTO
    return svc.create_part(db, WS, "test1",
                           PartCreationDTO(number=num, name="t"))


def test_save_nativecad_writes_vault_and_binaryresource(db):
    num = "P1BFS-NATIVE-1"
    _make_part(db, num)
    br = file_service.save_nativecad(db, WS, num, "A", 1,
                                     "m.stp", b"STEPDATA")
    db.commit()
    assert br.full_name == f"{WS}/parts/{num}/A/1/nativecad/m.stp"
    assert br.dtype == "BinaryResource"
    # vault 有文件
    from app.services import vault
    p = vault.part_nativecad_path(WS, num, "A", 1, "m.stp")
    assert p.read_bytes() == b"STEPDATA"
    # PartIteration 关联已设
    it = next(i for i in svc.get_revision(db, WS, num, "A").iterations
              if i.iteration == 1)
    assert it.native_cad_file_fullname == br.full_name
    # 清理
    svc.checkin(db, WS, num, "A", "test1")
    svc.delete_revision(db, WS, num, "A", "test1")
    os.remove(p)


def test_get_file_bytes_reads_back(db):
    num = "P1BFS-READ-1"
    _make_part(db, num)
    file_service.save_nativecad(db, WS, num, "A", 1, "m.stp", b"HELLO")
    db.commit()
    data = file_service.get_file_bytes(WS, num, "A", 1, "nativecad", "m.stp")
    assert data == b"HELLO"
    from app.services import vault
    p = vault.part_nativecad_path(WS, num, "A", 1, "m.stp")
    svc.checkin(db, WS, num, "A", "test1")
    svc.delete_revision(db, WS, num, "A", "test1")
    os.remove(p)
```

- [ ] **Step 2: 运行测试确认失败**

Run: `source venv/bin/activate && pytest tests/test_file_service.py -q`
Expected: FAIL（file_service 不存在）。

- [ ] **Step 3: 实现 file_service.py**

```python
# app/services/file_service.py
"""文件服务：vault 写入/读取 + BinaryResource DB 记录。对齐 Payara saveNativeCAD/saveFile。"""
from datetime import datetime
from pathlib import Path
from sqlalchemy.orm import Session
from app.services import vault
from app.models.part import (
    BinaryResource, PartIteration, part_iteration_binres,
)


def _upsert_binaryresource(db: Session, full_name: str, size: int,
                           dtype: str = "BinaryResource") -> BinaryResource:
    br = db.query(BinaryResource).filter(
        BinaryResource.full_name == full_name).first()
    now = datetime.utcnow()
    if br is None:
        br = BinaryResource(full_name=full_name, dtype=dtype,
                            content_length=size, last_modified=now)
        db.add(br)
    else:
        br.content_length = size
        br.last_modified = now
    db.flush()
    return br


def save_nativecad(db: Session, ws: str, pn: str, ver: str, iteration: int,
                   filename: str, data: bytes) -> BinaryResource:
    """写 nativecad 到 vault + upsert BinaryResource + 设 PartIteration.native_cad_file_fullname。"""
    path = vault.part_nativecad_path(ws, pn, ver, iteration, filename)
    vault.write_file(path, data)
    full_name = f"{ws}/parts/{pn}/{ver}/{iteration}/nativecad/{filename}"
    br = _upsert_binaryresource(db, full_name, len(data))
    it = db.query(PartIteration).filter(
        PartIteration.workspace_id == ws,
        PartIteration.partmaster_partnumber == pn,
        PartIteration.partrevision_version == ver,
        PartIteration.iteration == iteration,
    ).first()
    if it is not None:
        it.native_cad_file_fullname = full_name
    db.flush()
    return br


def save_attached(db: Session, ws: str, pn: str, ver: str, iteration: int,
                  filename: str, data: bytes) -> BinaryResource:
    """写附件到 vault + upsert BinaryResource + insert part_iteration_binres 关联。"""
    path = vault.part_attached_path(ws, pn, ver, iteration, filename)
    vault.write_file(path, data)
    full_name = f"{ws}/parts/{pn}/{ver}/{iteration}/attachedfiles/{filename}"
    br = _upsert_binaryresource(db, full_name, len(data))
    exists = db.execute(
        part_iteration_binres.select().where(
            part_iteration_binres.c.workspace_id == ws,
            part_iteration_binres.c.partmaster_partnumber == pn,
            part_iteration_binres.c.partrevision_version == ver,
            part_iteration_binres.c.iteration == iteration,
            part_iteration_binres.c.attachedfile_fullname == full_name,
        )
    ).first()
    if exists is None:
        db.execute(part_iteration_binres.insert().values(
            workspace_id=ws, partmaster_partnumber=pn,
            partrevision_version=ver, iteration=iteration,
            attachedfile_fullname=full_name,
        ))
    db.flush()
    return br


def get_file_bytes(ws: str, pn: str, ver: str, iteration: int,
                   sub_type: str | None, filename: str) -> bytes:
    """从 vault 读文件。sub_type=None 读 {iter}/{filename}（几何体 GLB）。"""
    if sub_type is None:
        from app.services.vault import _vault_root
        path = (_vault_root() / ws / "parts" / pn / ver
                / str(iteration) / filename)
    elif sub_type == "nativecad":
        path = vault.part_nativecad_path(ws, pn, ver, iteration, filename)
    else:
        path = vault.part_attached_path(ws, pn, ver, iteration, filename)
    return vault.read_file(path)
```

- [ ] **Step 4: 运行测试确认通过**

Run: `source venv/bin/activate && pytest tests/test_file_service.py -q`
Expected: 2 passed。

- [ ] **Step 5: Commit**

```bash
git add docdoku-plm-server-py/app/services/file_service.py docdoku-plm-server-py/tests/test_file_service.py
git commit -m "feat(py): file_service——vault 写读 + BinaryResource 记录"
```

---

## Task 3: 文件上传/下载端点

**Files:**
- Create: `docdoku-plm-server-py/app/routers/part_files.py`
- Modify: `docdoku-plm-server-py/app/main.py`
- Test: `docdoku-plm-server-py/tests/test_part_files_api.py`

**Interfaces:**
- Consumes: `file_service`、`kafka_producer.send_conversion_order`、`ProductService`、`get_current_user`。
- Produces 端点（挂载于 API_PREFIX）：
  - `POST /files/{ws}/parts/{pn}/{ver}/{iter}/nativecad`（multipart field=upload）
  - `POST /files/{ws}/parts/{pn}/{ver}/{iter}/attachedfiles`
  - `GET /files/{ws}/parts/{pn}/{ver}/{iter}/{sub_type}/{file_name}`
  - `GET /files/{ws}/parts/{pn}/{ver}/{iter}/{file_name}`（几何体直下，sub_type=None）
- 校验：非签出用户或非最新迭代→`NotAllowedException4`；CAD 非白名单→400 "Unsupported CAD file format"。
- userToken 从请求 Authorization 头取（`get_current_user` 已验证），透传给 Kafka。

- [ ] **Step 1: 写失败测试**

```python
# tests/test_part_files_api.py
from fastapi.testclient import TestClient
from unittest.mock import patch
from app.main import app

PREFIX = "/docdoku-plm-server-rest/api"
WS = "Workspace_2"
client = TestClient(app)


def _token():
    r = client.post(f"{PREFIX}/auth/login",
                    json={"login": "test1", "password": "password"})
    return r.headers.get("jwt")


def _create(num, h):
    client.post(f"{PREFIX}/workspaces/{WS}/parts",
                json={"number": num, "name": "t"}, headers=h)


def _cleanup(num, h):
    client.put(f"{PREFIX}/workspaces/{WS}/parts/{num}-A/checkin", headers=h)
    client.request("DELETE", f"{PREFIX}/workspaces/{WS}/parts/{num}-A", headers=h)


def test_upload_nativecad_triggers_conversion():
    token = _token(); h = {"Authorization": f"Bearer {token}"}
    num = "P1BUP-CAD-1"; _create(num, h)
    with patch("app.routers.part_files.send_conversion_order") as mock_send:
        resp = client.post(
            f"{PREFIX}/files/{WS}/parts/{num}/A/1/nativecad",
            files={"upload": ("m.stp", b"STEPDATA", "application/octet-stream")},
            headers=h)
    assert resp.status_code == 201
    assert mock_send.called
    # 传给 kafka 的 token 非空
    assert mock_send.call_args[0][5]
    _cleanup(num, h)


def test_upload_bad_extension_returns_400():
    token = _token(); h = {"Authorization": f"Bearer {token}"}
    num = "P1BUP-BAD-1"; _create(num, h)
    resp = client.post(
        f"{PREFIX}/files/{WS}/parts/{num}/A/1/nativecad",
        files={"upload": ("m.txt", b"x", "text/plain")}, headers=h)
    assert resp.status_code == 400
    assert "Unsupported CAD file format" in resp.text
    _cleanup(num, h)


def test_upload_download_attached_roundtrip():
    token = _token(); h = {"Authorization": f"Bearer {token}"}
    num = "P1BUP-ATT-1"; _create(num, h)
    up = client.post(
        f"{PREFIX}/files/{WS}/parts/{num}/A/1/attachedfiles",
        files={"upload": ("doc.pdf", b"PDFBYTES", "application/pdf")}, headers=h)
    assert up.status_code == 201
    dl = client.get(f"{PREFIX}/files/{WS}/parts/{num}/A/1/attachedfiles/doc.pdf",
                    headers=h)
    assert dl.status_code == 200
    assert dl.content == b"PDFBYTES"
    _cleanup(num, h)
```

- [ ] **Step 2: 运行测试确认失败**

Run: `source venv/bin/activate && pytest tests/test_part_files_api.py -q`
Expected: FAIL（part_files 路由不存在，404）。

- [ ] **Step 3: 实现 part_files.py**

```python
# app/routers/part_files.py
"""零件文件上传/下载端点，路径 /api/files/{ws}/parts/...（对齐 Payara PartBinaryResource）。"""
from pathlib import Path
from fastapi import APIRouter, Depends, UploadFile, File, Request, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.exceptions import NotAllowedException
from app.models.auth import Account
from app.services import file_service
from app.services.product_service import ProductService
from app.services.kafka_producer import send_conversion_order

router = APIRouter()
svc = ProductService()

CAD_WHITELIST = {"stp", "step", "igs", "iges", "stl", "off", "ply", "obj", "dae", "ifc"}


def _check_writable(db: Session, ws: str, pn: str, ver: str,
                    iteration: int, user_login: str) -> None:
    """签出用户 && 最新迭代，否则 NotAllowedException4。"""
    pr = svc.get_revision(db, ws, pn, ver)
    if pr.checkout_user_login != user_login or pr.last_iteration_number != iteration:
        raise NotAllowedException("NotAllowedException4")


@router.post("/files/{ws}/parts/{pn}/{ver}/{iteration}/nativecad", status_code=201)
def upload_nativecad(
    ws: str, pn: str, ver: str, iteration: int,
    request: Request,
    upload: UploadFile = File(...),
    current_user: Account = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _check_writable(db, ws, pn, ver, iteration, current_user.login)
    ext = Path(upload.filename).suffix.lstrip(".").lower()
    if ext not in CAD_WHITELIST:
        raise HTTPException(400, "Unsupported CAD file format")
    data = upload.file.read()
    file_service.save_nativecad(db, ws, pn, ver, iteration, upload.filename, data)
    # 建 pending Conversion
    svc.create_conversion(db, ws, pn, ver, iteration)
    db.commit()
    # 透传当前请求 token 给 Kafka（回调 Bearer 认证用）
    auth = request.headers.get("authorization", "")
    token = auth[7:] if auth.startswith("Bearer ") else ""
    send_conversion_order(ws, pn, ver, iteration, upload.filename, token)
    return {"status": "uploaded"}


@router.post("/files/{ws}/parts/{pn}/{ver}/{iteration}/attachedfiles", status_code=201)
def upload_attached(
    ws: str, pn: str, ver: str, iteration: int,
    upload: UploadFile = File(...),
    current_user: Account = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _check_writable(db, ws, pn, ver, iteration, current_user.login)
    data = upload.file.read()
    file_service.save_attached(db, ws, pn, ver, iteration, upload.filename, data)
    db.commit()
    return {"status": "uploaded"}


@router.get("/files/{ws}/parts/{pn}/{ver}/{iteration}/{sub_type}/{file_name}")
def download_with_subtype(
    ws: str, pn: str, ver: str, iteration: int, sub_type: str, file_name: str,
    current_user: Account = Depends(get_current_user),
):
    try:
        data = file_service.get_file_bytes(ws, pn, ver, iteration, sub_type, file_name)
    except FileNotFoundError:
        raise HTTPException(404, "File not found")
    return Response(content=data, media_type="application/octet-stream")


@router.get("/files/{ws}/parts/{pn}/{ver}/{iteration}/{file_name}")
def download_direct(
    ws: str, pn: str, ver: str, iteration: int, file_name: str,
    current_user: Account = Depends(get_current_user),
):
    """几何体 GLB 直下（fullname 无 subType 段）。"""
    try:
        data = file_service.get_file_bytes(ws, pn, ver, iteration, None, file_name)
    except FileNotFoundError:
        raise HTTPException(404, "File not found")
    return Response(content=data, media_type="application/octet-stream")
```

- [ ] **Step 4: 在 main.py 注册路由 + 加 create_conversion 方法**

`main.py`：`from app.routers import auth, parts` 改为 `from app.routers import auth, parts, part_files`，并在 `app.include_router(parts.router, prefix=API_PREFIX)` 下方加 `app.include_router(part_files.router, prefix=API_PREFIX)`。

`product_service.py` 新增方法（在 `get_conversion` 下方）：

```python
    def create_conversion(self, db: Session, ws: str, pn: str,
                          ver: str, iteration: int) -> Conversion:
        """建 pending Conversion（已存在则复用并重置为 pending）。"""
        conv = self.get_conversion(db, ws, pn, ver, iteration)
        now = datetime.utcnow()
        if conv is None:
            conv = Conversion(
                workspace_id=ws, partmaster_partnumber=pn,
                partrevision_version=ver, iteration=iteration,
                pending=True, succeed=False, start_date=now,
            )
            db.add(conv)
        else:
            conv.pending = True
            conv.succeed = False
            conv.start_date = now
            conv.end_date = None
        db.flush()
        return conv
```

- [ ] **Step 5: 运行测试确认通过**

Run: `source venv/bin/activate && pytest tests/test_part_files_api.py -q`
Expected: 3 passed。

- [ ] **Step 6: 全量测试**

Run: `source venv/bin/activate && pytest tests/ -q`
Expected: 全部 passed。

- [ ] **Step 7: Commit**

```bash
git add docdoku-plm-server-py/app/routers/part_files.py docdoku-plm-server-py/app/main.py docdoku-plm-server-py/app/services/product_service.py docdoku-plm-server-py/tests/test_part_files_api.py
git commit -m "feat(py): 文件上传下载端点 + 触发转换（带 userToken）"
```

---

## Task 4: 转换回调服务 + 端点

**Files:**
- Create: `docdoku-plm-server-py/app/services/conversion_service.py`
- Modify: `docdoku-plm-server-py/app/schemas/part.py`（+ConversionResultDTO）
- Modify: `docdoku-plm-server-py/app/routers/parts.py`（+回调端点）
- Test: `docdoku-plm-server-py/tests/test_conversion_service.py`

**Interfaces:**
- Consumes: `vault`、`Conversion`/`BinaryResource`/`part_iteration_geometry` model、`settings.CONVERSIONS_PATH`。
- Produces:
  - `find_pending_conversion(db, ws, pn, ver) -> Conversion | None` — 查该 revision 下 pending=True 的 Conversion（定位真正发起转换的 iteration，避免 race）。
  - `end_conversion(db, conv, succeed) -> None` — 设 pending=False/succeed/end_date=now。
  - `handle_callback(db, ws, pn, ver, result: ConversionResultDTO) -> None` — 空几何"no geometry generated"→succeed=True 跳过；其他 errorOutput→succeed=False；正常→从 CONVERSIONS_PATH/{tempDir}/{glb} 读 GLB 写 vault + 建 Geometry BinaryResource(box) + 关联 + succeed=True。
- `ConversionResultDTO`：`tempDir: str|None`、`convertedFileLODs: dict|None`、`box: list[float]|None`、`errorOutput: str|None`。

- [ ] **Step 1: 写失败测试**

```python
# tests/test_conversion_service.py
import os
import uuid
from pathlib import Path
from app.services import conversion_service
from app.services.product_service import ProductService
from app.schemas.part import ConversionResultDTO
from app.models.part import BinaryResource, part_iteration_geometry
from app.core.config import settings
from app.services import vault

WS = "Workspace_2"
svc = ProductService()


def _make_part_with_conversion(db, num):
    from app.schemas.part import PartCreationDTO
    svc.create_part(db, WS, "test1", PartCreationDTO(number=num, name="t"))
    svc.create_conversion(db, WS, num, "A", 1)
    db.commit()


def test_callback_no_geometry_marks_succeed(db):
    num = "P1BCV-EMPTY-1"
    _make_part_with_conversion(db, num)
    conversion_service.handle_callback(db, WS, num, "A",
        ConversionResultDTO(errorOutput="no geometry generated"))
    db.commit()
    conv = svc.get_conversion(db, WS, num, "A", 1)
    assert conv.pending is False
    assert conv.succeed is True
    svc.checkin(db, WS, num, "A", "test1")
    svc.delete_revision(db, WS, num, "A", "test1")


def test_callback_error_marks_failed(db):
    num = "P1BCV-ERR-1"
    _make_part_with_conversion(db, num)
    conversion_service.handle_callback(db, WS, num, "A",
        ConversionResultDTO(errorOutput="some real error"))
    db.commit()
    conv = svc.get_conversion(db, WS, num, "A", 1)
    assert conv.pending is False
    assert conv.succeed is False
    svc.checkin(db, WS, num, "A", "test1")
    svc.delete_revision(db, WS, num, "A", "test1")


def test_callback_success_writes_glb(db):
    num = "P1BCV-OK-1"
    _make_part_with_conversion(db, num)
    # 准备临时 GLB
    temp_dir = str(uuid.uuid4())
    glb_name = f"{uuid.uuid4()}.glb"
    conv_dir = Path(settings.CONVERSIONS_PATH) / temp_dir
    conv_dir.mkdir(parents=True, exist_ok=True)
    (conv_dir / glb_name).write_bytes(b"GLBDATA")
    conversion_service.handle_callback(db, WS, num, "A",
        ConversionResultDTO(tempDir=temp_dir,
                            convertedFileLODs={"0": glb_name},
                            box=[-1, -1, -1, 1, 1, 1]))
    db.commit()
    conv = svc.get_conversion(db, WS, num, "A", 1)
    assert conv.succeed is True
    # vault 有 GLB + BinaryResource(Geometry)
    fn = f"{WS}/parts/{num}/A/1/{glb_name}"
    br = db.query(BinaryResource).filter(BinaryResource.full_name == fn).first()
    assert br is not None and br.dtype == "Geometry"
    assert br.x_min == -1 and br.z_max == 1
    glb_path = vault._vault_root() / WS / "parts" / num / "A" / "1" / glb_name
    assert glb_path.read_bytes() == b"GLBDATA"
    # 清理
    os.remove(glb_path)
    import shutil; shutil.rmtree(conv_dir, ignore_errors=True)
    svc.checkin(db, WS, num, "A", "test1")
    svc.delete_revision(db, WS, num, "A", "test1")
```

- [ ] **Step 2: 运行测试确认失败**

Run: `source venv/bin/activate && pytest tests/test_conversion_service.py -q`
Expected: FAIL（conversion_service/ConversionResultDTO 不存在）。

- [ ] **Step 3: 加 ConversionResultDTO 到 schemas/part.py**

在 `ConversionDTO` 定义下方新增：

```python
class ConversionResultDTO(BaseModel):
    tempDir: Optional[str] = None
    convertedFileLODs: Optional[dict] = None
    box: Optional[list[float]] = None
    errorOutput: Optional[str] = None
```

（确认文件顶部已 `from typing import Optional`；若无则补。）

- [ ] **Step 4: 实现 conversion_service.py**

```python
# app/services/conversion_service.py
"""转换回调处理，对齐 Payara handleConversionResultCallback（保留 race/空几何修复）。"""
from datetime import datetime
from pathlib import Path
from sqlalchemy.orm import Session
from app.core.config import settings
from app.services import vault
from app.models.part import (
    Conversion, BinaryResource, part_iteration_geometry,
)
from app.schemas.part import ConversionResultDTO


def find_pending_conversion(db: Session, ws: str, pn: str,
                            ver: str) -> Conversion | None:
    """查该 revision 下 pending=True 的 Conversion，定位真正发起转换的 iteration。"""
    return db.query(Conversion).filter(
        Conversion.workspace_id == ws,
        Conversion.partmaster_partnumber == pn,
        Conversion.partrevision_version == ver,
        Conversion.pending.is_(True),
    ).first()


def end_conversion(db: Session, conv: Conversion, succeed: bool) -> None:
    conv.pending = False
    conv.succeed = succeed
    conv.end_date = datetime.utcnow()
    db.flush()


def handle_callback(db: Session, ws: str, pn: str, ver: str,
                    result: ConversionResultDTO) -> None:
    conv = find_pending_conversion(db, ws, pn, ver)
    if conv is None:
        return  # 无 pending，幂等跳过
    iteration = conv.iteration
    err = (result.errorOutput or "")
    if "no geometry generated" in err.lower():
        end_conversion(db, conv, True)   # 空几何件标记成功跳过
        return
    if err:
        end_conversion(db, conv, False)
        return
    # 正常：从 CONVERSIONS_PATH/{tempDir}/{glb} 读 GLB 写 vault
    glb_name = (result.convertedFileLODs or {}).get("0")
    if not glb_name:
        end_conversion(db, conv, False)
        return
    src = Path(settings.CONVERSIONS_PATH) / result.tempDir / glb_name
    data = src.read_bytes()
    from app.services.vault import _vault_root
    dst = _vault_root() / ws / "parts" / pn / ver / str(iteration) / glb_name
    vault.write_file(dst, data)
    full_name = f"{ws}/parts/{pn}/{ver}/{iteration}/{glb_name}"
    box = result.box or [0, 0, 0, 0, 0, 0]
    br = db.query(BinaryResource).filter(
        BinaryResource.full_name == full_name).first()
    if br is None:
        br = BinaryResource(
            full_name=full_name, dtype="Geometry",
            content_length=len(data), last_modified=datetime.utcnow(),
            x_min=box[0], y_min=box[1], z_min=box[2],
            x_max=box[3], y_max=box[4], z_max=box[5],
        )
        db.add(br)
        db.flush()
    # 关联 part_iteration_geometry（若无）
    exists = db.execute(
        part_iteration_geometry.select().where(
            part_iteration_geometry.c.workspace_id == ws,
            part_iteration_geometry.c.partmaster_partnumber == pn,
            part_iteration_geometry.c.partrevision_version == ver,
            part_iteration_geometry.c.iteration == iteration,
            part_iteration_geometry.c.geometry_fullname == full_name,
        )
    ).first()
    if exists is None:
        db.execute(part_iteration_geometry.insert().values(
            workspace_id=ws, partmaster_partnumber=pn,
            partrevision_version=ver, iteration=iteration,
            geometry_fullname=full_name,
        ))
    end_conversion(db, conv, True)
```

- [ ] **Step 5: 加回调端点到 parts.py**

`parts.py` import 增加 `from app.schemas.part import ConversionResultDTO` 和 `from app.services import conversion_service`。在 `get_conversion_status` 端点下方新增（注意：`{part_key}/conversion` PUT，part_key 已含 -ver）：

```python
@router.put("/workspaces/{workspace_id}/parts/{part_key}/conversion")
def conversion_callback(
    workspace_id: str,
    part_key: str,
    body: ConversionResultDTO,
    current_user: Account = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    number, version = _split_part_key(part_key)
    conversion_service.handle_callback(db, workspace_id, number, version, body)
    db.commit()
    return {"status": "ok"}
```

- [ ] **Step 6: 运行测试确认通过**

Run: `source venv/bin/activate && pytest tests/test_conversion_service.py -q`
Expected: 3 passed。

- [ ] **Step 7: Commit**

```bash
git add docdoku-plm-server-py/app/services/conversion_service.py docdoku-plm-server-py/app/schemas/part.py docdoku-plm-server-py/app/routers/parts.py docdoku-plm-server-py/tests/test_conversion_service.py
git commit -m "feat(py): 转换回调服务+端点（race/空几何修复对齐 Payara）"
```

---

## Task 5: release / obsolete / newVersion

**Files:**
- Modify: `docdoku-plm-server-py/app/services/product_service.py`
- Modify: `docdoku-plm-server-py/app/routers/parts.py`
- Test: `docdoku-plm-server-py/tests/test_part_status.py`

**Interfaces:**
- Produces（ProductService 方法）：
  - `release(db, ws, pn, ver, user_login) -> PartRevision` — 已签出→`NotAllowedException46`；无迭代→`41`；已废弃(status=2)→`38`。成功 status=1、release_date、release_user_login/workspace。
  - `mark_obsolete(db, ws, pn, ver, user_login) -> PartRevision` — 未发布(status≠1)→`NotAllowedException36`。成功 status=2、obsolete_date、obsolete_user。
  - `create_new_version(db, ws, pn, ver, user_login) -> PartRevision` — 原版本已签出→`NotAllowedException40`；无迭代→`41`。建新 PartRevision(下一版本字母)+首迭代，自动签出。
- 端点：PUT `.../release`、`.../obsolete`、`.../newVersion`，返回 map_revision。

- [ ] **Step 1: 写失败测试**

```python
# tests/test_part_status.py
from fastapi.testclient import TestClient
from app.main import app
from app.core import i18n

PREFIX = "/docdoku-plm-server-rest/api"
WS = "Workspace_2"
client = TestClient(app)


def _token():
    r = client.post(f"{PREFIX}/auth/login",
                    json={"login": "test1", "password": "password"})
    return r.headers.get("jwt")


def _create(num, h):
    client.post(f"{PREFIX}/workspaces/{WS}/parts",
                json={"number": num, "name": "t"}, headers=h)


def _cleanup(num, h, ver="A"):
    client.request("DELETE", f"{PREFIX}/workspaces/{WS}/parts/{num}-{ver}", headers=h)


def test_release_checked_out_returns_403():
    token = _token(); h = {"Authorization": f"Bearer {token}"}
    num = "P1BST-REL-1"; _create(num, h)
    # 新建即签出，直接 release 应报已签出 46
    resp = client.put(f"{PREFIX}/workspaces/{WS}/parts/{num}-A/release", headers=h)
    assert resp.status_code == 403
    assert resp.json()["message"] == i18n.get("NotAllowedException46", "zh")
    client.put(f"{PREFIX}/workspaces/{WS}/parts/{num}-A/checkin", headers=h)
    _cleanup(num, h)


def test_release_then_obsolete_succeeds():
    token = _token(); h = {"Authorization": f"Bearer {token}"}
    num = "P1BST-OBS-1"; _create(num, h)
    client.put(f"{PREFIX}/workspaces/{WS}/parts/{num}-A/checkin", headers=h)
    rel = client.put(f"{PREFIX}/workspaces/{WS}/parts/{num}-A/release", headers=h)
    assert rel.status_code == 200
    assert rel.json()["status"] == "RELEASED"
    obs = client.put(f"{PREFIX}/workspaces/{WS}/parts/{num}-A/obsolete", headers=h)
    assert obs.status_code == 200
    assert obs.json()["status"] == "OBSOLETE"
    _cleanup(num, h)


def test_obsolete_unreleased_returns_403():
    token = _token(); h = {"Authorization": f"Bearer {token}"}
    num = "P1BST-OBSU-1"; _create(num, h)
    client.put(f"{PREFIX}/workspaces/{WS}/parts/{num}-A/checkin", headers=h)
    resp = client.put(f"{PREFIX}/workspaces/{WS}/parts/{num}-A/obsolete", headers=h)
    assert resp.status_code == 403
    assert resp.json()["message"] == i18n.get("NotAllowedException36", "zh")
    _cleanup(num, h)
```

- [ ] **Step 2: 运行测试确认失败**

Run: `source venv/bin/activate && pytest tests/test_part_status.py -q`
Expected: FAIL（端点 404）。

- [ ] **Step 3: 实现 ProductService 方法**

`product_service.py` 在 `undo_checkout` 下方新增：

```python
    def release(self, db: Session, ws: str, pn: str, ver: str,
                user_login: str) -> PartRevision:
        from app.core.exceptions import NotAllowedException
        pr = self.get_revision(db, ws, pn, ver)
        if pr.checkout_user_login:
            raise NotAllowedException("NotAllowedException46")
        if not pr.iterations:
            raise NotAllowedException("NotAllowedException41")
        if pr.status == 2:
            raise NotAllowedException("NotAllowedException38")
        pr.status = 1
        pr.release_date = datetime.utcnow()
        pr.release_user_login = user_login
        pr.release_user_workspace = ws
        db.commit()
        db.refresh(pr)
        return pr

    def mark_obsolete(self, db: Session, ws: str, pn: str, ver: str,
                      user_login: str) -> PartRevision:
        from app.core.exceptions import NotAllowedException
        pr = self.get_revision(db, ws, pn, ver)
        if pr.status != 1:
            raise NotAllowedException("NotAllowedException36")
        pr.status = 2
        pr.obsolete_date = datetime.utcnow()
        pr.obsolete_user_login = user_login
        pr.obsolete_user_workspace = ws
        db.commit()
        db.refresh(pr)
        return pr

    def create_new_version(self, db: Session, ws: str, pn: str, ver: str,
                           user_login: str) -> PartRevision:
        from app.core.exceptions import NotAllowedException
        pr = self.get_revision(db, ws, pn, ver)
        if pr.checkout_user_login:
            raise NotAllowedException("NotAllowedException40")
        if not pr.iterations:
            raise NotAllowedException("NotAllowedException41")
        now = datetime.utcnow()
        new_ver = self._next_version(ver)
        new_pr = PartRevision(
            workspace_id=ws, partmaster_partnumber=pn, version=new_ver,
            description=pr.description, status=0, creation_date=now,
            author_workspace_id=ws, author_login=user_login,
            checkout_user_workspace_id=ws, checkout_user_login=user_login,
            check_out_date=now,
        )
        db.add(new_pr)
        db.flush()
        db.add(PartIteration(
            workspace_id=ws, partmaster_partnumber=pn,
            partrevision_version=new_ver, iteration=1,
            creation_date=now, author_workspace_id=ws, author_login=user_login,
        ))
        db.commit()
        db.refresh(new_pr)
        return new_pr
```

- [ ] **Step 4: 加端点到 parts.py**

在回调端点下方新增：

```python
@router.put("/workspaces/{workspace_id}/parts/{part_key}/release",
            response_model=PartRevisionDTO)
def release_part(workspace_id: str, part_key: str,
                 current_user: Account = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    number, version = _split_part_key(part_key)
    pr = svc.release(db, workspace_id, number, version, current_user.login)
    return map_revision(pr, db)


@router.put("/workspaces/{workspace_id}/parts/{part_key}/obsolete",
            response_model=PartRevisionDTO)
def obsolete_part(workspace_id: str, part_key: str,
                  current_user: Account = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    number, version = _split_part_key(part_key)
    pr = svc.mark_obsolete(db, workspace_id, number, version, current_user.login)
    return map_revision(pr, db)


@router.put("/workspaces/{workspace_id}/parts/{part_key}/newVersion",
            response_model=PartRevisionDTO)
def new_version_part(workspace_id: str, part_key: str,
                     current_user: Account = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    number, version = _split_part_key(part_key)
    pr = svc.create_new_version(db, workspace_id, number, version, current_user.login)
    return map_revision(pr, db)
```

- [ ] **Step 5: 运行测试确认通过**

Run: `source venv/bin/activate && pytest tests/test_part_status.py -q`
Expected: 3 passed。

- [ ] **Step 6: Commit**

```bash
git add docdoku-plm-server-py/app/services/product_service.py docdoku-plm-server-py/app/routers/parts.py docdoku-plm-server-py/tests/test_part_status.py
git commit -m "feat(py): release/obsolete/newVersion 端点对齐 Payara i18n"
```

---

## Task 6: 标签管理

**Files:**
- Modify: `docdoku-plm-server-py/app/services/product_service.py`
- Modify: `docdoku-plm-server-py/app/routers/parts.py`
- Test: `docdoku-plm-server-py/tests/test_part_tags.py`

**Interfaces:**
- Produces（ProductService）：
  - `set_tags(db, ws, pn, ver, labels: list[str]) -> PartRevision` — 整体替换标签集合。
  - `add_tag(db, ws, pn, ver, label: str) -> PartRevision` — 追加。
  - `remove_tag(db, ws, pn, ver, label: str) -> PartRevision` — 移除。
  - 内部 `_ensure_tag(db, ws, label)` upsert tag 表。操作 `part_revision_tags` 关联表。
- 端点：PUT/POST `.../tags`（body `{"tags": ["a","b"]}` 或 `{"tag":"a"}`）、DELETE `.../tags/{tag_label}`。

- [ ] **Step 1: 写失败测试**

```python
# tests/test_part_tags.py
from fastapi.testclient import TestClient
from app.main import app

PREFIX = "/docdoku-plm-server-rest/api"
WS = "Workspace_2"
client = TestClient(app)


def _token():
    r = client.post(f"{PREFIX}/auth/login",
                    json={"login": "test1", "password": "password"})
    return r.headers.get("jwt")


def _create(num, h):
    client.post(f"{PREFIX}/workspaces/{WS}/parts",
                json={"number": num, "name": "t"}, headers=h)


def _cleanup(num, h):
    client.put(f"{PREFIX}/workspaces/{WS}/parts/{num}-A/checkin", headers=h)
    client.request("DELETE", f"{PREFIX}/workspaces/{WS}/parts/{num}-A", headers=h)


def test_set_and_get_tags():
    token = _token(); h = {"Authorization": f"Bearer {token}"}
    num = "P1BTAG-1"; _create(num, h)
    resp = client.put(f"{PREFIX}/workspaces/{WS}/parts/{num}-A/tags",
                      json={"tags": ["alpha", "beta"]}, headers=h)
    assert resp.status_code == 200
    assert set(resp.json()["tags"]) == {"alpha", "beta"}
    _cleanup(num, h)


def test_remove_tag():
    token = _token(); h = {"Authorization": f"Bearer {token}"}
    num = "P1BTAG-2"; _create(num, h)
    client.put(f"{PREFIX}/workspaces/{WS}/parts/{num}-A/tags",
               json={"tags": ["x", "y"]}, headers=h)
    resp = client.request("DELETE",
                          f"{PREFIX}/workspaces/{WS}/parts/{num}-A/tags/x",
                          headers=h)
    assert resp.status_code == 200
    assert resp.json()["tags"] == ["y"]
    _cleanup(num, h)
```

- [ ] **Step 2: 运行测试确认失败**

Run: `source venv/bin/activate && pytest tests/test_part_tags.py -q`
Expected: FAIL（端点 404）。

- [ ] **Step 3: 实现 ProductService 方法**

`product_service.py` import 增加 `Tag, part_revision_tags`（从 app.models.part）。新增方法：

```python
    def _ensure_tag(self, db: Session, ws: str, label: str) -> None:
        from app.models.part import Tag
        t = db.query(Tag).filter(Tag.workspace_id == ws,
                                 Tag.label == label).first()
        if t is None:
            db.add(Tag(workspace_id=ws, label=label))
            db.flush()

    def set_tags(self, db: Session, ws: str, pn: str, ver: str,
                 labels: list) -> PartRevision:
        from app.models.part import part_revision_tags
        pr = self.get_revision(db, ws, pn, ver)
        db.execute(part_revision_tags.delete().where(
            part_revision_tags.c.partmaster_workspace_id == ws,
            part_revision_tags.c.partmaster_partnumber == pn,
            part_revision_tags.c.partrevision_version == ver,
        ))
        for label in labels:
            self._ensure_tag(db, ws, label)
            db.execute(part_revision_tags.insert().values(
                partmaster_workspace_id=ws, partmaster_partnumber=pn,
                partrevision_version=ver, tag_workspace_id=ws, tag_label=label,
            ))
        db.commit()
        db.refresh(pr)
        return pr

    def add_tag(self, db: Session, ws: str, pn: str, ver: str,
                label: str) -> PartRevision:
        from app.models.part import part_revision_tags
        pr = self.get_revision(db, ws, pn, ver)
        self._ensure_tag(db, ws, label)
        exists = db.execute(part_revision_tags.select().where(
            part_revision_tags.c.partmaster_workspace_id == ws,
            part_revision_tags.c.partmaster_partnumber == pn,
            part_revision_tags.c.partrevision_version == ver,
            part_revision_tags.c.tag_label == label,
        )).first()
        if exists is None:
            db.execute(part_revision_tags.insert().values(
                partmaster_workspace_id=ws, partmaster_partnumber=pn,
                partrevision_version=ver, tag_workspace_id=ws, tag_label=label,
            ))
        db.commit()
        db.refresh(pr)
        return pr

    def remove_tag(self, db: Session, ws: str, pn: str, ver: str,
                   label: str) -> PartRevision:
        from app.models.part import part_revision_tags
        pr = self.get_revision(db, ws, pn, ver)
        db.execute(part_revision_tags.delete().where(
            part_revision_tags.c.partmaster_workspace_id == ws,
            part_revision_tags.c.partmaster_partnumber == pn,
            part_revision_tags.c.partrevision_version == ver,
            part_revision_tags.c.tag_label == label,
        ))
        db.commit()
        db.refresh(pr)
        return pr
```

- [ ] **Step 4: 加端点到 parts.py**

新增（`Request` 已可用；用 dict body）：

```python
from fastapi import Body

@router.put("/workspaces/{workspace_id}/parts/{part_key}/tags",
            response_model=PartRevisionDTO)
def set_tags(workspace_id: str, part_key: str,
             body: dict = Body(...),
             current_user: Account = Depends(get_current_user),
             db: Session = Depends(get_db)):
    number, version = _split_part_key(part_key)
    pr = svc.set_tags(db, workspace_id, number, version, body.get("tags", []))
    return map_revision(pr, db)


@router.post("/workspaces/{workspace_id}/parts/{part_key}/tags",
             response_model=PartRevisionDTO)
def add_tag(workspace_id: str, part_key: str,
            body: dict = Body(...),
            current_user: Account = Depends(get_current_user),
            db: Session = Depends(get_db)):
    number, version = _split_part_key(part_key)
    pr = svc.add_tag(db, workspace_id, number, version, body.get("tag", ""))
    return map_revision(pr, db)


@router.delete("/workspaces/{workspace_id}/parts/{part_key}/tags/{tag_label}",
               response_model=PartRevisionDTO)
def remove_tag(workspace_id: str, part_key: str, tag_label: str,
               current_user: Account = Depends(get_current_user),
               db: Session = Depends(get_db)):
    number, version = _split_part_key(part_key)
    pr = svc.remove_tag(db, workspace_id, number, version, tag_label)
    return map_revision(pr, db)
```

- [ ] **Step 5: 运行测试确认通过**

Run: `source venv/bin/activate && pytest tests/test_part_tags.py -q`
Expected: 2 passed。

- [ ] **Step 6: Commit**

```bash
git add docdoku-plm-server-py/app/services/product_service.py docdoku-plm-server-py/app/routers/parts.py docdoku-plm-server-py/tests/test_part_tags.py
git commit -m "feat(py): 标签管理端点（set/add/remove）"
```

---

## Task 7: 搜索（DB MVP）

**Files:**
- Modify: `docdoku-plm-server-py/app/services/product_service.py`
- Modify: `docdoku-plm-server-py/app/routers/parts.py`
- Test: `docdoku-plm-server-py/tests/test_part_search.py`

**Interfaces:**
- Produces: `search_parts(db, ws, name=None, number=None, type_=None) -> list[PartRevision]` — 对 partmaster ilike 模糊匹配，返回其所有 revision。
- 端点：GET `/workspaces/{ws}/parts/search`，query 参数 name/number/type。
- **路由顺序**：`search` 是固定路径，必须在 `{part_key}` 之前注册（放到 `count`/`numbers` 那组固定路径附近）。

- [ ] **Step 1: 写失败测试**

```python
# tests/test_part_search.py
from fastapi.testclient import TestClient
from app.main import app

PREFIX = "/docdoku-plm-server-rest/api"
WS = "Workspace_2"
client = TestClient(app)


def _token():
    r = client.post(f"{PREFIX}/auth/login",
                    json={"login": "test1", "password": "password"})
    return r.headers.get("jwt")


def test_search_by_name_finds_seeded_part():
    token = _token(); h = {"Authorization": f"Bearer {token}"}
    # Workspace_2 有 "Differential Axle 2010" 等种子零件
    resp = client.get(f"{PREFIX}/workspaces/{WS}/parts/search?name=Differential",
                      headers=h)
    assert resp.status_code == 200
    numbers = [r["number"] for r in resp.json()]
    assert any("Differential" in n for n in numbers)


def test_search_no_match_returns_empty():
    token = _token(); h = {"Authorization": f"Bearer {token}"}
    resp = client.get(f"{PREFIX}/workspaces/{WS}/parts/search?name=ZZZNOMATCH999",
                      headers=h)
    assert resp.status_code == 200
    assert resp.json() == []
```

- [ ] **Step 2: 运行测试确认失败**

Run: `source venv/bin/activate && pytest tests/test_part_search.py -q`
Expected: FAIL（search 端点未实现，可能命中 {part_key} 报错）。

- [ ] **Step 3: 实现 search_parts**

`product_service.py` 新增：

```python
    def search_parts(self, db: Session, ws: str, name=None,
                     number=None, type_=None) -> list:
        q = db.query(PartMaster).filter(PartMaster.workspace_id == ws)
        if name:
            q = q.filter(PartMaster.name.ilike(f"%{name}%"))
        if number:
            q = q.filter(PartMaster.number.ilike(f"%{number}%"))
        if type_:
            q = q.filter(PartMaster.type.ilike(f"%{type_}%"))
        masters = q.limit(100).all()
        result = []
        for m in masters:
            result.extend(m.revisions)
        return result
```

- [ ] **Step 4: 加端点到 parts.py（固定路径，放在 count 端点附近，务必在 `{part_key}` 之前）**

```python
@router.get("/workspaces/{workspace_id}/parts/search",
            response_model=list[PartRevisionDTO])
def search_parts(
    workspace_id: str,
    name: str = Query(None),
    number: str = Query(None),
    type: str = Query(None),
    current_user: Account = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    revisions = svc.search_parts(db, workspace_id, name=name,
                                 number=number, type_=type)
    return [map_revision(pr, db) for pr in revisions]
```

- [ ] **Step 5: 运行测试确认通过**

Run: `source venv/bin/activate && pytest tests/test_part_search.py -q`
Expected: 2 passed。

- [ ] **Step 6: 全量测试**

Run: `source venv/bin/activate && pytest tests/ -q`
Expected: 全部 passed。

- [ ] **Step 7: Commit**

```bash
git add docdoku-plm-server-py/app/services/product_service.py docdoku-plm-server-py/app/routers/parts.py docdoku-plm-server-py/tests/test_part_search.py
git commit -m "feat(py): 零件搜索端点（DB LIKE MVP）"
```

---

## Task 8: 部署——Nginx files 路由 + 切换 ENDPOINT（严格按时序）

**Files:**
- Modify: `docdoku-plm-docker/front/nginx.conf`
- Modify: `docdoku-plm-docker/env/conversion.env`

**Interfaces:** 无代码接口，纯部署。**严格按序**：先部署 back-py（含前 7 任务）→ 加 Nginx files 路由 → 改 ENDPOINT → 重启 conversion。

- [ ] **Step 1: 重建并部署 back-py（含前 7 任务全部代码）**

```bash
cd docdoku-plm-docker && docker compose up -d --build back-py && sleep 3
curl -s http://localhost:8009/docdoku-plm-server-rest/api/health
```
Expected: `{"status":"ok","backend":"fastapi"}`

- [ ] **Step 2: 加 Nginx files 路由块**

`docdoku-plm-docker/front/nginx.conf` 中，在 parts 正则 location（`~ ^/docdoku-plm-server-rest/api/workspaces/[^/]+/parts`）下方、兜底 `location /docdoku-plm-server-rest/` 之前，新增：

```nginx
    location ~ ^/docdoku-plm-server-rest/api/files/[^/]+/parts {
        set $backpy "back-py:8000";
        proxy_pass         http://$backpy;
        proxy_http_version 1.1;
        proxy_set_header   Host              $host;
        proxy_set_header   X-Real-IP         $remote_addr;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
        client_max_body_size 500m;
    }
```

- [ ] **Step 3: 重启 front 使 Nginx 生效**

```bash
cd docdoku-plm-docker && docker compose up -d --force-recreate --no-deps front && sleep 3
```

- [ ] **Step 4: 验证文件路由通到 FastAPI（未认证应 401/403，非 Payara 的 500）**

Run: `curl -s -o /dev/null -w "%{http_code}" "http://localhost:8000/docdoku-plm-server-rest/api/files/Workspace_2/parts/x/A/1/nativecad/y.stp"`
Expected: 401 或 403（FastAPI 认证拒绝，证明路由到了 back-py）。

- [ ] **Step 5: 改 conversion.env ENDPOINT**

`docdoku-plm-docker/env/conversion.env` 内容改为：

```
# Callback API — 指向 FastAPI back-py（P1b 迁移）
ENDPOINT=http://back-py:8000/docdoku-plm-server-rest/api
```

- [ ] **Step 6: 重启 conversion 服务**

```bash
cd docdoku-plm-docker && docker compose up -d --force-recreate --no-deps conversion && sleep 3
docker logs docdoku-plm-docker-conversion-1 --tail=5
```
Expected: 服务正常启动，无报错。

- [ ] **Step 7: 端到端验证（前端实测清单交用户）**

交给用户按以下清单在前端实测：
1. 上传一个 .stp 文件到某零件 → 观察转换完成 → 3D 预览出现
2. 上传附件（PDF）→ 下载附件 → 内容正确
3. 签入后 release → 状态变 RELEASED → obsolete → OBSOLETE
4. newVersion → 出现新版本
5. 打标签/删标签
6. 搜索零件名

- [ ] **Step 8: Commit**

```bash
git add docdoku-plm-docker/front/nginx.conf docdoku-plm-docker/env/conversion.env
git commit -m "chore(docker): P1b 切换——Nginx files 路由 + conversion 回调指向 back-py"
```

---

## Task 9: 对齐审计 + Payara 对拍 + 文档

**Files:**
- Modify: `docs/CHANGELOG.md`、`docs/REMINDERS.md`、`docs/superpowers/fastapi-migration-roadmap.md`

- [ ] **Step 1: Payara 对拍关键操作**

Run: `source venv/bin/activate && python scripts/compare_with_payara.py /workspaces/Workspace_2/parts/Differential Axle 2010-A`
Expected: 无新增 diff（release/tags 等字段与 Payara 一致；datetime 精度差异可接受）。

- [ ] **Step 2: 全量测试最终确认**

Run: `source venv/bin/activate && pytest tests/ -q`
Expected: 全部 passed。

- [ ] **Step 3: 更新 CHANGELOG**

在顶部加当天条目，记录：Kafka 消息重构、文件上传下载、转换回调迁移、release/obsolete/newVersion、标签、搜索、Nginx files 路由、ENDPOINT 切换。

- [ ] **Step 4: 更新 REMINDERS + 路线图**

REMINDERS：P1b 标记完成移入"已解决"；记录债务（JWT 过期风险、装配同步未做、搜索 DB MVP）。
路线图 `fastapi-migration-roadmap.md`：P1b 状态改 ✅；Nginx 路由表加 files 行；对齐债务表更新。

- [ ] **Step 5: Commit**

```bash
git add docs/CHANGELOG.md docs/REMINDERS.md docs/superpowers/fastapi-migration-roadmap.md
git commit -m "docs: P1b 完成——文件/转换/状态/标签/搜索迁移记录"
```

---

## Self-Review 结果

- **Spec 覆盖**：文件上传下载（Task 2/3）✅；转换回调+userToken（Task 1/4）✅；release/obsolete/newVersion（Task 5）✅；标签（Task 6）✅；搜索 DB MVP（Task 7）✅；Nginx+ENDPOINT 切换时序（Task 8）✅；对齐审计+对拍+文档（Task 9）✅。7 条修正全部落实：topic CONVERT（Task 1）、嵌套消息（Task 1）、GLB 路径无 geometry/ 子目录（Task 4）、双下载路由（Task 3）、dtype 值（Task 2/4）、CONVERSIONS_PATH（Task 1/4）、装配同步不做（记入 Task 9 债务）。
- **Placeholder 扫描**：无 TBD/TODO 占位（delete_revision 既有 TODO 是 P1a 遗留债务，不属本计划新增）。每个代码步骤含完整代码。
- **类型一致**：`send_conversion_order(..., user_token)`、`create_conversion`、`find_pending_conversion`、`end_conversion`、`handle_callback`、`ConversionResultDTO`、`save_nativecad`/`save_attached`/`get_file_bytes`、`release`/`mark_obsolete`/`create_new_version`、`set_tags`/`add_tag`/`remove_tag`、`search_parts` 全计划一致。

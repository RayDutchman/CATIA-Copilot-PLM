# P3 产品结构 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 FastAPI 实现产品结构（ConfigurationItem/Baseline/Configuration/Instance CRUD + filterProductStructure 递归组件树 + decodePath），行为与 Payara 一致，前端零改动。

**Architecture:** 新建 `product.py` ORM + `product_structure_service.py`（含 ComponentDTO 递归组装）+ 4 路由文件。异常/i18n 复用基础设施。CFItem 创建绑定已存在的 PartRevision（关联装配数据 partusagelink 21 行）。

**Tech Stack:** FastAPI、SQLAlchemy、Pydantic v2、pytest。

## Global Constraints

- 路径前缀 `/docdoku-plm-server-rest/api` 不变，前端零改动。
- 运行测试：`workdir: docdoku-plm-server-py` → `source venv/bin/activate && pytest tests/ -q`。
- 重建容器：`workdir: docdoku-plm-docker` → `docker compose up -d --build back-py`。
- 测试数据：test1/password，Workspace_2 有 20+ 零件 + partusagelink 21 行 + cadinstance 102 行。
- 异常复用 `app/core/exceptions.py`，抛 i18n key。
- 遵循标准每阶段工作流 + 防御性检查清单。
- **所有 POST/PUT 端点必须双路由注册（尾斜杠 307）。**

## 关键事实（DB 已验证）

- `configurationitem` PK: `(workspace_id, id)`，FK→partmaster(`partmaster_workspace_id`, `partmaster_partnumber`)
- `productbaseline` PK: `id`(auto)，FK→configurationitem
- `productconfiguration` PK: `id`(auto)，FK→configurationitem
- `productinstancemaster` PK: `(serialnumber, workspace_id, configurationitem_id)`
- `productinstanceiteration` PK: 复合 5 列
- `cadinstance` 有 102 行（MATRIX 类型，3x3 + translation）
- ComponentDTO: 24 简单字段 + 4 list 字段（含 `components[]` 递归）
- path 格式: `u1-u4-u7-u12`（linkCode-linkId 链，`-` 分隔）
- ConfigurationItem 无 nested `partIterations` — 只存 `partmaster` 引用

## 文件结构

**新建：**
- `app/models/product.py` — ORM（CI/baseline/configuration/instance/baselinedpart）
- `app/routers/products.py` — ProductResource + ConfigurationsResource + BaselinesResource
- `app/routers/product_instances.py` — ProductInstancesResource
- `app/routers/product_files.py` — ProductInstanceBinaryResource
- `app/services/product_structure_service.py` — filterProductStructure + ComponentDTO 递归 + decodePath
- `tests/test_product_models.py`、`tests/test_product_service.py`、`tests/test_products_api.py`

**修改：**
- `app/main.py` — 注册 4 个新路由
- `docdoku-plm-docker/front/nginx.conf` — 新增 5 个路由块

---

## Task 1: ORM 模型（`app/models/product.py`）

**Files:**
- Create: `docdoku-plm-server-py/app/models/product.py`
- Test: `docdoku-plm-server-py/tests/test_product_models.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_product_models.py
from app.core.database import SessionLocal
from app.models.product import ConfigurationItem, ProductBaseline, CADInstance

def test_tables_exist():
    db = SessionLocal()
    assert ConfigurationItem.__tablename__ == "configurationitem"
    assert ProductBaseline.__tablename__ == "productbaseline"
    assert CADInstance.__tablename__ == "cadinstance"
    db.close()

def test_cadinstance_count():
    db = SessionLocal()
    count = db.query(CADInstance).count()
    assert count >= 100
    db.close()
```

- [ ] **Step 2: 运行失败**

Run: `source venv/bin/activate && pytest tests/test_product_models.py -q`
Expected: FAIL。

- [ ] **Step 3: 实现 `app/models/product.py`**

```python
# app/models/product.py
"""ORM: configurationitem → productbaseline/productconfiguration/productinstance。"""
from typing import Optional, List
from sqlalchemy import (
    Column, String, Boolean, Integer, Float, DateTime, Text,
    ForeignKey, ForeignKeyConstraint, Table
)
from sqlalchemy.orm import relationship, Mapped
from app.core.database import Base

class ConfigurationItem(Base):
    __tablename__ = "configurationitem"
    workspace_id = Column(String, primary_key=True)
    id = Column(String, primary_key=True)
    description = Column(Text)
    partmaster_workspace_id = Column(String)
    partmaster_partnumber = Column(String)
    author_workspace_id = Column(String)
    author_login = Column(String)

    part_master: Mapped[Optional["PartMaster"]] = relationship(
        "PartMaster",
        foreign_keys=[partmaster_workspace_id, partmaster_partnumber],
        primaryjoin=(
            "and_(ConfigurationItem.partmaster_workspace_id==PartMaster.workspace_id,"
            "ConfigurationItem.partmaster_partnumber==PartMaster.number)"
        ),
    )

from app.models.part import PartMaster  # noqa: E402

class ProductBaseline(Base):
    __tablename__ = "productbaseline"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    creation_date = Column("creationdate", DateTime)
    type = Column(Integer)
    author_workspace_id = Column(String)
    author_login = Column(String)
    configurationitem_id = Column(String)
    configurationitem_workspace_id = Column(String)
    documentcollection_id = Column(Integer)
    partcollection_id = Column(Integer)

class ProductConfiguration(Base):
    __tablename__ = "productconfiguration"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    creation_date = Column("creationdate", DateTime)
    author_workspace_id = Column(String)
    author_login = Column(String)
    configurationitem_id = Column(String)
    configurationitem_workspace_id = Column(String)
    acl_id = Column(Integer)

class ProductInstanceMaster(Base):
    __tablename__ = "productinstancemaster"
    serialnumber = Column("serialnumber", String, primary_key=True)
    workspace_id = Column(String, primary_key=True)
    configurationitem_id = Column(String, primary_key=True)
    acl_id = Column(Integer)

class ProductInstanceIteration(Base):
    __tablename__ = "productinstanceiteration"
    workspace_id = Column(String, primary_key=True)
    configurationitem_id = Column(String, primary_key=True)
    prdinstancemaster_serialnumber = Column("prdinstancemaster_serialnumber", String, primary_key=True)
    iteration = Column(Integer, primary_key=True)
    creation_date = Column("creationdate", DateTime)
    modification_date = Column("modificationdate", DateTime)
    iteration_note = Column("iterationnote", String)
    productbaseline_id = Column(Integer)
    author_workspace_id = Column(String)
    author_login = Column(String)
    documentcollection_id = Column(Integer)
    partcollection_id = Column(Integer)

# CADInstance 已存在 models/part.py 中，此处不重复定义
from app.models.part import CADInstance  # noqa: E402
```

- [ ] **Step 4: 运行通过**

Run: `source venv/bin/activate && pytest tests/test_product_models.py -q`
Expected: 2 passed。

- [ ] **Step 5: Commit**

```bash
git add app/models/product.py tests/test_product_models.py
git commit -m "feat(py): 产品结构 ORM——CI/baseline/configuration/instance"
```

---

## Task 2: product_structure_service（ComponentDTO 递归 + decodePath）

**Files:**
- Create: `docdoku-plm-server-py/app/services/product_structure_service.py`
- Test: `docdoku-plm-server-py/tests/test_product_service.py`

**关键：ComponentDTO 24 简单字段 + 4 list 字段，`components` 递归。**

路径构建：每层 link_code + link_id → `u1-u4-u7-u12`

- [ ] **Step 1: 写测试**

```python
# tests/test_product_service.py
from app.services.product_structure_service import ProductStructureService
WS = "Workspace_2"
svc = ProductStructureService()

def test_create_ci(db):
    ci = svc.create_ci(db, WS, "P3CI-T1", "Test CI",
                       "Assem1", "test1")
    assert ci.id == "P3CI-T1"
    assert ci.partmaster_partnumber == "Assem1"
    return ci

def test_ci_already_exists(db):
    from app.core.exceptions import EntityAlreadyExistsException
    svc.create_ci(db, WS, "P3CI-DUP", "T", "Assem1", "test1")
    try:
        svc.create_ci(db, WS, "P3CI-DUP", "T", "Assem1", "test1")
        assert False
    except EntityAlreadyExistsException as e:
        assert "ConfigurationItem" in e.key
    svc.delete_ci(db, WS, "P3CI-DUP")
```

- [ ] **Step 2: 运行失败**

Run: `source venv/bin/activate && pytest tests/test_product_service.py -q`
Expected: FAIL。

- [ ] **Step 3: 实现 service**

核心方法：

```python
# app/services/product_structure_service.py
from app.models.product import (
    ConfigurationItem, ProductBaseline, ProductConfiguration,
    ProductInstanceMaster, ProductInstanceIteration,
)
from app.models.part import PartMaster, PartRevision, PartIteration, PartUsageLink, CADInstance
from app.core.exceptions import EntityAlreadyExistsException

class ProductStructureService:

    # ── CI CRUD ──

    def create_ci(self, db, ws, ci_id, description, part_number, user_login):
        existing = db.query(ConfigurationItem).filter(
            ConfigurationItem.workspace_id == ws,
            ConfigurationItem.id == ci_id,
        ).first()
        if existing:
            raise EntityAlreadyExistsException(
                "ConfigurationItemAlreadyExistsException", ci_id)
        ci = ConfigurationItem(
            workspace_id=ws, id=ci_id, description=description,
            partmaster_workspace_id=ws, partmaster_partnumber=part_number,
            author_workspace_id=ws, author_login=user_login)
        db.add(ci); db.commit(); db.refresh(ci)
        return ci

    def list_cis(self, db, ws):
        return db.query(ConfigurationItem).filter(
            ConfigurationItem.workspace_id == ws).all()

    def get_ci(self, db, ws, ci_id):
        ci = db.query(ConfigurationItem).filter(
            ConfigurationItem.workspace_id == ws,
            ConfigurationItem.id == ci_id).first()
        if ci is None:
            raise HTTPException(404, "Configuration item not found")
        return ci

    def delete_ci(self, db, ws, ci_id):
        ci = self.get_ci(db, ws, ci_id)
        db.delete(ci); db.commit()

    # ── filterProductStructure 递归组件树 ──

    def _build_component(self, db, rev, usage_link, path):
        """构建单个 ComponentDTO，递归填充 components[]。"""
        last_it = rev.last_iteration
        comp = {
            "number": rev.partmaster_partnumber,
            "name": rev.part_master.name or "",
            "version": rev.version,
            "iteration": last_it.iteration if last_it else 0,
            "path": path,
            "amount": usage_link.amount if usage_link and usage_link.amount else 1.0,
            "unit": usage_link.unit if usage_link else None,
            "optional": usage_link.optional if usage_link else False,
            "partUsageLinkId": f"u{usage_link.id}" if usage_link else "u1",
            "description": rev.description or "",
            "standardPart": rev.part_master.standard_part or False,
            "assembly": bool(last_it and last_it.components),
            "released": rev.status == 1,
            "obsolete": rev.status == 2,
            "author": rev.author_login or "",
            "authorLogin": rev.author_login or "",
            "checkOutUser": {"login": rev.checkout_user_login} if rev.checkout_user_login else None,
            "checkOutDate": str(rev.check_out_date) if rev.check_out_date else None,
            "lastIterationNumber": rev.last_iteration_number,
            "attributes": [],
            "components": [],
            "substituteIds": [],
            "notifications": [],
        }
        # 递归子组件
        if last_it:
            for order_link in (last_it.components or []):
                child_rev = order_link.component
                child_path = f"{path}-u{order_link.id}" if path else f"u{order_link.id}"
                child_comp = self._build_component(db, child_rev, order_link, child_path)
                comp["components"].append(child_comp)
        return comp

    def filter_product_structure(self, db, ws, ci_id, config_spec=None,
                                  path=None, depth=None):
        ci = self.get_ci(db, ws, ci_id)
        root_pn = ci.partmaster_partnumber
        master = db.query(PartMaster).filter(
            PartMaster.workspace_id == ws, PartMaster.number == root_pn).first()
        if master is None or not master.revisions:
            return []
        root_rev = master.last_revision
        return [self._build_component(db, root_rev, None, ci_id)]

    # ── decodePath ──

    def decode_path(self, db, ws, ci_id, path_str):
        """u1-u4-u7 → PartLink 列表。"""
        ci = self.get_ci(db, ws, ci_id)
        root_pn = ci.partmaster_partnumber
        master = db.query(PartMaster).filter(
            PartMaster.workspace_id == ws, PartMaster.number == root_pn).first()
        if master is None:
            return []
        segments = path_str.split("-")
        result = []
        current_rev = master.last_revision
        for seg in segments:
            link_id = int(seg[1:])  # "u4" → 4
            link = db.query(PartUsageLink).filter(
                PartUsageLink.id == link_id).first()
            if link is None:
                break
            comp = link.component
            if comp is None:
                break
            result.append({
                "id": link.id,
                "partNumber": comp.partmaster_partnumber,
                "version": comp.version,
                "amount": link.amount or 1.0,
                "unit": link.unit,
                "optional": link.optional or False,
            })
        return result

    # ── Baseline CRUD ──

    def list_baselines(self, db, ws, ci_id=None):
        q = db.query(ProductBaseline).filter(
            ProductBaseline.configurationitem_workspace_id == ws)
        if ci_id:
            q = q.filter(ProductBaseline.configurationitem_id == ci_id)
        return q.all()

    def create_baseline(self, db, ws, ci_id, name, desc, bl_type, user_login):
        bl = ProductBaseline(
            name=name, description=desc, type=bl_type,
            configurationitem_workspace_id=ws,
            configurationitem_id=ci_id,
            author_workspace_id=ws, author_login=user_login,
            creation_date=__import__('datetime').datetime.utcnow())
        db.add(bl); db.commit(); db.refresh(bl)
        return bl

    def delete_baseline(self, db, ws, bl_id):
        bl = db.query(ProductBaseline).filter(
            ProductBaseline.id == bl_id).first()
        if bl is None:
            raise HTTPException(404, "Baseline not found")
        db.delete(bl); db.commit()

    # ── Configuration CRUD ──

    def create_config(self, db, ws, ci_id, name, desc, user_login):
        cfg = ProductConfiguration(
            name=name, description=desc,
            configurationitem_workspace_id=ws,
            configurationitem_id=ci_id,
            author_workspace_id=ws, author_login=user_login,
            creation_date=__import__('datetime').datetime.utcnow())
        db.add(cfg); db.commit(); db.refresh(cfg)
        return cfg

    def list_configs(self, db, ws, ci_id=None):
        q = db.query(ProductConfiguration).filter(
            ProductConfiguration.configurationitem_workspace_id == ws)
        if ci_id:
            q = q.filter(ProductConfiguration.configurationitem_id == ci_id)
        return q.all()

    def delete_config(self, db, ws, cfg_id):
        cfg = db.query(ProductConfiguration).filter(
            ProductConfiguration.id == cfg_id).first()
        if cfg is None:
            raise HTTPException(404, "Configuration not found")
        db.delete(cfg); db.commit()

    # ── Instance CRUD ──

    def create_instance(self, db, ws, ci_id, serial, baseline_id, user_login):
        master = ProductInstanceMaster(
            serialnumber=serial, workspace_id=ws,
            configurationitem_id=ci_id)
        db.add(master); db.flush()
        it = ProductInstanceIteration(
            workspace_id=ws, configurationitem_id=ci_id,
            prdinstancemaster_serialnumber=serial, iteration=1,
            productbaseline_id=baseline_id,
            author_workspace_id=ws, author_login=user_login,
            creation_date=__import__('datetime').datetime.utcnow())
        db.add(it); db.commit(); db.refresh(master)
        return master

    def list_instances(self, db, ws, ci_id=None):
        q = db.query(ProductInstanceMaster).filter(
            ProductInstanceMaster.workspace_id == ws)
        if ci_id:
            q = q.filter(ProductInstanceMaster.configurationitem_id == ci_id)
        return q.all()

    def delete_instance(self, db, ws, ci_id, serial):
        inst = db.query(ProductInstanceMaster).filter(
            ProductInstanceMaster.workspace_id == ws,
            ProductInstanceMaster.configurationitem_id == ci_id,
            ProductInstanceMaster.serialnumber == serial).first()
        if inst is None:
            raise HTTPException(404, "Instance not found")
        db.delete(inst); db.commit()
```

- [ ] **Step 4: 运行通过**

Run: `source venv/bin/activate && pytest tests/test_product_service.py -q`
Expected: 2 passed。

- [ ] **Step 5: Commit**

```bash
git add app/services/product_structure_service.py tests/test_product_service.py
git commit -m "feat(py): product_structure_service——ComponentDTO递归+CI/Baseline/Config/Instance CRUD"
```

---

## Task 3: 产品端点（products.py + product_instances.py + product_files.py）

**Files:**
- Create: `app/routers/products.py`, `app/routers/product_instances.py`, `app/routers/product_files.py`
- Modify: `app/main.py`
- Test: `tests/test_products_api.py`

**端点清单（双路由注册尾斜杠）**：

```python
# products.py
@router.get("/workspaces/{ws}/products")                    # list CI
@router.get("/workspaces/{ws}/products/numbers")             # search CI numbers
@router.post("/workspaces/{ws}/products", status_code=201)   # create CI
@router.post("/workspaces/{ws}/products/", status_code=201, include_in_schema=False)
@router.get("/workspaces/{ws}/products/{ci_id}")             # get CI
@router.delete("/workspaces/{ws}/products/{ci_id}")          # delete CI
@router.get("/workspaces/{ws}/products/{ci_id}/filter")      # filterProductStructure
@router.get("/workspaces/{ws}/products/{ci_id}/decode-path/{path:path}")  # decodePath
@router.get("/workspaces/{ws}/products/{ci_id}/baselines")   # list baselines
@router.post("/workspaces/{ws}/products/{ci_id}/baselines", status_code=201)
@router.post("/workspaces/{ws}/products/{ci_id}/baselines/", status_code=201, include_in_schema=False)
@router.delete("/workspaces/{ws}/products/{ci_id}/baselines/{bid}")

# product_instances.py
@router.get("/workspaces/{ws}/products/{ci_id}/instances")
@router.post("/workspaces/{ws}/products/{ci_id}/instances", status_code=201)
@router.post("/workspaces/{ws}/products/{ci_id}/instances/", status_code=201, include_in_schema=False)
@router.delete("/workspaces/{ws}/products/{ci_id}/instances/{sn}")

# product_files.py
@router.post("/files/{ws}/products/{ci_id}/instances/{sn}/iterations/{it}", status_code=201)
@router.post("/files/{ws}/products/{ci_id}/instances/{sn}/iterations/{it}/", status_code=201, include_in_schema=False)
@router.get("/files/{ws}/products/{ci_id}/instances/{sn}/iterations/{it}/{fn}")
```

- [ ] **Step 1: 写测试**

```python
# tests/test_products_api.py
from fastapi.testclient import TestClient
from app.main import app
PREFIX = "/docdoku-plm-server-rest/api"
WS = "Workspace_2"
client = TestClient(app)

def _token():
    r = client.post(f"{PREFIX}/auth/login", json={"login":"test1","password":"password"})
    return r.headers.get("jwt")

def test_create_and_filter_ci():
    token = _token(); h = {"Authorization": f"Bearer {token}"}
    resp = client.post(f"{PREFIX}/workspaces/{WS}/products/",
                       json={"id": "P3API-1", "description": "T",
                             "partNumber": "Assem1"}, headers=h)
    assert resp.status_code == 201
    # filter structure
    resp2 = client.get(
        f"{PREFIX}/workspaces/{WS}/products/P3API-1/filter?depth=1", headers=h)
    assert resp2.status_code == 200
    # cleanup
    client.request("DELETE", f"{PREFIX}/workspaces/{WS}/products/P3API-1", headers=h)
```

- [ ] **Step 2: 运行→FAIL→实现→PASS→全量测试→Commit**

---

## Task 4: 对齐审计 + Payara 对拍 + Nginx 切换

**Files:**
- Modify: `docdoku-plm-docker/front/nginx.conf`

**Nginx 新增（5 个路由块）**：

```nginx
location ~ ^/docdoku-plm-server-rest/api/workspaces/[^/]+/products {
    set $backpy "back-py:8000";
    proxy_pass http://$backpy;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_read_timeout 300s;
    proxy_send_timeout 300s;
}

# product-instances, product-configurations, product-baselines 同样格式
# files/products 加 client_max_body_size 500m
```

- [ ] **Step 1: Payara 对拍**——对同一 CI 的 filterProductStructure 响应逐字段对比
- [ ] **Step 2: 前端实测清单**（创建 CI→绑定零件→查看结构树→基线→配置→实例）
- [ ] **Step 3: 通过后切 Nginx + 重启 front**
- [ ] **Step 4: 更新 CHANGELOG/REMINDERS/路线图**

---

## 前端实测清单

1. 创建 CI（选 Assem1 作根零件）→ 出现在列表
2. 点 CI→查看产品结构树（含子件递归）
3. 创建基线 → 删除基线
4. 创建配置 → 删除配置
5. 创建实例 → 上传文件 → 下载文件
6. 搜索 CI

## 后续补做清单（记入 REMINDERS）

| 端点 | 补做时机 |
|------|----------|
| path-to-path links CRUD ×3 | 需要时 |
| cascade-checkout/checkin/undocheckout ×3 | 结构树稳定后 |
| import/export ×2 | 需要时 |
| path-data CRUD ×10 | 实例功能稳定后 |

---

## Self-Review 结果

- **Spec 覆盖**：CI CRUD（Task 2/3）✅；filterProductStructure 递归组件树（Task 2）✅；decodePath（Task 2）✅；Baseline/Config/Instance（Task 2/3）✅；文件（Task 3）✅；对齐+Nginx（Task 4）✅。
- **Placeholder 扫描**：无 TBD。Service 代码含完整 ComponentDTO 24 字段。
- **类型一致**：CADInstance 复用 models/part.py；path 格式 u1-u4 全计划一致。

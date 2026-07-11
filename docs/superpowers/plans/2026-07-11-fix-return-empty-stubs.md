# fix-return-empty-stubs 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task.

**Goal:** 修复 `docdoku-plm-server-py` 中所有不对齐 Java 原版的 `return []` / `return {}` ——分两类：（A）补全未实现的占位桩函数；（B）修复错误处理差异，让 Python 与 Java 的 HTTP 语义一致。

**Architecture:** 全部改动限于 FastAPI 后端（`docdoku-plm-server-py/`）。错误处理类通过已有的 `app/core/exceptions.py` 体系对齐 Java 异常→HTTP 状态码映射；未实现函数直接查数据库（SQLAlchemy ORM + raw SQL），风格与已有代码一致。

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy 2.x, PostgreSQL

## Global Constraints

- 不引入新依赖
- 代码注释用中文，函数/变量名用英文
- 不修改数据库 schema，只读取已有表
- 不提交 git commit，除非明确要求
- 修改前先读取目标文件确认内容
- 每个 Task 完成后可独立验证（重启 back-py 容器 + curl 测试端点）

---

## 文件清单

| 文件 | 改动类型 |
|------|---------|
| `app/services/product_structure.py` | 修复错误处理（Task 1） |
| `app/routers/products.py` | 修复错误处理（Task 2）+ 补全 `ci_paths`、`ci_document_links`（Task 7） |
| `app/routers/part.py` | 修复错误处理（Task 3）+ 补全 `get_baselines`、`used_by_product`、`filter_by_baseline`（Task 5） |
| `app/routers/product_instances.py` | 修复错误处理（Task 4） |
| `app/services/public_entity_manager.py` | 修复错误处理（Task 4） |
| `app/models/configuration/baselined_part.py` | 增补缺失列（Task 5 前置） |
| `app/routers/workspaces.py` | 补全 `tag_documents`（Task 6） |
| `app/services/documents/document_workflow_manager.py` | 补全 `get_aborted_workflows`（Task 8） |

---

## Task 1：修复服务层错误处理（product_structure.py）

**Files:**
- Modify: `app/services/product_structure.py:154-157`（`filter_product_structure`）
- Modify: `app/services/product_structure.py:460-463`（`decode_path`）

**问题：** 两处在查不到 `PartMaster` 时静默 `return []`，Java 此时抛 `PartMasterNotFoundException` → HTTP 404。

- [ ] **Step 1: 读取文件确认当前内容**

```bash
# 读取 product_structure.py 第 145-170 行 和 455-470 行
```

用 Read 工具读取 `docdoku-plm-server-py/app/services/product_structure.py`，offset=145, limit=30 和 offset=455, limit=20。

- [ ] **Step 2: 修复 `filter_product_structure`（第 154-157 行）**

将：
```python
if master is None or not master.revisions:
    return []
```
改为：
```python
if master is None:
    raise PartMasterNotFoundException("PartMasterNotFoundException", root_pn)
if not master.revisions:
    return []   # 无修订版本时合法返空
```

确认文件顶部已导入 `PartMasterNotFoundException`；若无则在 import 块加：
```python
from app.core.exceptions import PartMasterNotFoundException
```

- [ ] **Step 3: 修复 `decode_path`（第 462-463 行）**

将：
```python
if master is None:
    return []
```
改为：
```python
if master is None:
    raise PartMasterNotFoundException("PartMasterNotFoundException", root_pn)
```

- [ ] **Step 4: 验证**

```bash
# 在 back-py 容器内直接 Python 导入验证语法
docker exec docdoku-plm-docker-back-py-1 python -c \
  "from app.services.product_structure import ProductStructureService; print('OK')"
```

---

## Task 2：修复路由层错误处理（products.py）

**Files:**
- Modify: `app/routers/products.py:150-155`（`filter_structure`）
- Modify: `app/routers/products.py:270-290`（`last_release`）
- Modify: `app/routers/products.py:325-350`（`path_choices`）
- Modify: `app/routers/products.py:354-362`（`versions_choices`）
- Modify: `app/routers/products.py:447-453`（`_collect_ci_parts`）

**问题模式：** `try: ci = svc.get_ci(...) except HTTPException: return []` 吞掉了 `get_ci` 抛出的 404，客户端收到 200 + 空列表。

- [ ] **Step 1: 读取文件**

读取 `products.py` 第 140-210 行、265-370 行、445-460 行。

- [ ] **Step 2: 修复 `filter_structure`（line 153-154）**

将：
```python
if not result:
    return {}
```
改为：
```python
if not result:
    raise HTTPException(status_code=404, detail="Product structure not found for this configuration item")
```

- [ ] **Step 3: 修复 `last_release`（line 275-286）**

将：
```python
try:
    ci = svc.get_ci(db, ws, ci_id)
except HTTPException:
    return []
```
改为（移除 try/except，让 get_ci 的异常向上传播）：
```python
ci = svc.get_ci(db, ws, ci_id)
```

并将：
```python
if rev is None:
    return []
```
改为：
```python
if rev is None:
    raise HTTPException(status_code=404, detail="No released revision for this configuration item")
```

- [ ] **Step 4: 修复 `path_choices`（line 328-348）**

将第一处：
```python
try:
    ci = svc.get_ci(db, ws, ci_id)
except HTTPException:
    return []
```
改为：
```python
ci = svc.get_ci(db, ws, ci_id)
```

将第二处（DB 异常吞掉）：
```python
except Exception:
    return []
```
改为：
```python
except Exception:
    raise HTTPException(status_code=500, detail="Failed to retrieve path choices")
```

- [ ] **Step 5: 修复 `versions_choices`（line 357-360）**

将：
```python
try:
    ci = svc.get_ci(db, ws, ci_id)
except HTTPException:
    return []
```
改为：
```python
ci = svc.get_ci(db, ws, ci_id)
```

- [ ] **Step 6: 修复 `_collect_ci_parts`（line 448-451）**

同样模式，移除 `try/except HTTPException: return []`，改为直接调用 `svc.get_ci(db, ws, ci_id)`。

- [ ] **Step 7: 验证**

```bash
docker exec docdoku-plm-docker-back-py-1 python -c \
  "from app.routers.products import router; print('OK')"
```

---

## Task 3：修复 part.py 错误处理

**Files:**
- Modify: `app/routers/part.py:454-457`（`get_instances`）

**问题：** 查不到 `PartIteration` 时返回 `[]`，Java 此时抛 404。

- [ ] **Step 1: 读取文件**

读取 `part.py` 第 425-465 行。

- [ ] **Step 2: 修复（line 456-457）**

将：
```python
if not pi:
    return []
```
改为：
```python
if not pi:
    from app.core.exceptions import PartIterationNotFoundException
    raise PartIterationNotFoundException("PartIterationNotFoundException",
                                         part_number, version)
```

确认 `PartIterationNotFoundException` 签名（查看 `app/core/exceptions.py`），根据实际签名调整参数。

- [ ] **Step 3: 验证**

```bash
docker exec docdoku-plm-docker-back-py-1 python -c \
  "from app.routers.part import router; print('OK')"
```

---

## Task 4：修复 product_instances.py 和 public_entity_manager.py 错误处理

**Files:**
- Modify: `app/routers/product_instances.py:385-389`（`instance_link_path_part`）
- Modify: `app/services/public_entity_manager.py:62-65`（`get_binary_resource`）

- [ ] **Step 1: 读取文件**

读取 `product_instances.py` 第 375-400 行，读取 `public_entity_manager.py` 全文。

- [ ] **Step 2: 修复 `instance_link_path_part`（line 387-389）**

将：
```python
if not decoded:
    return {}
last = decoded[-1] if decoded else {}
return last
```
改为（移除防御检查，依赖 `decode_path` 服务层的异常传播）：
```python
last = decoded[-1]
return last
```

Task 1 修复 `decode_path` 后，`decoded` 为空时已经会抛 404，此处无需额外检查。

- [ ] **Step 3: 修复 `get_binary_resource`（line 63-65）**

将：
```python
if row:
    return dict(row._mapping)
return {}
```
改为：
```python
if row:
    return dict(row._mapping)
from app.core.exceptions import BinaryResourceNotFoundException  # 或用通用异常
raise HTTPException(status_code=404, detail=f"BinaryResource not found: {full_name}")
```

若 `BinaryResourceNotFoundException` 不存在，直接用 `HTTPException(404, ...)` 即可。

- [ ] **Step 4: 验证**

```bash
docker exec docdoku-plm-docker-back-py-1 python -c \
  "from app.routers.product_instances import router; print('OK')"
docker exec docdoku-plm-docker-back-py-1 python -c \
  "from app.services.public_entity_manager import PublicEntityManager; print('OK')"
```

---

## Task 5：补全 part.py 三个未实现函数（前置：修复 BaselinedPart 模型）

**Files:**
- Modify: `app/models/configuration/baselined_part.py`（增补缺失列）
- Modify: `app/routers/part.py:441-481`（`get_baselines`、`used_by_product`、`filter_by_baseline`）

### Step 1：先修复 BaselinedPart ORM 模型

- [ ] **Step 1.1: 读取模型文件**

读取 `app/models/configuration/baselined_part.py` 全文。

- [ ] **Step 1.2: 增补缺失列**

检查是否已有 `target_iteration`、`target_partmaster_partnumber`、`target_workspace_id`、`target_partrevision_version`。若缺失，添加：
```python
target_workspace_id = Column("target_workspace_id", String, primary_key=True)
target_partmaster_partnumber = Column("target_partmaster_partnumber", String, primary_key=True)
target_partrevision_version = Column("target_partrevision_version", String)
target_iteration = Column("target_iteration", Integer, primary_key=True)
```

- [ ] **Step 1.3: 验证模型映射**

```bash
docker exec docdoku-plm-docker-back-py-1 python -c "
from app.models.configuration.baselined_part import BaselinedPart
print([c.key for c in BaselinedPart.__table__.columns])
"
```

### Step 2：实现 `get_baselines`（part.py:441）

- [ ] **Step 2.1: 读取当前占位代码**

读取 `part.py` 第 435-465 行，确认函数签名和路由装饰器。

- [ ] **Step 2.2: 实现**

用子查询找到包含该 PartRevision 的所有基线：

```python
@router.get("/{workspace_id}/parts/{part_key}/baselines")
def get_baselines(
    workspace_id: str,
    part_key: str,
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_user),
):
    """获取该零件修订版所在的所有基线（对齐 Java PartResource.getBaselinesWherePartRevisionHasIterations）"""
    number, version = _split_part_key(part_key)

    from app.models.configuration.baselined_part import BaselinedPart
    from app.models.configuration.product_baseline import ProductBaseline

    # 子查询：找到所有包含该 PartRevision 的 PartCollection ID
    subq = (
        db.query(BaselinedPart.partcollection_id)
        .filter(
            BaselinedPart.target_workspace_id == workspace_id,
            BaselinedPart.target_partmaster_partnumber == number,
            BaselinedPart.target_partrevision_version == version,
        )
        .subquery()
    )

    baselines = (
        db.query(ProductBaseline)
        .filter(ProductBaseline.partcollection_id.in_(subq))
        .order_by(ProductBaseline.name)
        .all()
    )

    # 返回简化 DTO（对齐 Java ProductBaselineDTO）
    return [
        {
            "id": b.id,
            "name": b.name,
            "description": b.description,
            "type": b.baseline_type,
            "configurationItemId": b.configurationitem_id,
            "creationDate": b.creation_date.isoformat() if b.creation_date else None,
        }
        for b in baselines
    ]
```

确认 `ProductBaseline` 的列名（`partcollection_id`、`configurationitem_id` 等）与 ORM 实际定义一致。

### Step 3：实现 `used_by_product`（part.py:463）

- [ ] **Step 3.1: 实现**

```python
@router.get("/{workspace_id}/parts/{part_key}/used-by")
def used_by_product(
    workspace_id: str,
    part_key: str,
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_user),
):
    """获取引用此零件修订版的所有产品实例（对齐 Java PartResource.getProductInstanceMasters）"""
    number, version = _split_part_key(part_key)

    from app.models.configuration.baselined_part import BaselinedPart
    from app.models.configuration.product_baseline import ProductBaseline
    from app.models.configuration.product_instance_master import ProductInstanceMaster
    from sqlalchemy import and_

    # 联查：ProductInstanceMaster → ProductBaseline → BaselinedPart
    results = (
        db.query(ProductInstanceMaster)
        .distinct()
        .join(
            ProductBaseline,
            and_(
                ProductBaseline.configurationitem_workspace_id == ProductInstanceMaster.workspace_id,
                ProductBaseline.configurationitem_id == ProductInstanceMaster.configurationitem_id,
            ),
        )
        .join(
            BaselinedPart,
            BaselinedPart.partcollection_id == ProductBaseline.partcollection_id,
        )
        .filter(
            BaselinedPart.target_workspace_id == workspace_id,
            BaselinedPart.target_partmaster_partnumber == number,
            BaselinedPart.target_partrevision_version == version,
        )
        .order_by(ProductBaseline.configurationitem_id)
        .all()
    )

    # Java 中专门将 productInstanceIterations 置 null
    return [
        {
            "serialNumber": pim.serialnumber,
            "configurationItemId": pim.configurationitem_id,
            "workspaceId": pim.workspace_id,
            "productInstanceIterations": None,
            "acl": None,
        }
        for pim in results
    ]
```

### Step 4：实现 `filter_by_baseline`（part.py:473）

- [ ] **Step 4.1: 实现**

```python
@router.get("/{workspace_id}/parts/{part_number}/filter-by-baseline")
def filter_by_baseline(
    workspace_id: str,
    part_number: str,
    baseline_id: str = Query(...),
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_user),
):
    """按基线过滤零件，返回该零件在基线中被钉住的迭代版本（对齐 Java PartsResource.filterPartMasterInBaseline）"""
    from app.models.configuration.baselined_part import BaselinedPart
    from app.models.configuration.product_baseline import ProductBaseline
    from app.models.part.part_iteration import PartIteration

    try:
        bl_id = int(baseline_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="baseline_id 必须是整数")

    baseline = db.query(ProductBaseline).filter(ProductBaseline.id == bl_id).first()
    if baseline is None:
        raise HTTPException(status_code=404, detail="Baseline not found")
    if baseline.configurationitem_workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Baseline not in this workspace")

    # 在基线的 PartCollection 中查找该零件
    bp = (
        db.query(BaselinedPart)
        .filter(
            BaselinedPart.partcollection_id == baseline.partcollection_id,
            BaselinedPart.target_workspace_id == workspace_id,
            BaselinedPart.target_partmaster_partnumber == part_number,
        )
        .first()
    )

    if bp is None:
        raise HTTPException(status_code=404, detail="Part not found in baseline")

    # 加载对应的 PartIteration
    pi = (
        db.query(PartIteration)
        .filter(
            PartIteration.workspace_id == workspace_id,
            PartIteration.partmaster_partnumber == part_number,
            PartIteration.partrevision_version == bp.target_partrevision_version,
            PartIteration.iteration == bp.target_iteration,
        )
        .first()
    )

    if pi is None:
        raise HTTPException(status_code=404, detail="Part iteration not found in database")

    # 复用已有的 map_revision 或直接构造 PartIterationDTO
    return map_revision(pi.revision)  # map_revision 已在 part.py 顶部导入
```

- [ ] **Step 5: 验证**

```bash
docker exec docdoku-plm-docker-back-py-1 python -c \
  "from app.routers.part import router; print('OK')"
```

---

## Task 6：补全 workspaces.py 的 `tag_documents`

**Files:**
- Modify: `app/routers/workspaces.py:315-320`（`tag_documents`）

**对应 Java：** `TagResource.getDocumentsWithGivenTagIdAndWorkspaceId` — 按标签查文档，返回 Light DocumentRevisionDTO 列表。

- [ ] **Step 1: 读取文件**

读取 `workspaces.py` 第 305-330 行，确认函数签名、路由装饰器、已导入的模型。

- [ ] **Step 2: 实现**

```python
def tag_documents(
    workspace_id: str,
    tag_id: str,
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_user),
):
    """按标签查询文档修订版（对齐 Java TagResource.getDocumentsWithGivenTagIdAndWorkspaceId）"""
    from app.models.document.document_revision import DocumentRevision
    from sqlalchemy import text

    # 使用 raw SQL 查询（与项目中其他文档查询保持一致风格）
    rows = db.execute(text("""
        SELECT DISTINCT dr.documentmaster_id, dr.version, dr.workspace_id,
               dr.title, dr.location_completepath, dr.creation_date,
               dr.checkoutuser_login, dr.checkoutdate
        FROM documentrevision dr
        JOIN documentrevision_tag drt
          ON dr.workspace_id = drt.documentmaster_workspace_id
         AND dr.documentmaster_id = drt.documentmaster_id
         AND dr.version = drt.documentrevision_version
        WHERE drt.tag_workspace_id = :ws
          AND drt.tag_label = :tag
    """), {"ws": workspace_id, "tag": tag_id}).fetchall()

    result = []
    for row in rows:
        # createLightDocumentRevisionDTO：获取最后一个迭代，tags=null, workflow=null
        last_it_row = db.execute(text("""
            SELECT iteration, title, creation_date
            FROM documentiteration
            WHERE workspace_id = :ws
              AND documentmaster_id = :did
              AND documentrevision_version = :v
            ORDER BY iteration DESC
            LIMIT 1
        """), {"ws": row.workspace_id, "did": row.documentmaster_id, "v": row.version}).first()

        result.append({
            "documentMasterId": row.documentmaster_id,
            "version": row.version,
            "workspaceId": row.workspace_id,
            "title": row.title,
            "path": row.location_completepath or "",
            "checkOutUser": row.checkoutuser_login,
            "checkOutDate": row.checkoutdate.isoformat() if row.checkoutdate else None,
            "creationDate": row.creation_date.isoformat() if row.creation_date else None,
            # Light DTO：只保留最后一个迭代
            "documentIterations": [
                {
                    "iteration": last_it_row.iteration,
                    "title": last_it_row.title,
                    "creationDate": last_it_row.creation_date.isoformat() if last_it_row.creation_date else None,
                }
            ] if last_it_row else [],
            "lastIteration": last_it_row.iteration if last_it_row else 0,
            # Light DTO：tags 和 workflow 置 null
            "tags": None,
            "workflow": None,
            "lifeCycleState": None,
            "iterationSubscription": False,
            "stateSubscription": False,
        })

    return result
```

- [ ] **Step 3: 验证**

```bash
docker exec docdoku-plm-docker-back-py-1 python -c \
  "from app.routers.workspaces import router; print('OK')"
```

---

## Task 7：补全 products.py 两个未实现函数

**Files:**
- Modify: `app/routers/products.py:550-570`（`ci_paths`、`ci_document_links`）

### `ci_paths`（对应 Java `ProductResource.searchPaths`）

- [ ] **Step 1: 读取文件**

读取 `products.py` 第 543-600 行，并读取 `product_structure.py` 中的 `PSFilterVisitor` 相关代码确认可用 API。

- [ ] **Step 2: 实现 `ci_paths`**

Java 逻辑：遍历 CI 的整个产品结构树，用正则匹配 `partNumber`、`partName` 或路径字符串。

```python
@router.get("/{workspace_id}/products/{ci_id}/paths")
def ci_paths(
    workspace_id: str,
    ci_id: str,
    search: str = Query(None),
    config_spec: str = Query("wip"),
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_user),
):
    """在装配结构中搜索路径（对齐 Java ProductResource.searchPaths）"""
    import re
    from app.services.product_structure import ProductStructureService
    from app.models.product.configuration_item import ConfigurationItem
    from app.models.part.part_master import PartMaster

    svc = ProductStructureService()
    ci = svc.get_ci(db, workspace_id, ci_id)  # CI 不存在则抛 404

    root_master = (
        db.query(PartMaster)
        .filter(
            PartMaster.workspace_id == workspace_id,
            PartMaster.number == ci.partmaster_partnumber,
        )
        .first()
    )
    if root_master is None:
        return []

    # 编译搜索正则（search 为空时匹配所有）
    try:
        pattern = re.compile(search) if search else None
    except re.error:
        pattern = re.compile(re.escape(search)) if search else None

    collected: list[str] = []

    def walk(master, path_parts: list[str]):
        """递归遍历装配结构，收集匹配路径"""
        path_str = "-".join(path_parts)
        # 判断是否匹配
        if pattern is None or (
            pattern.search(master.number or "")
            or pattern.search(master.name or "")
            or pattern.search(path_str)
        ):
            if path_str:  # 跳过根节点
                collected.append(path_str)

        # 获取最新修订版的最后迭代的子链接
        if not master.revisions:
            return
        last_rev = master.revisions[-1]
        if not last_rev.iterations:
            return
        last_it = last_rev.iterations[-1]
        for link in (last_it.components or []):
            child_master = (
                db.query(PartMaster)
                .filter(
                    PartMaster.workspace_id == workspace_id,
                    PartMaster.number == link.component_partnumber,
                )
                .first()
            )
            if child_master:
                child_path = path_parts + [str(link.id)]
                walk(child_master, child_path)

    walk(root_master, [])
    return [{"path": p} for p in collected]
```

> **注意**：`walk` 的递归深度在大型装配体中可能很深。若已有 `PSFilterVisitor` 提供了遍历 API，优先复用（读取 `product_structure.py` 后根据实际 API 调整）。

### `ci_document_links`（对应 Java `ProductResource.getDocumentLinksForGivenPartIteration`）

- [ ] **Step 3: 实现 `ci_document_links`**

Java 核心逻辑：
1. 解析 `config_spec` → ProductBaseline
2. 获取 baseline 的 DocumentCollection → BaselinedDocuments
3. 获取 PartIteration 的 linkedDocuments
4. 交叉匹配（DocumentRevisionKey 相同），返回 `DocumentIterationLinkDTO`

```python
@router.get("/{workspace_id}/products/{ci_id}/{part_number}-{part_version}-{part_iteration}/{config_spec}/document-links")
def ci_document_links(
    workspace_id: str,
    ci_id: str,
    part_number: str,
    part_version: str,
    part_iteration: int,
    config_spec: str,
    db: Session = Depends(get_db),
    current_user: Account = Depends(get_current_user),
):
    """获取零件迭代在指定基线中关联的文档（对齐 Java ProductResource.getDocumentLinksForGivenPartIteration）"""
    from sqlalchemy import text
    from app.models.configuration.product_baseline import ProductBaseline
    from app.models.configuration.product_instance_master import ProductInstanceMaster

    # 1. 解析 config_spec → baseline
    baseline = None
    if config_spec.startswith("pi-"):
        serial_number = config_spec[3:]
        last_pii = db.execute(text("""
            SELECT basedon_baseline_id FROM productinstanceiteration
            WHERE workspace_id = :ws AND configurationitem_id = :ci
              AND prdinstancemaster_serialnumber = :sn
            ORDER BY iteration DESC LIMIT 1
        """), {"ws": workspace_id, "ci": ci_id, "sn": serial_number}).first
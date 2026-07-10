# Query 执行引擎实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: 用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务执行。步骤用 checkbox (`- [ ]`) 跟踪。

**Goal:** 将 Payara 的自定义查询「保存 + 执行」迁移到 FastAPI：实现 QueryRule 树 → 动态 SQL 的 PartRevision 查询执行、PathData（pd-attr-\*）查询、context 产品分解结构（PBS）过滤 + mergeRows、以及 QueryResult JSON 序列化。补齐查询保存（递归写入 queryrule 树）。

**Architecture:** 递归遍历 QueryRule 树（AND/OR 组合）→ 按 `field` 前缀路由到 PartMaster / PartRevision / PartIteration / author / 8 种 InstanceAttribute → 用参数化原生 SQL（对齐现有 `parts.py` / `part_mapper.py` 风格）编译 WHERE → 执行 → 权限/签出后过滤 → `part_mapper.map_revision` 映射为 DTO → 按 `selects` 序列化为 JSON 行数组。对齐 Payara `PartRevisionQueryDAO` / `PathDataQueryDAO` / `ProductManagerBean.filterProductBreakdownStructure` / `QueryResult`。

**Tech Stack:** FastAPI, SQLAlchemy Core (`text()` 参数化 SQL), 现有 ORM/Service。

## Global Constraints（铁律）
- **对齐 Payara**：字段前缀、operator 语义、type 强制转换、返回结构以 Java 源码为准。
- **部署**：`docker cp` + `docker restart docdoku-plm-docker-back-py-1`，不 rebuild。容器端口 8009。
- **测试基线**：pytest ≥176 passed / 1 skipped 不退化；对比脚本 158 端点不退化。
- **编辑规范**：优先改已有文件；注释中文，函数/变量英文；`extra=forbid` 不擅改。
- **SQL 风格**：参数化 `text()`，禁止字符串拼接用户值（防注入）。所有属性值列用原生 SQL 访问（ORM 基类列名不全）。

---

## 已确认事实（调研结论，实施时无需重复确认）

**数据库表/列（已用 postgres 确认）：**
```
query(id PK, name, creationdate, author_workspace_id, author_login, queryrule_id, pathdata_queryrule_id)
queryrule(qid PK, cond, field, id, operator, type, parent_query_rule 自引用)
queryrule_values(queryrule_id FK, value, value_order)
query_selects(query_id FK, selects)
query_order_by(query_id FK, orderbylist)
query_grouped_by(query_id FK, groupedbylist)
querycontext(id PK, configurationitemid, serialnumber, workspaceid, query_id FK)
instanceattribute(id PK, dtype, name, booleanvalue, datevalue, indexvalue, numbervalue,
                  textvalue, longtextvalue, urlvalue, partmaster_workspace_id, partmaster_partnumber)
   → 8 种子类同一张单表，dtype 判别；PART_NUMBER 用 partmaster_* 列（无独立表）
partiteration_attribute(workspace_id, partmaster_partnumber, partrevision_version, iteration,
                        instanceattribute_id, attribute_order)
partrevision_tag(partmaster_workspace_id, partmaster_partnumber, partrevision_version,
                 tag_workspace_id, tag_label)
pathdataiteration_attribute(pathdata_iteration, pathdatamaster_id, instanceattribute_id, attribute_order)
```

**ID 生成（用序列，不要手动 max+1）：**
```
nextval('query_id_seq') / nextval('queryrule_qid_seq') / nextval('querycontext_id_seq')
```

**dtype 值映射**（复用 `app/services/product_structure.py:376-386` 的 `_DTYPE_TO_TYPE`）：
`InstanceTextAttribute→TEXT / InstanceNumberAttribute→NUMBER / InstanceDateAttribute→DATE /
InstanceBooleanAttribute→BOOLEAN / InstanceURLAttribute→URL / InstanceListOfValuesAttribute→LOV /
InstanceLongTextAttribute→LONG_TEXT / InstancePartNumberAttribute→PART_NUMBER`。
查询时按前缀反查 dtype 集合（见 Task 2 属性路由）。

**partrevision 表关键列：** `workspace_id, partmaster_partnumber, version, status(0/1/2), publicshared, creationdate, checkoutdate, checkoutuser_login, author_login, author_workspace_id, acl_id`。
**partiteration 表关键列：** `workspace_id, partmaster_partnumber, partrevision_version, iteration, checkindate, modificationdate`。
**partmaster 表关键列：** `workspace_id, partnumber, name, type, standardpart`。

**复用资产：**
- `app/routers/parts.py`：`get_queries:251`、`_load_query_rule:286`、`_load_query_contexts:313`、`delete_query:375`、`_delete_query_rule:400`、stub `post_workspace_query:329`、`post_queries:354`。
- `app/services/part_mapper.py`：`map_revision(pr, db)`（PartRevision ORM → PartRevisionDTO）。
- `app/services/factory/acl_factory.py`：`check_read_access(db, acl_id, user_login, is_admin, workspace_id=None)`。
- 签出隐藏逻辑参照 `app/services/product_manager.py:79-84`（`checkout_user_login` 非空且 != 当前用户）。
- `app/services/product_structure.py`：`filter_product_structure(db, ws, ci_id, config_spec, path, depth, user_login, is_admin)`、`parse_config_spec_str`。
- ORM：`app/models/product/{part_master,part_revision,part_iteration}.py`；`app/models/configuration/{path_data_master,path_data_iteration,product_instance_master,product_instance_iteration}.py`。
- Schema：`app/schemas/query.py`(QueryDTO)、`query_rule.py`(QueryRuleDTO)、`query_context.py`(QueryContextDTO)、`app/schemas/part/part_revision.py`(PartRevisionDTO)。

**operator 语义（对齐 `QueryPredicateBuilder.java`）：**
| operator | string/PART_NUMBER | double/date |
|----------|--------------------|-------------|
| `equal` | `= v` | double: `= v`；date: **`>= d AND < d+1天`** |
| `not_equal` | `<> v`（或 `NOT (= v)`） | 同 equal 取反 |
| `contains` | `LIKE %v%` | — |
| `not_contains` | `NOT LIKE %v%` | — |
| `begins_with` | `LIKE v%` | — |
| `not_begins_with` | `NOT LIKE v%` | — |
| `ends_with` | `LIKE %v` | — |
| `not_ends_with` | `NOT LIKE %v` | — |
| `less` | — | `< v` |
| `less_or_equal` | — | `<= v` |
| `greater` | — | `> v` |
| `greater_or_equal` | — | `>= v` |
| `between` | — | `BETWEEN v0 AND v1`（需 2 值） |

type 强制转换：`string`→原样；`double`→float；`date`→`DateUtils`/`datetime` 解析；`status`→枚举整数（WIP=0/RELEASED=1/OBSOLETE=2），要求 `len(values)==1`。

**字段前缀路由（叶子节点，对齐 `PartRevisionQueryDAO.getRulePredicate`）：**
| 前缀 | 去前缀 | 目标 |
|------|--------|------|
| `pm.` | `[3:]` | partmaster.{number,name,type,standardpart} |
| `pr.` | `[3:]` | partrevision.{version,status,creationdate,lifeCycleState}；特殊：checkInDate/modificationDate→partiteration 末迭代；tags→partrevision_tag join；linkedDocuments→恒 true |
| `author.` | `[7:]` | author（account.login / account.name）经 author_login/author_workspace_id |
| `attr-TEXT.` | `[10:]` | instanceattribute dtype∈TEXT，比较 textvalue |
| `attr-LONG_TEXT.` | `[15:]` | LONG_TEXT，longtextvalue |
| `attr-DATE.` | `[10:]` | DATE，datevalue |
| `attr-BOOLEAN.` | `[13:]` | BOOLEAN，booleanvalue（equal/not_equal） |
| `attr-URL.` | `[9:]` | URL，urlvalue |
| `attr-NUMBER.` | `[12:]` | NUMBER，numbervalue |
| `attr-LOV.` | `[9:]` | LOV，indexvalue（equal/not_equal，整数索引） |
| `attr-PART_NUMBER.` | `[17:]` | PART_NUMBER，partmaster_partnumber（string 语义） |

PathData 前缀同构：`pd-attr-{TYPE}.`，挂在 `pathdataiteration_attribute`。

---

## Task 1: 查询保存 `_save_query` + 接线 POST 端点

**Files:**
- Modify: `app/routers/parts.py`（新增 `_save_query`/`_save_query_rule` 辅助函数；改 `post_workspace_query:329-347`、`post_queries:350-369` 调用保存）
- Test: `docdoku-plm-server-py/tests/test_query_save.py`

**Interfaces:**
- Produces: `_save_query(db, workspace_id, author_login, body: dict) -> int`（返回新 query id）；`_save_query_rule(db, rule: dict|None) -> int|None`（递归写 queryrule 树，返回根 qid）。

- [ ] **Step 1: 写失败测试** `tests/test_query_save.py`

```python
import pytest
from sqlalchemy import text
from app.core.database import SessionLocal
from app.routers.parts import _save_query, _load_query_rule

def test_save_query_writes_rule_tree_and_selects():
    db = SessionLocal()
    try:
        body = {
            "name": "SEED-Q-SAVE-1",
            "queryRule": {
                "condition": "AND", "operator": None, "field": None, "type": None,
                "values": [],
                "rules": [
                    {"condition": None, "field": "pm.number", "type": "string",
                     "operator": "equal", "values": ["SEED-PART-1"], "rules": []},
                    {"condition": None, "field": "pr.status", "type": "status",
                     "operator": "equal", "values": ["1"], "rules": []},
                ],
            },
            "pathDataQueryRule": None,
            "selects": ["pm.number", "pr.version"],
            "orderByList": ["pm.number"],
            "groupedByList": [],
            "contexts": [],
        }
        qid = _save_query(db, "SEED-WS", "SEED-USER", body)
        db.commit()
        assert isinstance(qid, int) and qid > 0
        row = db.execute(text("SELECT name, queryrule_id FROM query WHERE id=:q"),
                         {"q": qid}).fetchone()
        assert row[0] == "SEED-Q-SAVE-1"
        rule = _load_query_rule(db, row[1])
        assert rule["condition"] == "AND"
        assert len(rule["rules"]) == 2
        assert {r["field"] for r in rule["rules"]} == {"pm.number", "pr.status"}
        selects = [s[0] for s in db.execute(
            text("SELECT selects FROM query_selects WHERE query_id=:q"), {"q": qid}).fetchall()]
        assert selects == ["pm.number", "pr.version"]
    finally:
        db.execute(text("DELETE FROM query WHERE name='SEED-Q-SAVE-1'"))
        db.commit(); db.close()
```

- [ ] **Step 2: 运行确认失败** `pytest tests/test_query_save.py -v` → FAIL (`_save_query` 不存在)

- [ ] **Step 3: 实现 `_save_query` / `_save_query_rule`**（加在 `_delete_query_rule` 之后）

```python
def _save_query_rule(db, rule):
    """递归写入 queryrule 树，返回根 qid（对齐 Java QueryDAO.persistQueryRules）。"""
    if rule is None:
        return None
    from sqlalchemy import text
    qid = db.execute(text("SELECT nextval('queryrule_qid_seq')")).scalar()
    db.execute(text(
        "INSERT INTO queryrule (qid, cond, field, id, operator, type, parent_query_rule) "
        "VALUES (:qid, :cond, :field, :rid, :op, :type, NULL)"
    ), {"qid": qid, "cond": rule.get("condition"), "field": rule.get("field"),
        "rid": rule.get("id"), "op": rule.get("operator"), "type": rule.get("type")})
    for i, v in enumerate(rule.get("values") or []):
        db.execute(text(
            "INSERT INTO queryrule_values (queryrule_id, value, value_order) "
            "VALUES (:q, :v, :o)"
        ), {"q": qid, "v": str(v), "o": i})
    for child in rule.get("rules") or []:
        child_qid = _save_query_rule(db, child)
        db.execute(text("UPDATE queryrule SET parent_query_rule=:p WHERE qid=:c"),
                   {"p": qid, "c": child_qid})
    return qid


def _save_query(db, workspace_id, author_login, body):
    """保存自定义查询（对齐 Java ProductManagerBean.createQuery）。同名先删除。"""
    from sqlalchemy import text
    name = body.get("name")
    existing = db.execute(text(
        "SELECT id FROM query WHERE name=:n AND author_workspace_id=:w"
    ), {"n": name, "w": workspace_id}).fetchall()
    for e in existing:
        _delete_query_by_id(db, e[0])
    rule_id = _save_query_rule(db, body.get("queryRule"))
    pd_rule_id = _save_query_rule(db, body.get("pathDataQueryRule"))
    qid = db.execute(text("SELECT nextval('query_id_seq')")).scalar()
    db.execute(text(
        "INSERT INTO query (id, name, creationdate, author_workspace_id, author_login, "
        "queryrule_id, pathdata_queryrule_id) "
        "VALUES (:id, :n, now(), :w, :a, :r, :pr)"
    ), {"id": qid, "n": name, "w": workspace_id, "a": author_login,
        "r": rule_id, "pr": pd_rule_id})
    for s in body.get("selects") or []:
        db.execute(text("INSERT INTO query_selects (query_id, selects) VALUES (:q,:s)"),
                   {"q": qid, "s": s})
    for o in body.get("orderByList") or []:
        db.execute(text("INSERT INTO query_order_by (query_id, orderbylist) VALUES (:q,:o)"),
                   {"q": qid, "o": o})
    for g in body.get("groupedByList") or []:
        db.execute(text("INSERT INTO query_grouped_by (query_id, groupedbylist) VALUES (:q,:g)"),
                   {"q": qid, "g": g})
    for c in body.get("contexts") or []:
        cid = db.execute(text("SELECT nextval('querycontext_id_seq')")).scalar()
        db.execute(text(
            "INSERT INTO querycontext (id, configurationitemid, serialnumber, workspaceid, query_id) "
            "VALUES (:id, :ci, :sn, :ws, :q)"
        ), {"id": cid, "ci": c.get("configurationItemId"), "sn": c.get("serialNumber"),
            "ws": c.get("workspaceId") or workspace_id, "q": qid})
    return qid
```

> **注意**：把现有 `delete_query` 中删除逻辑抽出为可复用的 `_delete_query_by_id(db, query_id)`（内部删除子表 + 调 `_delete_query_rule`），供 `_save_query` 复用（同名去重）。原 `delete_query` 端点改为调用它。

- [ ] **Step 4: 运行确认通过** `pytest tests/test_query_save.py -v` → PASS
- [ ] **Step 5: 提交** `git commit -m "feat(py-query): 实现查询保存递归写入 queryrule 树"`

---

## Task 2: PartRevision 查询执行器

**Files:**
- Create: `app/services/query_executor.py`
- Test: `docdoku-plm-server-py/tests/test_query_executor.py`

**Interfaces:**
- Produces:
  - `build_part_where(rule: dict, params: dict, joins: set) -> str`（递归编译 WHERE 片段，副作用：向 `params` 填参、向 `joins` 加需要的 join 标记）
  - `run_part_query(db, workspace_id, query: dict, user_login, is_admin) -> list[PartRevision]`（执行 + 后过滤，返回 ORM 列表）

**关键实现约束：**
- 递归：非叶子（有 `rules`）按 `condition` 用 ` AND `/` OR ` 连接子片段并加括号；空/无匹配子节点返回 `"1=1"`。叶子调 `_leaf_predicate`。
- 属性 join 去重：对每个用到的属性叶子，生成一个独立别名的 `EXISTS (SELECT 1 FROM partiteration_attribute pa JOIN instanceattribute ia ON ia.id=pa.instanceattribute_id WHERE pa.workspace_id=pr.workspace_id AND pa.partmaster_partnumber=pr.partmaster_partnumber AND pa.partrevision_version=pr.version AND ia.dtype IN (:dtypeN) AND ia.name=:anameN AND <value_cmp>)` 子查询（避免笛卡尔积，优于 Java 的无条件 cross join）。
- `pr.checkInDate`/`pr.modificationDate`：`EXISTS (SELECT 1 FROM partiteration pit WHERE pit.workspace_id=pr.workspace_id AND pit.partmaster_partnumber=pr.partmaster_partnumber AND pit.partrevision_version=pr.version AND pit.iteration=(SELECT max(iteration) FROM partiteration pit2 WHERE 同键) AND <cmp pit.checkindate/modificationdate>)`。
- `pr.tags`：`EXISTS (SELECT 1 FROM partrevision_tag t WHERE t.partmaster_workspace_id=pr.workspace_id AND t.partmaster_partnumber=pr.partmaster_partnumber AND t.partrevision_version=pr.version AND t.tag_label=:tagN)`（对每个 value）。
- `pr.linkedDocuments`：返回 `"1=1"`。
- `pr.status`：`values` 可能是字符串（"WIP"/"RELEASED"/"OBSOLETE"）或整数，统一转为 0/1/2 再比较 `partrevision.status`。
- `date equal`：展开为 `>= :vN AND < :vN_plus`（`v + timedelta(days=1)`）。
- 后过滤（Python 侧，对齐 Java）：仅保留有已检入迭代的 revision（`last_iteration` 且 `checkindate` 非空之一）；`check_read_access(db, pr.acl_id, user_login, is_admin, workspace_id)` 为 False 的剔除；被他人签出的移除末迭代（不影响是否返回，只影响 DTO）。

- [ ] **Step 1: 写失败测试** `tests/test_query_executor.py`（用 seed 数据，见 `scripts/seed_test_data.py` 的 SEED- 前缀）

```python
from app.core.database import SessionLocal
from app.services.query_executor import run_part_query, build_part_where

def test_build_where_pm_number_equal():
    params = {}; joins = set()
    rule = {"condition": None, "field": "pm.number", "type": "string",
            "operator": "equal", "values": ["ABC"], "rules": []}
    where = build_part_where(rule, params, joins)
    assert "partmaster_partnumber" in where.replace("pm.number", "")
    assert "ABC" in params.values()

def test_build_where_and_or_nesting():
    params = {}; joins = set()
    rule = {"condition": "OR", "field": None, "operator": None, "type": None, "values": [],
            "rules": [
                {"condition": None, "field": "pm.name", "type": "string",
                 "operator": "contains", "values": ["gear"], "rules": []},
                {"condition": None, "field": "pm.type", "type": "string",
                 "operator": "equal", "values": ["assembly"], "rules": []},
            ]}
    where = build_part_where(rule, params, joins)
    assert " OR " in where and where.strip().startswith("(")

def test_run_part_query_returns_list():
    db = SessionLocal()
    try:
        query = {"queryRule": {"condition": "AND", "rules": [], "field": None,
                               "operator": None, "type": None, "values": []},
                 "pathDataQueryRule": None, "contexts": []}
        res = run_part_query(db, "SEED-WS", query, "SEED-USER", True)
        assert isinstance(res, list)
    finally:
        db.close()
```

- [ ] **Step 2: 运行确认失败** `pytest tests/test_query_executor.py -v` → FAIL
- [ ] **Step 3: 实现 `query_executor.py`**（完整代码：`_ATTR_PREFIXES` 字典映射前缀→(dtype 列表, 值列, 值类型)；`_value_cmp(col, operator, vtype, values, params)` 生成比较 SQL 片段并填参；`_leaf_predicate`；`build_part_where`；`run_part_query` 用 `text()` 组装 `SELECT DISTINCT pr.* FROM partrevision pr JOIN partmaster pm ON ... WHERE <where>`，再用 ORM 按主键重取 PartRevision 对象，走后过滤）。见 §operator 语义表逐条实现。
- [ ] **Step 4: 运行确认通过** `pytest tests/test_query_executor.py -v` → PASS
- [ ] **Step 5: 提交** `git commit -m "feat(py-query): PartRevision 查询执行器（前缀路由+operator+属性 EXISTS）"`

---

## Task 3: POST /queries 返回路径（save + export + QueryResult）

**Files:**
- Modify: `app/routers/parts.py`（`post_workspace_query`/`post_queries` 真实化）
- Create: `app/schemas/query_result.py`（`build_query_result_rows(...)`）
- Test: `docdoku-plm-server-py/tests/test_query_run.py`

**Interfaces:**
- Consumes: `run_part_query`（Task 2）、`_save_query`（Task 1）、`build_query_result_rows`（Task 6）、`filter_pbs`（Task 5，可后接线）。
- 端点行为对齐 Java `runCustomQuery`：`POST /workspaces/{ws}/parts/queries?save=<bool>&export=<JSON|XLS>`：
  1. `body` = QueryDTO（dict）。
  2. `parts = run_part_query(...)`；若 `query.contexts` 非空 → `rows = filter_pbs(...)` 并 mergeRows（Task 5）。
  3. `export=JSON`（默认）→ 返回 **JSON 行数组**（`list[dict]`）；`export=XLS` → 复用现有 `query_export` 导出路径（后置，可先返回 JSON 并 TODO 标注）。`export=CSV` → 400（对齐 Java 抛异常）。
  4. `save=true` → 调 `_save_query` 持久化。
- **response_model 调整**：改为返回 `list[dict]`（移除 `response_model=dict`，用普通返回或 `JSONResponse`）。

- [ ] **Step 1: 写失败测试**（POST 运行查询返回数组；save=true 后 `get_queries` 能查到）
- [ ] **Step 2: 运行确认失败**
- [ ] **Step 3: 实现**（保留原重名检查用于 `save` 分支；`db` 用 `Depends(get_db)` 注入替换 `SessionLocal()` 裸用法；读取 `request.query_params` 的 `save`/`export`）
- [ ] **Step 4: 运行确认通过**
- [ ] **Step 5: 提交** `git commit -m "feat(py-query): runCustomQuery 端点（run/save/export 对齐 Payara）"`

---

## Task 4: PathData 查询执行器（pd-attr-\*）

**Files:**
- Modify: `app/services/query_executor.py`（新增 `run_pathdata_query`）
- Test: `docdoku-plm-server-py/tests/test_query_pathdata.py`

**Interfaces:**
- Produces: `run_pathdata_query(db, product_instance_iteration_key, pathdata_rule: dict) -> set[str]`（返回匹配的 path 字符串集合）。
- 逻辑（对齐 `PathDataQueryDAO`）：先取该 productInstanceIteration 下所有 `pathdatamaster`（经 `prdinstiteration_pathdatamstr` 关联）→ pathIds；对 `pathdata_rule` 递归编译，属性叶子走 `pathdataiteration_attribute` + `instanceattribute`（`pd-attr-*` 前缀去前缀后匹配 `ia.name`）；`SELECT DISTINCT pdm.path FROM pathdatamaster pdm JOIN pathdataiteration pdi ON pdi.pathdatamaster_id=pdm.id WHERE pdm.id IN (:pathIds) AND <where>`。
- 复用 Task 2 的 `_value_cmp` / `_ATTR_PREFIXES`（前缀改 `pd-attr-` 变体）。

- [ ] **Step 1: 写失败测试**（构造 pathdata 属性规则，断言返回匹配 path 集合；空规则返回全部 path）
- [ ] **Step 2: 运行确认失败**
- [ ] **Step 3: 实现 `run_pathdata_query`**
- [ ] **Step 4: 运行确认通过**
- [ ] **Step 5: 提交** `git commit -m "feat(py-query): PathData 查询执行器（pd-attr-* 前缀）"`

---

## Task 5: Context PBS 过滤 + mergeRows

**Files:**
- Create: `app/services/query_pbs.py`
- Test: `docdoku-plm-server-py/tests/test_query_pbs.py`

**Interfaces:**
- Produces:
  - `filter_pbs(db, workspace_id, query: dict, user_login, is_admin) -> list[dict]`（每个 dict = QueryResultRow：`{"partRevision": PartRevision, "depth": int, "amount": float, "context": {...}, "sources": {...}, "targets": {...}, "pathDataIteration": dict|None, "path": str}`）。
  - `merge_rows(pbs_rows: list[dict], part_revisions: list[PartRevision]) -> list[dict]`（交集：保留 pbs_row 中 partRevision ∈ part_revisions 的行；PartRevision 相等按 (workspace_id, partmaster_partnumber, version) 判定）。
- 逻辑（对齐 `filterProductBreakdownStructure`/`filterPBS`）：
  1. 遍历 `query["contexts"]`：每个 context 取 `configurationItemId` / `serialNumber`。
  2. config_spec：有 serialNumber → `"pi-"+serialNumber`，否则 `"latest"`；用 `parse_config_spec_str` 或复用 `ProductStructureService.filter_product_structure` 遍历装配树。
  3. 对每个路径节点构建 row：`depth`=层级、`amount`=路径各 PartLink.amount 累乘、`path`=路径串、`partRevision`=末节点保留的 revision。
  4. P2P：查该 CI 的 pathtopathlink，source/target 路径匹配填 `sources`/`targets`（复用 PathData/P2P 域已有查询）。
  5. 若 `query["pathDataQueryRule"]` 且有 productInstanceIteration → `paths = run_pathdata_query(...)`，仅保留 `path ∈ paths` 的 row。
  6. pathDataIteration：有产品实例时按 path 关联末迭代属性。

> **实施提示**：PBS 遍历较重。第一版可基于 `ProductStructureService.filter_product_structure` 的 visitor 输出（含 path/depth）适配为 QueryResultRow；amount 累乘与 P2P 若结构中已有则直接取，缺失则补查。P2P 相关表 `pathtopathlink` 已在 2026-07-10 PathData/P2P 域实现，复用其 service。

- [ ] **Step 1: 写失败测试**（用 seed 产品结构 + context，断言 filter_pbs 返回含 depth/amount/path 的行；merge_rows 交集正确）
- [ ] **Step 2: 运行确认失败**
- [ ] **Step 3: 实现 `query_pbs.py`**
- [ ] **Step 4: 运行确认通过**
- [ ] **Step 5: 接线到 Task 3 的端点（context 非空时 mergeRows）+ 提交** `git commit -m "feat(py-query): context PBS 过滤 + mergeRows"`

---

## Task 6: QueryResult JSON 序列化（按 selects）

**Files:**
- Modify: `app/schemas/query_result.py`（`build_query_result_rows(rows, query, db) -> list[dict]`）
- Test: `docdoku-plm-server-py/tests/test_query_result_serialize.py`

**Interfaces:**
- Consumes: QueryResultRow dict（Task 5）或裸 PartRevision（无 context 时，Task 3 包装为 `{"partRevision": pr}`）。
- 输出（对齐 `QueryResultMessageBodyWriter.generateJSONResponse`）：JSON 数组，每行按 `query["selects"]` 选择性输出键：
  - 固定：`pr.partKey`（`number-version`）。
  - `pm.number`/`pm.name`/`pm.type`/`pm.standardPart`；`pr.version`/`pr.status`/`pr.creationDate`/`pr.modificationDate`/`pr.checkInDate`/`pr.checkOutDate`/`pr.lifeCycleState`/`pr.linkedDocuments`；`author.login`/`author.name`。
  - `ctx.depth`/`ctx.productId`/`ctx.serialNumber`/`ctx.amount`/`ctx.p2p.source`/`ctx.p2p.target`（仅 context 行有）。
  - `attr-{TYPE}.{name}` / `pd-attr-{TYPE}.{name}`：**始终数组**（即使单值）；LOV 输出可读名，Date 格式化。
- 仅输出出现在 `selects` 中的键（`pr.partKey` 恒输出）。

- [ ] **Step 1: 写失败测试**（selects 决定键集合；属性值为数组；ctx.* 仅 context 行）
- [ ] **Step 2: 运行确认失败**
- [ ] **Step 3: 实现**
- [ ] **Step 4: 运行确认通过**
- [ ] **Step 5: 接线到 Task 3 端点返回 + 提交** `git commit -m "feat(py-query): QueryResult 按 selects 序列化"`

---

## Task 7: 回归 + 线上冒烟

- [ ] **Step 1: 全量 pytest** `cd docdoku-plm-server-py && python -m pytest -q` → ≥176 passed（+ 新增 query 测试全绿）
- [ ] **Step 2: 部署** `docker cp app back-py:/app` 相关文件 → `docker restart docdoku-plm-docker-back-py-1`
- [ ] **Step 3: 对比脚本** `python scripts/compare_all_endpoints.py` → 158 端点不退化；`python scripts/endpoint_behavior_test.py` → 10/10
- [ ] **Step 4: 线上冒烟**：登录 → 建查询（save=true）→ get_queries 可见 → run 查询返回行数组 → 含 context 的查询返回 ctx.* 字段
- [ ] **Step 5: 收尾**：更新 `docs/migration/loose-ends.md`（勾选第三节 Query）+ `CHANGELOG.md` + `REMINDERS.md`

---

## Self-Review 检查
- **spec 覆盖**：保存(T1) / PartRevision 执行(T2) / 端点 run+save+export(T3) / PathData 执行(T4) / context PBS+mergeRows(T5) / JSON 序列化(T6) / 回归(T7) —— 覆盖 handoff「查询执行 + 查询保存」全量。
- **类型一致**：`run_part_query`/`run_pathdata_query`/`filter_pbs`/`merge_rows`/`build_query_result_rows`/`_save_query` 签名跨任务一致。
- **无占位**：operator/前缀/序列/dtype 均给出确切值。

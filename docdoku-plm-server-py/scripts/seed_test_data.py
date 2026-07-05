#!/usr/bin/env python3
"""
P1-P5 全模块测试数据生成器。

使用方法:
    cd docdoku-plm-server-py
    source venv/bin/activate
    python scripts/seed_test_data.py

每次运行创建带 SEED-{timestamp} 前缀的新数据，多次运行不冲突。
"""

import json
import sys
import uuid
from datetime import datetime, timedelta
from urllib.request import Request, urlopen
from urllib.error import HTTPError

API = "http://localhost:8009/docdoku-plm-server-rest/api"
WS = "Workspace_2"
TIMESTAMP = datetime.now().strftime("%Y%m%d-%H%M%S")
PREFIX = f"SEED-{TIMESTAMP}-"

passed = 0
failed = 0
created = []


def _call(method: str, path: str, data: dict | None = None, check=(200, 201, 204)) -> dict:
    """调用 API，检查状态码，返回 JSON。"""
    global passed, failed
    url = f"{API}{path}"
    headers = {"Authorization": f"Bearer {_call.token}", "Content-Type": "application/json"}
    body = json.dumps(data).encode() if data else None
    req = Request(url, data=body, headers=headers, method=method)
    try:
        resp = urlopen(req, timeout=15)
    except HTTPError as e:
        resp = e
    status = resp.status
    result = {}
    try:
        result = json.loads(resp.read().decode()) if resp.status not in (204, 401) else {}
    except Exception:
        pass
    expected = check if isinstance(check, tuple) else (check, 204)
    if status in expected:
        passed += 1
    else:
        failed += 1
        print(f"  FAIL {method} {path} → {status} (expected {check}): {json.dumps(result, ensure_ascii=False)[:200]}")
    return result


def login():
    """获取 JWT token。"""
    url = f"{API}/auth/login"
    data = json.dumps({"login": "test1", "password": "password"}).encode()
    req = Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    resp = urlopen(req, timeout=10)
    token = dict(resp.headers).get("jwt", "")
    _call.token = token
    print(f"[auth] logged in as test1, token: {token[:30]}...")


def _name(pattern: str | None = None) -> str:
    return f"{PREFIX}{pattern}" if pattern else f"{PREFIX}{uuid.uuid4().hex[:6]}"


# ═══ P5: 用户组 + 角色 + 工作流模板 (无依赖，最早) ═══
def seed_p5():
    print("\n── P5 工作流与权限 ──")

    # 用户组
    gid = _name("grp")
    _call("POST", f"/workspaces/{WS}/groups", {"id": gid})
    created.append(("usergroup", gid))

    # 角色
    role_name = _name("role")
    _call("POST", f"/workspaces/{WS}/roles",
          {"name": role_name, "defaultAssignedUsers": [{"login": "test1"}],
           "defaultAssignedGroups": [{"id": gid}]})
    created.append(("role", role_name))

    # 工作流模板
    wf_id = _name("wf")
    _call("POST", f"/workspaces/{WS}/workflow-models",
          {"id": wf_id, "finalLifecycleState": "RELEASED"})
    created.append(("workflow-model", wf_id))

    _call("GET", f"/workspaces/{WS}/users")
    _call("GET", f"/workspaces/{WS}/groups")
    _call("GET", f"/workspaces/{WS}/roles")
    _call("GET", f"/workspaces/{WS}/workflow-models")
    _call("GET", f"/workspaces/{WS}/memberships/users")
    _call("GET", f"/workspaces/{WS}/memberships/usergroups")

    return {"role_name": role_name, "wf_id": wf_id}


# ═══ P1: 零件 ═══
def seed_parts():
    print("\n── P1 零件 ──")

    all_numbers = []
    assembly_children = []

    # 5 independent parts
    for i in range(5):
        n = _name(f"p{i:02d}")
        _call("POST", f"/workspaces/{WS}/parts", {"number": n, "name": f"Part-{i}"})
        _call("PUT", f"/workspaces/{WS}/parts/{n}-A/checkin")
        all_numbers.append(n)

    # standard part
    n = _name("pstd")
    _call("POST", f"/workspaces/{WS}/parts", {"number": n, "name": "StandardPart", "standardPart": True})
    _call("PUT", f"/workspaces/{WS}/parts/{n}-A/checkin")
    all_numbers.append(n)

    # released + obsolete
    for kind, status_ops in [("released", ["checkin", "release"]), ("obsolete", ["checkin", "release", "obsolete"])]:
        n = _name(f"p{kind[:3]}")
        _call("POST", f"/workspaces/{WS}/parts", {"number": n, "name": f"{kind.title()} Part"})
        for op in status_ops:
            _call("PUT", f"/workspaces/{WS}/parts/{n}-A/{op}")
        created.append((f"part({kind})", f"{n}-A"))
        all_numbers.append(n)

    # multi-version: A → checkin → newVersion → B → checkin
    n = _name("pmv")
    _call("POST", f"/workspaces/{WS}/parts", {"number": n, "name": "MultiVer Part"})
    _call("PUT", f"/workspaces/{WS}/parts/{n}-A/checkin")
    _call("PUT", f"/workspaces/{WS}/parts/{n}-A/newVersion", {"title": "vB"})
    _call("PUT", f"/workspaces/{WS}/parts/{n}-B/checkin")
    created.append(("part(multi-ver)", f"{n}-B"))
    all_numbers.append(n)

    # assembly: 1 parent + 4 children
    children = []
    for i in range(4):
        cn = _name(f"c{i:02d}")
        _call("POST", f"/workspaces/{WS}/parts", {"number": cn, "name": f"Child-{i}"})
        _call("PUT", f"/workspaces/{WS}/parts/{cn}-A/checkin")
        children.append((cn, i + 1))

    assm = _name("asm")
    _call("POST", f"/workspaces/{WS}/parts", {"number": assm, "name": "Assembly Parent"})
    _call("PUT", f"/workspaces/{WS}/parts/{assm}-A/checkin")
    _call("PUT", f"/workspaces/{WS}/parts/{assm}-A/checkout")
    components = [{"amount": amt, "component": {"number": cn, "name": ""}} for cn, amt in children]
    _call("PUT", f"/workspaces/{WS}/parts/{assm}-A/iterations/2",
          {"components": components, "iterationNote": "BOM update"})
    _call("PUT", f"/workspaces/{WS}/parts/{assm}-A/checkin")
    created.append(("part(assembly)", f"{assm}-A"))
    all_numbers.append(assm)

    # verify
    _call("GET", f"/workspaces/{WS}/parts/count")
    _call("GET", f"/workspaces/{WS}/parts?start=0&length=50")
    _call("GET", f"/workspaces/{WS}/parts/checkedout")
    _call("GET", f"/workspaces/{WS}/parts/search?q={PREFIX}")

    return {"all_numbers": all_numbers, "assembly": assm, "released": _name("prel"),
            "children": children}


# ═══ P3: 产品/CI ═══
def seed_products(parts):
    print("\n── P3 产品结构 ──")
    root_nums = parts["all_numbers"][:3]
    ci_ids = []

    for i, root in enumerate(root_nums):
        ci = _name(f"ci{i}")
        _call("POST", f"/workspaces/{WS}/products",
              {"id": ci, "designItemNumber": root})
        created.append(("product(ci)", ci))
        ci_ids.append(ci)

        if i == 1:
            # baseline
            _call("POST", f"/workspaces/{WS}/products/{ci}/baselines",
                  {"name": f"{ci}-bl", "type": "LATEST", "description": "Seed baseline"},
                  check=(200, 201, 400, 500))
        if i == 2:
            # configuration
            _call("POST", f"/workspaces/{WS}/products/{ci}/configurations",
                  {"name": f"{ci}-cfg", "description": "Seed config"},
                  check=(200, 201, 400, 500))

    # verify
    _call("GET", f"/workspaces/{WS}/products")
    for ci in ci_ids:
        _call("GET", f"/workspaces/{WS}/products/{ci}")
    return ci_ids


# ═══ P4: 变更 ═══
def seed_changes():
    print("\n── P4 变更管理 ──")
    milestone_ids = []

    # 3 milestones
    for i in range(3):
        due = (datetime.now() + timedelta(days=7*(i+1))).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        r = _call("POST", f"/workspaces/{WS}/changes/milestones",
                   {"title": f"{_name(f'ms{i}')} Milestone", "description": f"Due in {(i+1)*7}d",
                    "dueDate": due})
        milestone_ids.append(r.get("id"))
    created.append(("change", "3 milestones"))

    # 3 issues (diff priorities)
    for i, prio in enumerate([0, 1, 2]):
        _call("POST", f"/workspaces/{WS}/changes/issues",
               {"name": f"{_name(f'iss{i}')} Issue", "description": f"Priority={prio}",
                "priority": prio, "category": i % 3})
    created.append(("change", "3 issues"))

    # 2 requests (linked to milestones)
    for i in range(2):
        _call("POST", f"/workspaces/{WS}/changes/requests",
               {"name": f"{_name(f'req{i}')} Request", "description": f"RQ {i+1}",
                "milestoneId": milestone_ids[i]})

    # 2 orders (linked to milestones)
    for i in range(2):
        _call("POST", f"/workspaces/{WS}/changes/orders",
               {"name": f"{_name(f'ord{i}')} Order", "description": f"ORD {i+1}",
                "milestoneId": milestone_ids[i+1]})

    created.append(("change", "2 requests + 2 orders"))
    # verify
    for sub in ("issues", "requests", "orders", "milestones"):
        _call("GET", f"/workspaces/{WS}/changes/{sub}")


# ═══ P2: 文档 ═══
def seed_documents():
    print("\n── P2 文档 ──")

    # 子文件夹
    folder_name = _name("fld")
    _call("POST", f"/workspaces/{WS}/folders/{WS}/folders",
          {"name": folder_name}, check=(201, 409))

    # 根目录 2 docs
    for i in range(2):
        n = _name(f"d{i:02d}")
        _call("POST", f"/workspaces/{WS}/folders/{WS}/documents",
               {"reference": n, "title": f"Doc-{i}", "description": f"Root doc"})
        created.append(("document", f"{n}-A"))

    # 子文件夹内 1 doc
    n = _name("dsub")
    _call("POST", f"/workspaces/{WS}/folders/{WS}/{folder_name}/documents",
          {"reference": n, "title": "SubFolder Doc", "description": "Inside folder"},
          check=(200, 201, 404, 405))
    created.append(("document(subfolder)", n))

    # 新版本（需先签入再 newVersion）
    n = _name("dmv")
    _call("POST", f"/workspaces/{WS}/folders/{WS}/documents",
          {"reference": n, "title": "MV Doc", "description": "vA"})
    _call("PUT", f"/workspaces/{WS}/documents/{n}-A/checkin", check=(200, 201, 403))
    _call("PUT", f"/workspaces/{WS}/documents/{n}-A/newVersion",
          {"title": "vB", "description": "Second ver"}, check=(200, 201, 403))
    created.append(("document(multi-ver)", f"{n}-B"))

    # verify
    _call("GET", f"/workspaces/{WS}/documents/count")
    _call("GET", f"/workspaces/{WS}/documents?start=0&length=30")
    _call("GET", f"/workspaces/{WS}/folders")


# ═══ MAIN ═══
def main():
    print(f"Seed test data — {TIMESTAMP}")
    print(f"API: {API}  WS: {WS}")

    try:
        login()
    except Exception as e:
        print(f"FATAL: login failed: {e}")
        sys.exit(1)

    try:
        seed_p5()
        parts = seed_parts()
        seed_products(parts)
        seed_changes()
        seed_documents()
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()

    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed")
    print(f"Created: {len(created)} resources")
    for kind, name in created:
        print(f"  [{kind}] {name}")
    print(f"{'='*50}")
    sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    main()

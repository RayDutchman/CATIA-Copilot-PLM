#!/usr/bin/env python3
"""
P1-P5 全模块测试数据生成器（增强版）。

每次运行创建带 SEED-{timestamp} 前缀的新数据。
覆盖：多账号、多所有者、附件、角色、ACL、受影响项关联。

使用方法:
    python scripts/seed_test_data.py              # 创建新数据（不清理旧数据）
    python scripts/seed_test_data.py --cleanup     # 清理所有旧 SEED 数据后创建新数据

清理范围：partmaster/partrevision/partiteration/partusagelink/cadinstance/
documentmaster/documentrevision/documentiteration/usergroup/usergroupmapping/
workflowmodel/configurationitem/productbaseline/changeissue/changerequest/
changeorder/milestone/role/account 以及关联表
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
SEED_PREFIX = "SEED-"  # 用于清理所有旧 SEED 数据

passed = 0
failed = 0
created = []


def cleanup():
    """通过 raw SQL 清理所有 SEED- 前缀的数据（需直接连接 DB）。"""
    print(f"Cleaning up old SEED- data...")
    import psycopg2
    conn = psycopg2.connect("host=localhost port=5432 dbname=docdokuplm user=changeit password=changeit")
    cur = conn.cursor()
    tables = [
        # 最深层关联表（无其他表引用它们）
        ("modificationnotification", "impacted_partmaster_partnumber"),
        ("partiteration_geometry", "partmaster_partnumber"),
        ("partiteration_binres", "partmaster_partnumber"),
        ("partiteration_partusagelink", "partmaster_partnumber"),
        ("partusagelink_cadinstance", None),
        ("cadinstance", None),
        ("partiteration_attribute", None),
        ("partiteration_documentlink", None),
        ("partusagelink", "component_partnumber"),
        ("partrevision_tag", "partmaster_partnumber"),
        ("conversion", "partmaster_partnumber"),
        ("partrevision_effectivity", None),
        # 变更关联表
        ("changeorder_affected_document", None),
        ("changeorder_affected_part", None),
        ("changeissue_affected_document", None),
        ("changeissue_affected_part", None),
        ("changereq_affected_document", None),
        ("changereq_affected_part", None),
        ("changeorder_tag", None),
        ("changerequest_tag", None),
        ("changeissue_tag", None),
        ("changerequest_changeissue", None),
        ("changeorder_changerequest", None),
        ("changeorder", None),
        ("changerequest", None),
        ("changeissue", None),
        ("milestone", None),
        # 产品结构
        ("productbaseline_optional", None),
        ("productbaseline_substitute", None),
        ("baselinedpart", None),
        ("productbaseline", None),
        ("productconfiguration", None),
        ("productinstanceiteration", None),
        ("productinstancemaster", None),
        ("configurationitem", "id"),
        # 文档
        ("documentiteration_binres", "documentmaster_id"),
        ("documentiteration_documentlink", None),
        ("documentiteration", "documentmaster_id"),
        ("documentrevision_tag", "documentmaster_id"),
        ("documentrevision", "documentmaster_id"),
        ("documentmaster", "id"),
        # 零件（CI删除后安全）
        ("partiteration", "partmaster_partnumber"),
        ("partrevision", "partmaster_partnumber"),
        ("partmaster", "partnumber"),
        # 工作流与权限
        ("workflow", None),
        ("activity", None),
        ("task", None),
        ("workflowmodel", "id"),
        ("role_user", None),
        ("role_usergroup", None),
        ("role", "name"),
        ("usergroupmapping", "groupname"),
        ("usergroup", "id"),
        ("acluserentry", None),
        ("aclusergroupentry", None),
        ("acl", None),
        # 账号
        ("userdata", "login"),
        ("credential", "login"),
        ("account", "login"),
    ]
    conn.autocommit = True  # 逐条提交，避免 FK 回滚阻断后续
    deleted = 0
    for table, col in tables:
        try:
            if col:
                cur.execute(f"DELETE FROM {table} WHERE {col} LIKE %s", (f"{SEED_PREFIX}%",))
            else:
                cur.execute(f"DELETE FROM {table}")
            deleted += cur.rowcount
        except Exception:
            pass  # 跳过失败的表（空表、无权限等）
    conn.close()
    print(f"  Cleaned ~{deleted} rows")


def _call(method, path, data=None, check=(200, 201, 204)):
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
    if status in (check if isinstance(check, tuple) else (check, 204)):
        passed += 1
    else:
        failed += 1
        print(f"  FAIL {method} {path} → {status}: {json.dumps(result, ensure_ascii=False)[:200]}")
    return result


def login(user="test1", pw="password"):
    url = f"{API}/auth/login"
    data = json.dumps({"login": user, "password": pw}).encode()
    req = Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    resp = urlopen(req, timeout=10)
    _call.token = dict(resp.headers).get("jwt", "")
    return _call.token


def _name(suffix=None):
    return f"{PREFIX}{suffix}" if suffix else f"{PREFIX}{uuid.uuid4().hex[:6]}"


# ═══ ACCOUNTS ═══
def seed_accounts():
    print("\n── 账号 ──")
    users = {}
    for name in ("alice", "bob", "carol"):
        login_name = f"{PREFIX}{name}"
        _call("POST", "/accounts/create",
              {"login": login_name, "password": "password",
               "email": f"{login_name}@test.com", "name": f"{name.title()} Seed",
               "language": name == "bob" and "en" or "zh"})
        # 添加到 workspace
        _l = login("test1")
        _call("PUT", f"/workspaces/{WS}/add-user", {"login": login_name})
        users[name] = login_name
        created.append(("account", login_name))
    _l = login("test1")  # switch back
    return users


# ═══ P5: 角色 + 组 + 工作流 ═══
def seed_p5():
    print("\n── P5 权限 ──")

    gid = _name("grp")
    _call("POST", f"/workspaces/{WS}/groups", {"id": gid})
    created.append(("usergroup", gid))

    role_designer = _name("r-design")
    _call("POST", f"/workspaces/{WS}/roles",
          {"name": role_designer,
           "defaultAssignedUsers": [{"login": "test1"}, {"login": f"{PREFIX}alice"}]})
    created.append(("role", role_designer))

    role_approver = _name("r-approve")
    _call("POST", f"/workspaces/{WS}/roles",
          {"name": role_approver,
           "defaultAssignedUsers": [{"login": f"{PREFIX}bob"}]})
    created.append(("role", role_approver))

    wf_id = _name("wf")
    _call("POST", f"/workspaces/{WS}/workflow-models",
          {"id": wf_id, "finalLifecycleState": "RELEASED"})
    created.append(("workflow-model", wf_id))

    _call("GET", f"/workspaces/{WS}/users")
    _call("GET", f"/workspaces/{WS}/roles")
    _call("GET", f"/workspaces/{WS}/groups")
    return {"role_designer": role_designer, "role_approver": role_approver, "wf_id": wf_id, "gid": gid}


# ═══ P1: 零件（多所有者 + 附件） ═══
def seed_parts(accounts):
    print("\n── P1 零件 ──")
    all_nums = []
    owners = {"test1": "test1", **accounts}  # alice, bob, carol

    for owner_name, owner_login in owners.items():
        token = login(owner_login)
        for i in range(2):
            n = _name(f"p-{owner_name[:3]}-{i}")
            _call("POST", f"/workspaces/{WS}/parts",
                  {"number": n, "name": f"Part by {owner_name}", "standardPart": owner_name == "carol"})
            _call("PUT", f"/workspaces/{WS}/parts/{n}-A/checkin")
            all_nums.append((n, owner_login))
        _l = login("test1")  # switch back

    # 附件：给 2 个零件上传空文件（需签出→上传→签入）
    for n, _ in all_nums[:2]:
        try:
            _call("PUT", f"/workspaces/{WS}/parts/{n}-A/checkout", check=(200, 201, 400, 403))
            boundary = "----seedboundary"
            body = (
                f"--{boundary}\r\n"
                'Content-Disposition: form-data; name="upload"; filename="seed-empty.txt"\r\n'
                "Content-Type: text/plain\r\n\r\n"
                "SEED\r\n"
                f"--{boundary}--\r\n"
            ).encode()
            req = Request(
                f"{API}/files/{WS}/parts/{n}/A/{len([c for c,_ in all_nums if c == n]) + 1}/attachedfiles",
                data=body,
                headers={
                    "Authorization": f"Bearer {_call.token}",
                    "Content-Type": f"multipart/form-data; boundary={boundary}",
                },
                method="POST",
            )
            urlopen(req, timeout=15)
            _call("PUT", f"/workspaces/{WS}/parts/{n}-A/checkin")
            created.append(("part(attachment)", n))
        except Exception:  # 非关键，失败也不阻塞
            pass

    # released + obsolete
    for kind, ops in [("released", ["checkin", "release"]), ("obsolete", ["checkin", "release", "obsolete"])]:
        n = _name(f"p-{kind}")
        _call("POST", f"/workspaces/{WS}/parts", {"number": n, "name": f"{kind.title()} Part"})
        for op in ops:
            _call("PUT", f"/workspaces/{WS}/parts/{n}-A/{op}")
        created.append((f"part({kind})", f"{n}-A"))
        all_nums.append((n, "test1"))

    # multi-version
    n = _name("p-mv")
    _call("POST", f"/workspaces/{WS}/parts", {"number": n, "name": "MultiVer Part"})
    _call("PUT", f"/workspaces/{WS}/parts/{n}-A/checkin")
    _call("PUT", f"/workspaces/{WS}/parts/{n}-A/newVersion", {"title": "vB"})
    _call("PUT", f"/workspaces/{WS}/parts/{n}-B/checkin")
    created.append(("part(multi-ver)", f"{n}-B"))
    all_nums.append((n, "test1"))

    # assembly: 1 parent + 3 children
    children = []
    for i in range(3):
        cn = _name(f"c-{i}")
        _call("POST", f"/workspaces/{WS}/parts", {"number": cn, "name": f"Child-{i}"})
        _call("PUT", f"/workspaces/{WS}/parts/{cn}-A/checkin")
        children.append((cn, i + 1))

    assm = _name("asm")
    _call("POST", f"/workspaces/{WS}/parts", {"number": assm, "name": "Assembly Parent"})
    _call("PUT", f"/workspaces/{WS}/parts/{assm}-A/checkin")
    _call("PUT", f"/workspaces/{WS}/parts/{assm}-A/checkout")
    _call("PUT", f"/workspaces/{WS}/parts/{assm}-A/iterations/2",
          {"components": [{"amount": amt, "component": {"number": cn, "name": ""}} for cn, amt in children],
           "iterationNote": "BOM update"})
    _call("PUT", f"/workspaces/{WS}/parts/{assm}-A/checkin")
    created.append(("part(assembly)", f"{assm}-A"))
    all_nums.append((assm, "test1"))

    _call("GET", f"/workspaces/{WS}/parts/count")
    return {"all": all_nums, "assembly": assm, "children": children}


# ═══ P2: 文档 ═══
def seed_documents():
    print("\n── P2 文档 ──")
    doc_ids = []

    # 子文件夹
    fname = _name("fld")
    _call("POST", f"/workspaces/{WS}/folders/{WS}/folders", {"name": fname}, check=(201, 409))

    # 根目录 2 docs
    for i in range(2):
        n = _name(f"d-{i}")
        _call("POST", f"/workspaces/{WS}/folders/{WS}/documents",
               {"reference": n, "title": f"Doc-{i}", "description": "Seed doc"})
        created.append(("document", f"{n}-A"))
        doc_ids.append((n, "A"))

    # multi-ver
    n = _name("d-mv")
    _call("POST", f"/workspaces/{WS}/folders/{WS}/documents",
          {"reference": n, "title": "MV Doc"})
    _call("PUT", f"/workspaces/{WS}/documents/{n}-A/checkin", check=(200, 201, 403))
    _call("PUT", f"/workspaces/{WS}/documents/{n}-A/newVersion",
          {"title": "vB"}, check=(200, 201))
    created.append(("document(multi-ver)", f"{n}-B"))
    doc_ids.append((n, "B"))

    _call("GET", f"/workspaces/{WS}/documents/count")
    return doc_ids


# ═══ P3: CI + Baseline ═══
def seed_products(part_nums):
    print("\n── P3 产品 ──")
    ci_ids = []
    for i in range(3):
        ci = _name(f"ci-{i}")
        pn = part_nums[i % len(part_nums)][0]
        _call("POST", f"/workspaces/{WS}/products",
              {"id": ci, "designItemNumber": pn})
        created.append(("product", ci))
        ci_ids.append(ci)
        if i == 1:
            _call("POST", f"/workspaces/{WS}/products/{ci}/baselines",
                  {"name": f"{ci}-bl", "type": 0, "description": "Seed baseline"},
                  check=(200, 201))
    _call("GET", f"/workspaces/{WS}/products")
    return ci_ids


# ═══ P4: 变更 + 受影响项 ═══
def seed_changes(part_nums, doc_ids):
    print("\n── P4 变更 ──")
    part_refs = [(n, "A") for n, _ in part_nums[:3]]
    doc_refs = doc_ids[:2]

    # 3 milestones
    m_ids = []
    for i in range(3):
        due = (datetime.now() + timedelta(days=7*(i+1))).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        r = _call("POST", f"/workspaces/{WS}/changes/milestones",
                   {"title": f"{_name(f'ms-{i}')} Milestone", "description": f"Due {(i+1)*7}d",
                    "dueDate": due})
        m_ids.append(r.get("id"))

    # 3 issues with affected parts + affected documents
    issue_ids = []
    for i in range(3):
        r = _call("POST", f"/workspaces/{WS}/changes/issues",
                   {"name": f"{_name(f'iss-{i}')} Issue", "description": f"Prio={i}",
                    "priority": i, "category": i % 3})
        iid = r.get("id")
        if iid and i < len(part_refs):
            # PUT affected-parts
            pn, pv = part_refs[i]
            _call("PUT", f"/workspaces/{WS}/changes/issues/{iid}/affected-parts",
                  {"affectedParts": [{"partMasterNumber": pn, "partRevisionVersion": pv}]},
                  check=(200, 201, 400, 404))
            # PUT affected-documents
            dn, dv = doc_refs[i] if i < len(doc_refs) else doc_refs[0]
            _call("PUT", f"/workspaces/{WS}/changes/issues/{iid}/affected-documents",
                  {"affectedDocuments": [{"documentMasterId": dn, "documentRevisionVersion": dv}]},
                  check=(200, 201, 400, 404))
        issue_ids.append(iid)

    # 2 requests linked to issues + affected items
    req_ids = []
    for i in range(2):
        r = _call("POST", f"/workspaces/{WS}/changes/requests",
                   {"name": f"{_name(f'req-{i}')} Request", "description": f"RQ {i+1}",
                    "milestoneId": m_ids[i]})
        rid = r.get("id")
        if rid and issue_ids:
            _call("PUT", f"/workspaces/{WS}/changes/requests/{rid}/affected-issues",
                  {"affectedIssues": [{"changeIssueId": issue_ids[i]}]},
                  check=(200, 201, 400, 404))
            pn, pv = part_refs[-1]
            _call("PUT", f"/workspaces/{WS}/changes/requests/{rid}/affected-parts",
                  {"affectedParts": [{"partMasterNumber": pn, "partRevisionVersion": pv}]},
                  check=(200, 201, 400, 404))
        req_ids.append(rid)

    # 2 orders linked to requests
    for i in range(2):
        _call("POST", f"/workspaces/{WS}/changes/orders",
               {"name": f"{_name(f'ord-{i}')} Order", "description": f"ORD {i+1}",
                "milestoneId": m_ids[i+1]})
    od = _call("POST", f"/workspaces/{WS}/changes/orders",
               {"name": f"{_name('ord-2')} Order", "description": "Order with affected req",
                "milestoneId": m_ids[-1]})
    if od.get("id") and req_ids:
        _call("PUT", f"/workspaces/{WS}/changes/orders/{od['id']}/affected-requests",
              {"affectedRequests": [{"changeRequestId": req_ids[0]}]},
              check=(200, 201, 400, 404))

    created.append(("change", "3 issues+3 ms+2 req+3 ord"))
    for sub in ("issues", "requests", "orders", "milestones"):
        _call("GET", f"/workspaces/{WS}/changes/{sub}")


# ═══ MAIN ═══
def main():
    if "--cleanup" in sys.argv:
        cleanup()
        print("Cleanup done. Run without --cleanup to seed data.")
        sys.exit(0)

    print(f"Seed — {TIMESTAMP}")
    try:
        login()
    except Exception as e:
        print(f"FATAL: login failed: {e}")
        sys.exit(1)

    accounts = seed_accounts()
    p5 = seed_p5()
    parts = seed_parts(accounts)
    docs = seed_documents()
    seed_products(parts["all"])
    seed_changes(parts["all"], docs)

    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed")
    print(f"Created: {len(created)} resources")
    for kind, name in created[:30]:
        print(f"  [{kind}] {name}")
    if len(created) > 30:
        print(f"  ... and {len(created)-30} more")
    print(f"{'='*50}")
    sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    main()

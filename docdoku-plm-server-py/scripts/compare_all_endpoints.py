#!/usr/bin/env python3
"""系统化 Payara vs FastAPI 对拍 V2 — 覆盖全部 ~400 端点。

用法:
    python compare_all_endpoints.py              # 标准对拍
    python compare_all_endpoints.py --admin      # Admin 端点
    python compare_all_endpoints.py --fresh      # 清空→种子→对拍
    python compare_all_endpoints.py --summary    # 仅汇总
"""
import re, json, sys, os, time
from urllib.request import Request, urlopen
from urllib.error import HTTPError

FA = "http://localhost:8009"
PY = "http://localhost:8005"
API = "/docdoku-plm-server-rest/api"
WS = "Workspace_2"
LOGIN = "test1"

# ── 登录 ──
def login(host, user="test1", pwd="password"):
    url = f"{host}{API}/auth/login"
    data = json.dumps({"login": user, "password": pwd}).encode()
    req = Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    resp = urlopen(req, timeout=10)
    return dict(resp.headers).get("jwt", "")

def curl(method, host, path, body_dict=None, token=None):
    url = f"{host}{API}{path}"
    tok = token or ""
    headers = {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}
    body = None
    if method in ("POST", "PUT") and body_dict is not None:
        body = json.dumps(body_dict).encode()
    req = Request(url, data=body, headers=headers, method=method)
    try:
        resp = urlopen(req, timeout=15)
        code = resp.status
        try: data = json.loads(resp.read().decode())
        except: data = None
    except HTTPError as e:
        code = e.code
        try: data = json.loads(e.read().decode())
        except: data = None
    return code, data

def get_keys(data):
    if isinstance(data, list):
        if data and isinstance(data[0], dict): return sorted(data[0].keys())
        return []
    elif isinstance(data, dict): return sorted(data.keys())
    return []

def compare(name, method, path, body=None, token_fa=None, token_py=None):
    fa_code, fa_data = curl(method, FA, path, body_dict=body, token=token_fa)
    py_code, py_data = curl(method, PY, path, body_dict=body, token=token_py)
    fa_keys = get_keys(fa_data); py_keys = get_keys(py_data)
    if fa_code == py_code and fa_keys == py_keys:
        # 同状态码同 key：深度对比错误文本（仅 4xx/5xx 时）
        if fa_code >= 400 and isinstance(fa_data, dict) and isinstance(py_data, dict):
            fa_msg = fa_data.get("detail") or fa_data.get("message") or str(fa_data)
            py_msg = py_data.get("detail") or py_data.get("message") or str(py_data)
            if fa_msg != py_msg:
                return "PARTIAL", f"{fa_code} err-msg-diff FA={fa_msg[:80]} PY={py_msg[:80]}"
        return "MATCH", fa_code
    elif fa_code == py_code:
        fa_only = set(fa_keys) - set(py_keys)
        py_only = set(py_keys) - set(fa_keys)
        parts = []
        if fa_only: parts.append(f"FA+{fa_only}")
        if py_only: parts.append(f"PY+{py_only}")
        return "PARTIAL", f"{fa_code} keys:{' '.join(parts)}"
    else:
        return "MISMATCH", f"FA:{fa_code} PY:{py_code}"

# ── 端点清单: (domain, method, path, name, body_or_None) ──
# body=None → 不使用 body; body={} → POST/PUT 空 body; body=dict → 指定 body
def E(method, path, name, body=None):
    return (method, path, name, body)

# 动态路径: 用 lambda 在 resolve 后求值
def D(method, lam, name, body=None):
    return (method, lam, name, body)

# ================================================================
endpoints = []

A = endpoints.append

# ━━ Auth ━━
A(E("GET",  "/auth/providers", "auth-providers"))
A(E("GET",  "/auth/providers/42", "auth-provider-by-id"))
A(E("POST", "/auth/login", "auth-login"))
A(E("POST", "/auth/recovery", "auth-recovery", {"login": "test1"}))
A(E("GET",  "/auth/logout", "auth-logout"))

# ━━ Accounts ━━
A(E("GET",  "/accounts/me", "accounts-me"))
A(E("GET",  "/accounts/workspaces", "accounts-ws"))
A(E("PUT",  "/accounts/me", "accounts-me-update", {"name": "Test User", "email": "test@test.com"}))

# ━━ Organizations ━━
A(E("GET",  "/organizations", "orgs"))
A(E("GET",  "/organizations/members", "org-members"))

# ━━ Platform ━━
A(E("GET",  "/platform/health", "health"))

# ━━ Languages / Timezones ━━
A(E("GET",  "/languages", "languages"))
A(E("GET",  "/timezones", "timezones"))

# ━━ Workspaces ━━
A(E("GET",  "/workspaces", "ws-list"))
A(E("GET",  "/workspaces/more", "ws-more"))
A(E("GET", f"/workspaces/{WS}", "ws-detail"))
A(E("GET", f"/workspaces/{WS}/stats-overview", "ws-stats"))
A(E("GET", f"/workspaces/{WS}/disk-usage-stats", "ws-disk"))
A(E("GET", f"/workspaces/{WS}/front-options", "ws-front-opt"))
A(E("GET", f"/workspaces/{WS}/back-options", "ws-back-opt"))
A(E("PUT", f"/workspaces/{WS}/front-options", "ws-front-opt-update", {"xml": ""}))
A(E("PUT", f"/workspaces/{WS}/back-options", "ws-back-opt-update", {"xml": ""}))
A(E("GET", f"/workspaces/{WS}/checked-out-documents-stats", "ws-co-doc"))
A(E("GET", f"/workspaces/{WS}/checked-out-parts-stats", "ws-co-part"))
A(E("GET", f"/workspaces/{WS}/users-stats", "ws-users-stats"))

# ━━ Users ━━
A(E("GET", f"/workspaces/{WS}/users", "users"))
A(E("GET", f"/workspaces/{WS}/users/me", "users-me"))
A(E("GET", f"/workspaces/{WS}/users/admin", "users-admin"))
A(E("GET", f"/workspaces/{WS}/users/{LOGIN}/tag-subscriptions", "user-tag-subs"))
A(E("PUT", f"/workspaces/{WS}/users/{LOGIN}/tag-subscriptions/tag1", "user-tag-sub-add", {}))
A(E("DELETE", f"/workspaces/{WS}/users/{LOGIN}/tag-subscriptions/tag1", "user-tag-sub-del"))

# ━━ Groups ━━
A(E("GET", f"/workspaces/{WS}/groups", "groups"))
A(E("GET", f"/workspaces/{WS}/user-group", "user-group-list"))
A(E("GET", f"/workspaces/{WS}/groups/SEED-grp/users", "group-users"))
A(E("GET", f"/workspaces/{WS}/groups/SEED-grp/tag-subscriptions", "group-tag-subs"))

# ━━ Memberships ━━
A(E("GET", f"/workspaces/{WS}/memberships/users", "memberships-users"))
A(E("GET", f"/workspaces/{WS}/memberships/users/me", "memberships-users-me"))
A(E("GET", f"/workspaces/{WS}/memberships/usergroups", "memberships-groups"))
A(E("GET", f"/workspaces/{WS}/memberships/usergroups/me", "memberships-groups-me"))

# ━━ Roles ━━
A(E("GET", f"/workspaces/{WS}/roles", "roles"))
A(E("GET", f"/workspaces/{WS}/roles/inuse", "roles-inuse"))

# ━━ Workflow Models ━━
A(E("GET", f"/workspaces/{WS}/workflow-models", "wf-models"))
A(E("GET", f"/workspaces/{WS}/workflow-models/1", "wf-model-by-id"))

# ━━ Workflow Instances ━━
A(E("GET", f"/workspaces/{WS}/workflow-instances/1", "wf-instance"))
A(E("GET", f"/workspaces/{WS}/workflow-instances/1/aborted", "wf-instance-aborted"))
A(E("GET", f"/workspaces/{WS}/workspace-workflows", "ws-workflows"))
A(E("GET", f"/workspaces/{WS}/workspace-workflows/1", "ws-workflow-detail"))
A(E("GET", f"/workspaces/{WS}/workspace-workflows/1/aborted", "ws-workflow-aborted"))

# ━━ Parts (collection) ━━
A(E("GET", f"/workspaces/{WS}/parts?start=0&length=1", "parts-list"))
A(E("GET", f"/workspaces/{WS}/parts/count", "parts-count"))
A(E("GET", f"/workspaces/{WS}/parts/numbers", "parts-numbers"))
A(E("GET", f"/workspaces/{WS}/parts/checkedout", "parts-co"))
A(E("GET", f"/workspaces/{WS}/parts/countCheckedOut", "parts-co-count"))
A(E("GET", f"/workspaces/{WS}/parts/search", "parts-search"))
A(E("GET", f"/workspaces/{WS}/parts/tags/nosuchtag", "parts-by-tag"))
A(E("GET", f"/workspaces/{WS}/parts/parts_last_iter", "parts-last-iter"))

# ━━ Parts (single, dynamic) ━━
def _parts():
    part_key = os.environ.get("PART_KEY", "")
    return [
        E("GET", f"/workspaces/{WS}/parts/{part_key}", "part-detail"),
        E("DELETE", f"/workspaces/{WS}/parts/{part_key}", "part-delete"),
        E("GET", f"/workspaces/{WS}/parts/{part_key}/aborted-workflows", "part-aborted-wf"),
        E("GET", f"/workspaces/{WS}/parts/{part_key}/instances", "part-instances"),
        E("GET", f"/workspaces/{WS}/parts/{part_key}/baselines", "part-baselines"),
        E("GET", f"/workspaces/{WS}/parts/{part_key}/used-by-as-component", "part-usedby-comp"),
        E("GET", f"/workspaces/{WS}/parts/{part_key}/used-by-as-substitute", "part-usedby-sub"),
        E("GET", f"/workspaces/{WS}/parts/{part_key}/used-by-product-instance-masters", "part-usedby-pim"),
        E("GET", f"/workspaces/{WS}/parts/{part_key}/tags", "part-tags"),
        E("PUT", f"/workspaces/{WS}/parts/{part_key}/release", "part-release", {}),
        E("PUT", f"/workspaces/{WS}/parts/{part_key}/obsolete", "part-obsolete", {}),
        E("PUT", f"/workspaces/{WS}/parts/{part_key}/acl", "part-acl-update", {"userEntries": {}, "groupEntries": {}}),
    ]

# ━━ Part effectivities ━━
def _effectivities():
    part_key = os.environ.get("PART_KEY", "")
    return [
        E("GET", f"/workspaces/{WS}/parts/{part_key}/effectivities", "part-eff-list"),
    ]

# ━━ Part Templates ━━
A(E("GET", f"/workspaces/{WS}/part-templates", "pt-templates"))

# ━━ Attributes ━━
A(E("GET", f"/workspaces/{WS}/attributes/part-iterations", "attrs-part-iter"))
A(E("GET", f"/workspaces/{WS}/attributes/path-data", "attrs-path-data"))

# ━━ Documents (collection) ━━
A(E("GET", f"/workspaces/{WS}/documents?start=0&length=1", "docs-list"))
A(E("GET", f"/workspaces/{WS}/documents/count", "docs-count"))
A(E("GET", f"/workspaces/{WS}/documents/checkedout", "docs-co"))
A(E("GET", f"/workspaces/{WS}/documents/countCheckedOut", "docs-co-count"))
A(E("GET", f"/workspaces/{WS}/documents/search", "docs-search"))
A(E("GET", f"/workspaces/{WS}/documents/doc_revs", "docs-revs-to-link"))

# ━━ Documents (single, dynamic) ━━
def _docs():
    doc_key = os.environ.get("DOC_KEY", "")
    return [
        E("GET", f"/workspaces/{WS}/documents/{doc_key}", "doc-detail"),
        E("DELETE", f"/workspaces/{WS}/documents/{doc_key}", "doc-delete"),
        E("GET", f"/workspaces/{WS}/documents/{doc_key}/aborted-workflows", "doc-aborted-wf"),
        E("PUT", f"/workspaces/{WS}/documents/{doc_key}/release", "doc-release", {}),
        E("PUT", f"/workspaces/{WS}/documents/{doc_key}/obsolete", "doc-obsolete", {}),
        E("PUT", f"/workspaces/{WS}/documents/{doc_key}/acl", "doc-acl-update", {"userEntries": {}, "groupEntries": {}}),
        E("PUT", f"/workspaces/{WS}/documents/{doc_key}/tags", "doc-tags-set", ["tag1"]),
        E("GET", f"/workspaces/{WS}/documents/{doc_key}/share", "doc-share-list"),
    ]

# ━━ Document Templates ━━
A(E("GET", f"/workspaces/{WS}/document-templates", "dt-templates"))

# ━━ Folders ━━
A(E("GET", f"/workspaces/{WS}/folders", "folders"))
A(E("GET", f"/workspaces/{WS}/folders/Workspace_2/documents", "folder-root-docs"))
A(E("GET", f"/workspaces/{WS}/folders/Workspace_2/SeedFolder/folders", "folder-sub"))

# ━━ Products (CI) ━━
A(E("GET", f"/workspaces/{WS}/products", "products"))
A(E("GET", f"/workspaces/{WS}/products/numbers", "products-numbers"))
A(E("GET", f"/workspaces/{WS}/products/search", "products-search"))

def _ci():
    ci = os.environ.get("CI", "ACLCI-B98DED")
    return [
        E("GET", f"/workspaces/{WS}/products/{ci}", "ci-detail"),
        E("GET", f"/workspaces/{WS}/products/{ci}/filter", "ci-filter"),
        E("GET", f"/workspaces/{WS}/products/{ci}/paths", "ci-paths"),
        E("GET", f"/workspaces/{WS}/products/{ci}/path-choices", "ci-path-choices"),
        E("GET", f"/workspaces/{WS}/products/{ci}/versions-choices", "ci-vers-choices"),
        E("GET", f"/workspaces/{WS}/products/{ci}/releases/last", "ci-last-release"),
        E("GET", f"/workspaces/{WS}/products/{ci}/bom", "ci-bom"),
        E("GET", f"/workspaces/{WS}/products/{ci}/export-files", "ci-export"),
        E("GET", f"/workspaces/{WS}/products/{ci}/path-to-path-links-types", "ci-ptpl-types"),
        E("GET", f"/workspaces/{WS}/products/{ci}/path-to-path-links/source/path-src/target/path-tgt", "ci-ptpl-src-tgt"),
        E("GET", f"/workspaces/{WS}/products/{ci}/decode-path/u1", "ci-decode-path"),
        E("PUT", f"/workspaces/{WS}/products/{ci}/cascade-checkout", "ci-cascade-co", {}),
        E("PUT", f"/workspaces/{WS}/products/{ci}/cascade-checkin", "ci-cascade-ci", {}),
        E("PUT", f"/workspaces/{WS}/products/{ci}/cascade-undocheckout", "ci-cascade-undo", {}),
    ]

# ━━ Layers ━━
def _layers():
    ci = os.environ.get("CI", "ACLCI-B98DED")
    return [
        E("GET", f"/workspaces/{WS}/products/{ci}/layers", "layers"),
    ]

# ━━ Product Baselines ━━
A(E("GET", f"/workspaces/{WS}/product-baselines", "pb-all"))
def _baselines():
    ci = os.environ.get("CI", "ACLCI-B98DED")
    bl_id = os.environ.get("BL_ID", "3")
    return [
        E("GET", f"/workspaces/{WS}/product-baselines/{ci}/baselines", "pb-ci-list"),
        E("GET", f"/workspaces/{WS}/product-baselines/{ci}/baselines/{bl_id}", "pb-ci-detail"),
        E("GET", f"/workspaces/{WS}/product-baselines/{ci}/baselines/{bl_id}/parts", "pb-ci-parts"),
        E("GET", f"/workspaces/{WS}/product-baselines/{ci}/baselines/{bl_id}/path-to-path-links-types", "pb-ptpl-types"),
        E("GET", f"/workspaces/{WS}/product-baselines/{ci}/baselines/{bl_id}/path-to-path-links/source/src/target/tgt", "pb-ptpl"),
        E("GET", f"/workspaces/{WS}/product-baselines/{bl_id}", "pb-detail"),
        E("GET", f"/workspaces/{WS}/product-baselines/{bl_id}-light", "pb-light"),
        E("GET", f"/workspaces/{WS}/product-baselines/{bl_id}/export-files", "pb-export"),
    ]

# ━━ Product Configurations ━━
A(E("GET", f"/workspaces/{WS}/product-configurations", "pc-all"))
def _configs():
    ci = os.environ.get("CI", "ACLCI-B98DED")
    return [
        E("GET", f"/workspaces/{WS}/product-configurations/{ci}/configurations", "pc-ci-list"),
        E("GET", f"/workspaces/{WS}/product-configurations/{ci}/configurations/42", "pc-ci-detail"),
    ]

# ━━ Product Instances ━━
A(E("GET", f"/workspaces/{WS}/product-instances", "pi-all"))
def _instances():
    ci = os.environ.get("CI", "ACLCI-B98DED")
    sn = os.environ.get("INST_SN", "SN-001")
    return [
        E("GET", f"/workspaces/{WS}/product-instances/{ci}/instances", "pi-ci-list"),
        E("GET", f"/workspaces/{WS}/product-instances/{ci}/instances/{sn}", "pi-detail"),
        E("GET", f"/workspaces/{WS}/product-instances/{ci}/instances/{sn}/iterations", "pi-iters"),
        E("GET", f"/workspaces/{WS}/product-instances/{ci}/instances/{sn}/path-to-path-links-types", "pi-ptpl-types"),
        E("GET", f"/workspaces/{WS}/product-instances/{ci}/instances/{sn}/path-to-path-links/1", "pi-ptpl-detail"),
        E("GET", f"/workspaces/{WS}/product-instances/{ci}/instances/{sn}/path-to-path-links/source/src/target/tgt", "pi-ptpl-src-tgt"),
        E("GET", f"/workspaces/{WS}/product-instances/{ci}/instances/{sn}/link-path-part/u1", "pi-link-path"),
        E("GET", f"/workspaces/{WS}/product-instances/{ci}/instances/{sn}/pathdata/u1", "pi-pathdata"),
    ]

# ━━ Changes: Issues ━━
def _issues():
    iss = os.environ.get("ISS_ID", "41")
    return [
        E("GET", f"/workspaces/{WS}/changes/issues", "issues"),
        E("GET", f"/workspaces/{WS}/changes/issues/link", "issues-link"),
        E("GET", f"/workspaces/{WS}/changes/issues/{iss}", "issue-detail"),
    ]

# ━━ Changes: Requests ━━
A(E("GET", f"/workspaces/{WS}/changes/requests", "requests"))
A(E("GET", f"/workspaces/{WS}/changes/requests/link", "requests-link"))
A(E("GET", f"/workspaces/{WS}/changes/requests/42", "request-detail"))

# ━━ Changes: Orders ━━
A(E("GET", f"/workspaces/{WS}/changes/orders", "orders"))
A(E("GET", f"/workspaces/{WS}/changes/orders/42", "order-detail"))

# ━━ Changes: Milestones ━━
def _milestones():
    ms = os.environ.get("MS_ID", "1")
    return [
        E("GET", f"/workspaces/{WS}/changes/milestones", "milestones"),
        E("GET", f"/workspaces/{WS}/changes/milestones/{ms}", "milestone-detail"),
        E("GET", f"/workspaces/{WS}/changes/milestones/{ms}/requests", "milestone-reqs"),
        E("GET", f"/workspaces/{WS}/changes/milestones/{ms}/orders", "milestone-orders"),
    ]

# ━━ Tasks ━━
A(E("GET", f"/workspaces/{WS}/tasks/{LOGIN}/assigned", "tasks-assigned"))
A(E("GET", f"/workspaces/{WS}/tasks/{LOGIN}/documents", "tasks-docs"))
A(E("GET", f"/workspaces/{WS}/tasks/{LOGIN}/parts", "tasks-parts"))
A(E("GET", f"/workspaces/{WS}/tasks/1", "task-detail"))

# ━━ Tags ━━
A(E("GET", f"/workspaces/{WS}/tags", "tags"))
A(E("GET", f"/workspaces/{WS}/tags/1/documents", "tag-docs"))

# ━━ Document Baselines ━━
def _doc_baselines():
    bl_id = os.environ.get("BL_ID", "3")
    return [
        E("GET", f"/workspaces/{WS}/document-baselines", "db-all"),
        E("GET", f"/workspaces/{WS}/document-baselines/{bl_id}", "db-detail"),
        E("GET", f"/workspaces/{WS}/document-baselines/{bl_id}-light", "db-light"),
        E("GET", f"/workspaces/{WS}/document-baselines/{bl_id}/export-files", "db-export"),
    ]

# ━━ LOV ━━
A(E("GET", f"/workspaces/{WS}/lov", "lov"))
A(E("GET", f"/workspaces/{WS}/lov/test-lov", "lov-detail"))

# ━━ Effectivities ━━
A(E("GET", f"/workspaces/{WS}/effectivities/1", "eff-detail"))

# ━━ Webhooks ━━
A(E("GET", f"/workspaces/{WS}/webhooks", "webhooks"))
A(E("GET", f"/workspaces/{WS}/webhooks/1", "webhook-detail"))

# ━━ Shared ━━
A(E("GET", f"/shared/{WS}/documents/SEED-DOC-A", "shared-doc"))
A(E("GET", f"/shared/{WS}/parts/SEED-ASSEM-A", "shared-part"))

# ━━ File downloads ━━
def _files():
    part_key = os.environ.get("PART_KEY", "")
    if part_key:
        pn, ver = part_key.split("-") if "-" in part_key else (part_key, "A")
        return [
            E("GET", f"/files/{WS}/parts/{pn}/{ver}/1/nativecad/seed.stp", "file-part-nativecad"),
        ]
    return []

# ================================================================
# Admin endpoints
admin_endpoints = [
    E("GET",  "/admin/accounts", "adm-accounts"),
    E("GET",  "/admin/accounts/admin", "adm-account-detail"),
    E("GET",  "/admin/accounts-stats", "adm-accounts-stats"),
    E("GET",  "/admin/workspace-stats", "adm-workspace-stats"),
    E("GET",  "/admin/workspaces", "adm-workspaces"),
    E("GET",  "/admin/platform-options", "adm-platform-opt"),
    E("GET",  "/admin/disk-usage-stats", "adm-disk"),
    E("GET",  "/admin/users-stats", "adm-users-stats"),
    E("GET",  "/admin/documents-stats", "adm-docs-stats"),
    E("GET",  "/admin/products-stats", "adm-products-stats"),
    E("GET",  "/admin/parts-stats", "adm-parts-stats"),
    E("GET",  "/admin/index", "adm-index"),
    E("PUT",  "/admin/index", "adm-index-post", {}),
    E("PUT",  "/admin/accounts/admin/enable", "adm-enable-account", {}),
    E("PUT",  "/admin/accounts/admin/disable", "adm-disable-account", {}),
]

# ================================================================
def resolve_ids(token):
    """动态获取测试数据 ID。"""
    h = {"Authorization": f"Bearer {token}"}
    env = {}

    # 第一个零件
    try:
        resp = urlopen(Request(f"{FA}{API}/workspaces/{WS}/parts?start=0&length=1", headers=h))
        data = json.loads(resp.read().decode())
        if data and "partKey" in data[0]:
            env["PART_KEY"] = data[0]["partKey"]
    except: pass

    # 第一个文档
    try:
        resp = urlopen(Request(f"{FA}{API}/workspaces/{WS}/documents?start=0&length=1", headers=h))
        data = json.loads(resp.read().decode())
        if data and "id" in data[0]:
            env["DOC_KEY"] = data[0]["id"]
    except: pass

    # 第一个 CI
    try:
        resp = urlopen(Request(f"{FA}{API}/workspaces/{WS}/products", headers=h))
        data = json.loads(resp.read().decode())
        if data and "id" in data[0]:
            env["CI"] = data[0]["id"]
    except: pass

    # 第一个 baseline
    try:
        resp = urlopen(Request(f"{FA}{API}/workspaces/{WS}/product-baselines", headers=h))
        data = json.loads(resp.read().decode())
        if data and "id" in data[0]:
            env["BL_ID"] = str(data[0]["id"])
    except: pass

    # 第一个 issue
    try:
        resp = urlopen(Request(f"{FA}{API}/workspaces/{WS}/changes/issues", headers=h))
        data = json.loads(resp.read().decode())
        if data and "id" in data[0]:
            env["ISS_ID"] = str(data[0]["id"])
    except: pass

    # 第一个 milestone
    try:
        resp = urlopen(Request(f"{FA}{API}/workspaces/{WS}/changes/milestones", headers=h))
        data = json.loads(resp.read().decode())
        if data and "id" in data[0]:
            env["MS_ID"] = str(data[0]["id"])
    except: pass

    # 第一个 product instance serial number
    try:
        ci = env.get("CI", "ACLCI-B98DED")
        resp = urlopen(Request(f"{FA}{API}/workspaces/{WS}/product-instances/{ci}/instances", headers=h))
        data = json.loads(resp.read().decode())
        if data and "serialNumber" in data[0]:
            env["INST_SN"] = data[0]["serialNumber"]
    except: pass

    for k, v in env.items(): os.environ[k] = v
    print(f"Resolved: CI={env.get('CI')} PART_KEY={env.get('PART_KEY')} DOC_KEY={env.get('DOC_KEY')} BL={env.get('BL_ID')} ISS={env.get('ISS_ID')} MS={env.get('MS_ID')} INST_SN={env.get('INST_SN')}")
    return env

def resolve_all():
    """解析动态端点（lambda 形式）。"""
    all_e = list(endpoints)  # 拷贝静态列表
    # 动态域
    for fn in [_parts, _effectivities, _docs, _ci, _layers, _baselines, _configs,
               _instances, _issues, _milestones, _doc_baselines, _files]:
        try:
            for e in fn():
                all_e.append(e)
        except: pass
    return all_e

def run_compare(token_fa, token_py, entry_list, label):
    stats = {"MATCH": 0, "PARTIAL": 0, "MISMATCH": 0, "ERROR": 0}
    results = []
    print(f"\n═══ {label} — {len(entry_list)} 端点 ═══\n")
    for entry in entry_list:
        if len(entry) == 4:
            method, path, name, body = entry
        elif len(entry) == 3:
            method, path, name = entry
            body = None
        else: continue
        if callable(path): path = path()
        try:
            st, det = compare(name, method, path, body=body, token_fa=token_fa, token_py=token_py)
            marker = {"MATCH": "✓", "PARTIAL": "⚠", "MISMATCH": "✗"}[st]
            print(f"  {marker} {st:8s} {str(det):30s}  {method:4s} {path}")
            stats[st] += 1
            if st != "MATCH":
                results.append((st, method, path, det))
        except Exception as e:
            stats["ERROR"] += 1
            results.append(("ERROR", method, path, str(e)))
            print(f"  ✗ ERROR  {method:4s} {path}: {e}")
    total = sum(stats.values())
    print(f"\n─── {label} 汇总 ───")
    print(f"✓ MATCH: {stats['MATCH']}  ⚠ PARTIAL: {stats['PARTIAL']}  ✗ MISMATCH: {stats['MISMATCH']}  ✗ ERROR: {stats['ERROR']}  Total: {total}")
    return stats, results

def main():
    if "--admin" in sys.argv:
        print("Logging in as admin...")
        tfa = login(FA, "admin"); tpy = login(PY, "admin")
        print(f"FA admin: {tfa[:20] if tfa else 'N/A'}... PY admin: {tpy[:20] if tpy else 'N/A'}...")
        if not tfa or not tpy:
            print("FATAL: login failed"); return
        run_compare(tfa, tpy, admin_endpoints, "Admin 端点")
        return

    # 标准对拍
    print("Logging in as test1...")
    tfa = login(FA); tpy = login(PY)
    print(f"FA: {tfa[:20]}... PY: {tpy[:20]}...")
    if not tfa or not tpy:
        print("FATAL: login failed"); return

    resolve_ids(tfa)
    all_entries = resolve_all()
    stats, mismatches = run_compare(tfa, tpy, all_entries, "全端点对拍 V2")

    if "--summary" in sys.argv:
        return

    # 分类报告
    print(f"\n═══ MISMATCH 分类 ═══\n")
    by_cat = {}
    for st, method, path, det in mismatches:
        if "FA:500 PY:200" in det: cat = "FA500→PY200 (异常吞没)"
        elif "FA:200 PY:500" in det: cat = "FA200→PY500 (内部错误)"
        elif "FA:404 PY:500" in det: cat = "FA404→PY500 (异常处理)"
        elif "FA:500 PY:200" in det: cat = "FA500→PY200 (异常吞没)"
        elif "FA:200 PY:404" in det: cat = "FA200→PY404 (缺失路由)"
        elif "FA:404 PY:200" in det: cat = "FA404→PY200 (缺少404)"
        elif "FA:404 PY:403" in det: cat = "FA404→PY403 (权限次序)"
        elif "FA:405 PY:404" in det: cat = "FA405→PY404 (方法不允许)"
        elif "FA:403 PY:500" in det: cat = "FA403→PY500 (权限转500)"
        elif "FA:422 PY:500" in det: cat = "FA422→PY500 (校验→500)"
        else: cat = f"其他 ({det})"
        by_cat.setdefault(cat, []).append((method, path))

    for cat, items in sorted(by_cat.items()):
        print(f"  [{cat}] ({len(items)} 项)")
        for m, p in items:
            print(f"    {m} {p}")

if __name__ == "__main__":
    main()

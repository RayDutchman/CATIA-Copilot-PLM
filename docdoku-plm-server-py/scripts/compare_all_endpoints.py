#!/usr/bin/env python3
"""系统化 Payara vs FastAPI 对拍脚本。

从 Java Resource 文件提取全部端点，逐端点 curl 双后端对比。
用法: cd docdoku-plm-server-py && source venv/bin/activate && python scripts/compare_all_endpoints.py
"""

import re, json, subprocess, sys
from urllib.request import Request, urlopen
from urllib.error import HTTPError

JAVA_DIR = "../docdoku-plm-server/docdoku-plm-server-rest/src/main/java/com/docdoku/plm/server/rest/"
FA = "http://localhost:8009"
PY = "http://localhost:8005"
API = "/docdoku-plm-server-rest/api"
WS = "Workspace_2"
CI = "ACLCI-B98DED"
DOC_KEY = "SEED-20260705-184807-d-0-A"
PART_KEY = "SEED-20260705-184807-p00-A"
BASELINE_ID = "3"
ISSUE_ID = "41"
LOGIN = "test1"

token_fa = None
token_py = None

def login(host):
    url = f"{host}{API}/auth/login"
    data = json.dumps({"login": "test1", "password": "password"}).encode()
    req = Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    resp = urlopen(req, timeout=10)
    return dict(resp.headers).get("jwt", "")

def curl(method, host, path):
    url = f"{host}{API}{path}"
    tok = token_fa if host == FA else token_py
    headers = {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}
    body = None
    if method in ("POST", "PUT"):
        body = json.dumps({}).encode()
    req = Request(url, data=body, headers=headers, method=method)
    try:
        resp = urlopen(req, timeout=15)
        code = resp.status
        try:
            data = json.loads(resp.read().decode())
        except:
            data = None
    except HTTPError as e:
        code = e.code
        try:
            data = json.loads(e.read().decode())
        except:
            data = None
    return code, data

def compare(name, method, path, fa_expected=200, py_expected=200):
    fa_code, fa_data = curl(method, FA, path)
    py_code, py_data = curl(method, PY, path)

    # 提取 keys 作对比（兼容 dict / list / 标量）
    def get_keys(data):
        if isinstance(data, list):
            if data and isinstance(data[0], dict):
                return sorted(data[0].keys())
            else:
                return [type(data[0]).__name__ for x in data[:1]] if data else []
        elif isinstance(data, dict):
            return sorted(data.keys())
        else:
            return []

    fa_keys = get_keys(fa_data)
    py_keys = get_keys(py_data)

    match = fa_code == py_code and fa_keys == py_keys
    if match:
        return f"  \u2713 MATCH  {fa_code}"
    elif fa_code == py_code:
        fa_only = set(fa_keys) - set(py_keys)
        py_only = set(py_keys) - set(fa_keys)
        parts = []
        if fa_only: parts.append(f"FA+{fa_only}")
        if py_only: parts.append(f"PY+{py_only}")
        return f"  \u26a0 PARTIAL {fa_code}/{py_code} keys: {', '.join(parts)}"
    else:
        return f"  \u2717 MISMATCH FA:{fa_code} PY:{py_code}"

# ============================================================
# 端点清单：method, path, name
# 从 Java Resource 文件提取，覆盖全部 GET 端点 + 部分 POST/PUT/DELETE
# ============================================================
endpoints = [
    # ---- Auth ----
    ("GET",  "/auth/providers", "providers"),
    ("GET",  "/auth/providers/42", "provider by id"),
    ("GET",  "/auth/logout", "logout"),
    ("POST", "/auth/login", "login"),  # broken, Payara 500

    # ---- Admin (仅 accounts 和 platform-options，跳过 index/统计数据) ----
    ("GET",  "/admin/accounts", "admin accounts"),
    ("GET",  "/admin/platform-options", "platform options"),

    # ---- Platform ----
    ("GET",  "/platform/health", "health"),

    # ---- Languages / Timezones ----
    ("GET",  "/languages", "languages"),
    ("GET",  "/timezones", "timezones"),

    # ---- Accounts ----
    ("GET",  "/accounts/me", "accounts/me"),
    ("GET",  "/accounts/workspaces", "accounts workspaces"),

    # ---- Organizations ----
    ("GET",  "/organizations", "organization"),
    ("GET",  "/organizations/members", "org members"),

    # ---- Workspaces ----
    ("GET",  "/workspaces", "workspaces list"),
    ("GET", f"/workspaces/{WS}", "workspace detail"),
    ("GET", f"/workspaces/{WS}/stats-overview", "stats-overview"),
    ("GET", f"/workspaces/{WS}/disk-usage-stats", "disk-usage-stats"),
    ("GET", f"/workspaces/{WS}/front-options", "front-options"),
    ("GET", f"/workspaces/{WS}/back-options", "back-options"),
    ("GET", f"/workspaces/{WS}/checked-out-documents-stats", "checked-out-documents-stats"),
    ("GET", f"/workspaces/{WS}/checked-out-parts-stats", "checked-out-parts-stats"),
    ("GET", f"/workspaces/{WS}/users-stats", "users-stats"),
    ("GET", f"/workspaces/{WS}/user-group", "user-group list"),
    ("GET",  "/workspaces/more", "workspaces more"),

    # ---- Users/Groups/Memberships ----
    ("GET",  f"/workspaces/{WS}/users", "users"),
    ("GET",  f"/workspaces/{WS}/users/me", "users/me"),
    ("GET",  f"/workspaces/{WS}/users/admin", "users/admin"),
    ("GET",  f"/workspaces/{WS}/groups", "groups"),
    ("GET",  f"/workspaces/{WS}/groups/{LOGIN}/tag-subscriptions", "group tag-subs"),
    ("GET",  f"/workspaces/{WS}/groups/SEED-grp/users", "group users"),
    ("GET",  f"/workspaces/{WS}/memberships/users", "memberships users"),
    ("GET",  f"/workspaces/{WS}/memberships/users/me", "memberships users/me"),
    ("GET",  f"/workspaces/{WS}/memberships/usergroups", "memberships groups"),
    ("GET",  f"/workspaces/{WS}/memberships/usergroups/me", "memberships groups/me"),
    ("GET",  f"/workspaces/{WS}/roles", "roles"),
    ("GET",  f"/workspaces/{WS}/roles/inuse", "roles inuse"),

    # ---- Workflow ----
    ("GET",  f"/workspaces/{WS}/workflow-models", "workflow-models"),
    ("GET",  f"/workspaces/{WS}/workflow-models/1", "workflow-model by id"),
    ("GET",  f"/workspaces/{WS}/workflow-instances/1", "workflow instance"),
    ("GET",  f"/workspaces/{WS}/workflow-instances/1/aborted", "workflow aborted"),
    ("GET",  f"/workspaces/{WS}/workspace-workflows", "workspace-workflows"),

    # ---- Parts ----
    ("GET",  f"/workspaces/{WS}/parts?start=0&length=1", "parts list"),
    ("GET",  f"/workspaces/{WS}/parts/count", "parts count"),
    ("GET",  f"/workspaces/{WS}/parts/checkedout", "parts checkedout"),
    ("GET",  f"/workspaces/{WS}/parts/countCheckedOut", "parts countCheckedOut"),
    ("GET",  f"/workspaces/{WS}/parts/search", "parts search"),
    ("GET",  f"/workspaces/{WS}/parts/numbers", "parts numbers"),
    ("GET",  f"/workspaces/{WS}/parts/{PART_KEY}", "part detail"),
    ("GET",  f"/workspaces/{WS}/parts/{PART_KEY}/instances", "part instances"),
    ("GET",  f"/workspaces/{WS}/parts/{PART_KEY}/baselines", "part baselines"),
    ("GET",  f"/workspaces/{WS}/parts/{PART_KEY}/aborted-workflows", "part aborted-workflows"),
    ("GET",  f"/workspaces/{WS}/parts/{PART_KEY}/used-by-as-component", "part used-by-component"),
    ("GET",  f"/workspaces/{WS}/parts/{PART_KEY}/used-by-as-substitute", "part used-by-sub"),
    ("GET",  f"/workspaces/{WS}/parts/{PART_KEY}/used-by-product-instance-masters", "part used-by-pim"),
    ("GET",  f"/workspaces/{WS}/parts/SEED-ASSEM/effectivities", "part effectivities"),

    # ---- Part Templates ----
    ("GET",  f"/workspaces/{WS}/part-templates", "part-templates"),

    # ---- Attributes ----
    ("GET",  f"/workspaces/{WS}/attributes/part-iterations", "part-iterations attrs"),
    ("GET",  f"/workspaces/{WS}/attributes/path-data", "path-data attrs"),

    # ---- Documents ----
    ("GET",  f"/workspaces/{WS}/documents?start=0&length=1", "docs list"),
    ("GET",  f"/workspaces/{WS}/documents/count", "docs count"),
    ("GET",  f"/workspaces/{WS}/documents/checkedout", "docs checkedout"),
    ("GET",  f"/workspaces/{WS}/documents/countCheckedOut", "docs countCheckedOut"),
    ("GET",  f"/workspaces/{WS}/documents/search", "docs search"),
    ("GET",  f"/workspaces/{WS}/documents/doc_revs", "doc revs to link"),
    ("GET",  f"/workspaces/{WS}/documents/{DOC_KEY}", "doc detail"),
    ("GET",  f"/workspaces/{WS}/documents/{DOC_KEY}/aborted-workflows", "doc aborted-workflows"),

    # ---- Document Templates ----
    ("GET",  f"/workspaces/{WS}/document-templates", "doc-templates"),

    # ---- Folders ----
    ("GET",  f"/workspaces/{WS}/folders/Workspace_2/documents", "folder root"),
    ("GET",  f"/workspaces/{WS}/folders/Workspace_2/SeedFolder/folders", "folder sub"),

    # ---- Products (CI) ----
    ("GET",  f"/workspaces/{WS}/products", "products"),
    ("GET",  f"/workspaces/{WS}/products/numbers", "products numbers"),
    ("GET",  f"/workspaces/{WS}/products/{CI}", "ci detail"),
    ("GET",  f"/workspaces/{WS}/products/{CI}/bom", "ci bom"),
    ("GET",  f"/workspaces/{WS}/products/{CI}/filter", "ci filter"),
    ("GET",  f"/workspaces/{WS}/products/{CI}/paths", "ci paths"),
    ("GET",  f"/workspaces/{WS}/products/{CI}/path-choices", "ci path-choices"),
    ("GET",  f"/workspaces/{WS}/products/{CI}/versions-choices", "ci versions-choices"),
    ("GET",  f"/workspaces/{WS}/products/{CI}/releases/last", "ci last release"),
    ("GET",  f"/workspaces/{WS}/products/{CI}/instances", "ci instances filtered"),
    ("GET",  f"/workspaces/{WS}/products/{CI}/export-files", "ci export-files"),
    ("GET",  f"/workspaces/{WS}/products/{CI}/path-to-path-links-types", "ci ptpl types"),
    ("GET",  f"/workspaces/{WS}/products/{CI}/path-to-path-links/source/path-src/target/path-tgt", "ci ptpl by path"),
    ("GET",  f"/workspaces/{WS}/products/{CI}/decode-path/path-param", "ci decode-path"),
    ("GET",  f"/workspaces/{WS}/products/{CI}/document-links/SEED-ASSEM-A-1/wip", "ci document-links"),

    # ---- Layers ----
    ("GET",  f"/workspaces/{WS}/products/{CI}/layers", "layers"),

    # ---- Product Baselines ----
    ("GET",  f"/workspaces/{WS}/product-baselines", "product-baselines"),
    ("GET",  f"/workspaces/{WS}/product-baselines/{CI}/baselines", "ci baselines"),
    ("GET",  f"/workspaces/{WS}/product-baselines/{CI}/baselines/{BASELINE_ID}", "ci baseline"),
    ("GET",  f"/workspaces/{WS}/product-baselines/{CI}/baselines/{BASELINE_ID}/parts", "ci baseline parts"),
    ("GET",  f"/workspaces/{WS}/product-baselines/{CI}/baselines/{BASELINE_ID}/path-to-path-links-types", "ci baseline ptpl types"),
    ("GET",  f"/workspaces/{WS}/product-baselines/{CI}/baselines/{BASELINE_ID}/path-to-path-links/source/src/target/tgt", "ci baseline ptpl"),

    # ---- Product Configurations ----
    ("GET",  f"/workspaces/{WS}/product-configurations", "product-configs"),
    ("GET",  f"/workspaces/{WS}/product-configurations/{CI}/configurations", "ci configs"),
    ("GET",  f"/workspaces/{WS}/product-configurations/{CI}/configurations/42", "ci config detail"),

    # ---- Product Instances ----
    ("GET",  f"/workspaces/{WS}/product-instances", "product-instances"),
    ("GET",  f"/workspaces/{WS}/product-instances/{CI}/instances", "ci instances"),
    ("GET",  f"/workspaces/{WS}/product-instances/{CI}/instances/SN-001", "ci instance detail"),
    ("GET",  f"/workspaces/{WS}/product-instances/{CI}/instances/SN-001/iterations", "ci instance iterations"),
    ("GET",  f"/workspaces/{WS}/product-instances/{CI}/instances/SN-001/path-to-path-links-types", "ci inst ptpl types"),
    ("GET",  f"/workspaces/{WS}/product-instances/{CI}/instances/SN-001/link-path-part/path-part", "ci inst link-path-part"),
    ("GET",  f"/workspaces/{WS}/product-instances/{CI}/instances/SN-001/path-to-path-links/1", "ci inst ptpl detail"),
    ("GET",  f"/workspaces/{WS}/product-instances/{CI}/instances/SN-001/path-to-path-links/source/src/target/tgt", "ci inst ptpl by path"),
    ("GET",  f"/workspaces/{WS}/product-instances/{CI}/instances/SN-001/pathdata/path-x", "ci inst pathdata"),

    # ---- Changes: Issues ----
    ("GET",  f"/workspaces/{WS}/changes/issues", "issues"),
    ("GET",  f"/workspaces/{WS}/changes/issues/link", "issues link"),
    ("GET",  f"/workspaces/{WS}/changes/issues/{ISSUE_ID}", "issue detail"),

    # ---- Changes: Requests ----
    ("GET",  f"/workspaces/{WS}/changes/requests", "requests"),
    ("GET",  f"/workspaces/{WS}/changes/requests/link", "requests link"),
    ("GET",  f"/workspaces/{WS}/changes/requests/42", "request detail"),

    # ---- Changes: Orders ----
    ("GET",  f"/workspaces/{WS}/changes/orders", "orders"),
    ("GET",  f"/workspaces/{WS}/changes/orders/42", "order detail"),

    # ---- Changes: Milestones ----
    ("GET",  f"/workspaces/{WS}/changes/milestones", "milestones"),
    ("GET",  f"/workspaces/{WS}/changes/milestones/42", "milestone detail"),
    ("GET",  f"/workspaces/{WS}/changes/milestones/42/requests", "milestone requests"),
    ("GET",  f"/workspaces/{WS}/changes/milestones/42/orders", "milestone orders"),

    # ---- Tasks ----
    ("GET",  f"/workspaces/{WS}/tasks/1", "task detail"),
    ("GET",  f"/workspaces/{WS}/tasks/{LOGIN}/assigned", "assigned tasks"),
    ("GET",  f"/workspaces/{WS}/tasks/{LOGIN}/documents", "assigned docs"),
    ("GET",  f"/workspaces/{WS}/tasks/{LOGIN}/parts", "assigned parts"),

    # ---- Tags ----
    ("GET",  f"/workspaces/{WS}/tags", "tags"),
    ("GET",  f"/workspaces/{WS}/tags/1/documents", "tag docs"),

    # ---- Document Baselines ----
    ("GET",  f"/workspaces/{WS}/document-baselines", "doc-baselines"),
    ("GET",  f"/workspaces/{WS}/document-baselines/{BASELINE_ID}", "doc-baseline detail"),
    ("GET",  f"/workspaces/{WS}/document-baselines/{BASELINE_ID}-light", "doc-baseline light"),
    ("GET",  f"/workspaces/{WS}/document-baselines/{BASELINE_ID}/export-files", "doc-baseline export"),

    # ---- LOV ----
    ("GET",  f"/workspaces/{WS}/lov", "lov"),
    ("GET",  f"/workspaces/{WS}/lov/test-lov", "lov detail"),

    # ---- Effectivities (workspace level) ----
    ("GET",  f"/workspaces/{WS}/effectivities/1", "effectivity detail"),

    # ---- Webhooks ----
    ("GET",  f"/workspaces/{WS}/webhooks", "webhooks"),
    ("GET",  f"/workspaces/{WS}/webhooks/1", "webhook detail"),

    # ---- Tags subscriptions ----
    ("GET",  f"/workspaces/{WS}/users/{LOGIN}/tag-subscriptions", "user tag-subs"),

    # ---- Shared ----
    ("GET",  f"/shared/{WS}/documents/SEED-DOC-A", "shared doc detail"),
    ("GET",  f"/shared/{WS}/parts/SEED-ASSEM-A", "shared part detail"),
]

def main():
    global token_fa, token_py
    print("Logging in...")
    token_fa = login(FA)
    token_py = login(PY)
    print(f"FA: {token_fa[:30]}...  PY: {token_py[:30]}...")

    matched = partial = mismatch = error = 0
    print(f"\n═══ 对拍 {len(endpoints)} 端点 ═══\n")

    for method, path, name in endpoints:
        try:
            result = compare(name, method, path)
            print(f"{result}  {method} {path}")
            if result.startswith("  \u2713"): matched += 1
            elif result.startswith("  \u26a0"): partial += 1
            else: mismatch += 1
        except Exception as e:
            error += 1
            print(f"  \u2717 ERROR {method} {path}: {e}")

    print(f"\n═══ 汇总 ═══")
    print(f"\u2713 MATCH: {matched}  \u26a0 PARTIAL: {partial}  \u2717 MISMATCH: {mismatch}  \u2717 ERROR: {error}")

if __name__ == "__main__":
    main()

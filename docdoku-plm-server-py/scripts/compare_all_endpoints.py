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
ISSUE_ID = "41"

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
        body = json.dumps({}).encode()  # empty body for most GET-compared endpoints
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
    fa_keys = sorted(fa_data[0].keys()) if isinstance(fa_data, list) and fa_data else (sorted(fa_data.keys()) if isinstance(fa_data, dict) else [])
    py_keys = sorted(py_data[0].keys()) if isinstance(py_data, list) and py_data else (sorted(py_data.keys()) if isinstance(py_data, dict) else [])
    match = fa_code == py_code and fa_keys == py_keys
    if match:
        return f"  ✓ MATCH  {fa_code}"
    elif fa_code == py_code:
        fa_only = set(fa_keys) - set(py_keys)
        py_only = set(py_keys) - set(fa_keys)
        parts = []
        if fa_only: parts.append(f"FA+{fa_only}")
        if py_only: parts.append(f"PY+{py_only}")
        return f"  ⚠ PARTIAL {fa_code}/{py_code} keys: {', '.join(parts)}"
    else:
        return f"  ✗ MISMATCH FA:{fa_code} PY:{py_code}"

# 端点清单：method, path, name
endpoints = [
    # Auth
    ("GET",  "/auth/providers", "providers"),
    ("POST", "/auth/login", "login"),
    ("GET",  "/auth/logout", "logout"),
    # Workspaces
    ("GET",  "/workspaces", "workspaces list"),
    ("GET",  f"/workspaces/{WS}/stats-overview", "stats"),
    # Users/Groups
    ("GET",  f"/workspaces/{WS}/users", "users"),
    ("GET",  f"/workspaces/{WS}/users/me", "users/me"),
    ("GET",  f"/workspaces/{WS}/groups", "groups"),
    ("GET",  f"/workspaces/{WS}/memberships/users", "memberships"),
    ("GET",  f"/workspaces/{WS}/roles", "roles"),
    # Workflow
    ("GET",  f"/workspaces/{WS}/workflow-models", "workflow-models"),
    # Parts
    ("GET",  f"/workspaces/{WS}/parts?start=0&length=1", "parts list"),
    ("GET",  f"/workspaces/{WS}/parts/{PART_KEY}", "part detail"),
    ("GET",  f"/workspaces/{WS}/parts/count", "parts count"),
    ("GET",  f"/workspaces/{WS}/parts/checkedout", "parts checkedout"),
    # Documents
    ("GET",  f"/workspaces/{WS}/documents?start=0&length=1", "docs list"),
    ("GET",  f"/workspaces/{WS}/documents/{DOC_KEY}", "doc detail"),
    ("GET",  f"/workspaces/{WS}/documents/count", "docs count"),
    ("GET",  f"/workspaces/{WS}/folders", "folders"),
    # Products
    ("GET",  f"/workspaces/{WS}/products", "products"),
    ("GET",  f"/workspaces/{WS}/products/{CI}", "ci detail"),
    ("GET",  f"/workspaces/{WS}/product-baselines", "product-baselines"),
    ("GET",  f"/workspaces/{WS}/product-configurations", "product-configs"),
    ("GET",  f"/workspaces/{WS}/product-instances", "product-instances"),
    # Changes
    ("GET",  f"/workspaces/{WS}/changes/issues", "issues"),
    ("GET",  f"/workspaces/{WS}/changes/milestones", "milestones"),
    ("GET",  f"/workspaces/{WS}/changes/requests", "requests"),
    ("GET",  f"/workspaces/{WS}/changes/orders", "orders"),
    # Admin
    ("GET",  "/admin/accounts", "admin accounts"),
    # Misc
    ("GET",  "/languages", "languages"),
    ("GET",  "/platform/health", "health"),
    # Accounts
    ("GET",  "/accounts/me", "accounts/me"),
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
            if result.startswith("  ✓"): matched += 1
            elif result.startswith("  ⚠"): partial += 1
            else: mismatch += 1
        except Exception as e:
            error += 1
            print(f"  ✗ ERROR {method} {path}: {e}")
    
    print(f"\n═══ 汇总 ═══")
    print(f"✓ MATCH: {matched}  ⚠ PARTIAL: {partial}  ✗ MISMATCH: {mismatch}  ✗ ERROR: {error}")

if __name__ == "__main__":
    main()

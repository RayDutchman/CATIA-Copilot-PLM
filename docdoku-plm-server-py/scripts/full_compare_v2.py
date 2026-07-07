#!/usr/bin/env python3
"""全量字段级对拍 V2 — 对每个 200 端点做深度递归字段对比。

与 compare_all_endpoints.py 互补：
- compare_all_endpoints.py: 状态码 + 一级 key 对拍
- full_compare_v2.py: 字段级递归 diff + 值对拍

用法:
    python full_compare_v2.py                     # 全量字段对拍
    python full_compare_v2.py --domain products   # 仅指定域
    python full_compare_v2.py --quick             # 快速模式(仅对比第1层)
"""
import json, sys, os, re
from urllib.request import Request, urlopen
from urllib.error import HTTPError

FA = "http://localhost:8009"
PY = "http://localhost:8005"
API = "/docdoku-plm-server-rest/api"
WS = "Workspace_2"
LOGIN = "test1"

def login(host):
    url = f"{host}{API}/auth/login"
    data = json.dumps({"login": "test1", "password": "password"}).encode()
    req = Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    resp = urlopen(req, timeout=10)
    return dict(resp.headers).get("jwt", "")

def get(host, path, token):
    url = f"{host}{API}{path}"
    req = Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        resp = urlopen(req, timeout=15)
        return resp.status, json.loads(resp.read().decode())
    except HTTPError as e:
        try: return e.code, json.loads(e.read().decode())
        except: return e.code, None
    except Exception as e:
        return -1, str(e)

# ── 深度 diff ──
def deep_diff(fa_val, py_val, path="", quick=False):
    """递归对比两个 JSON 值，返回差异列表 [(path, fa_val, py_val, severity)]。"""
    diffs = []

    if type(fa_val) != type(py_val):
        diffs.append((path, f"type:{type(fa_val).__name__}", f"type:{type(py_val).__name__}", "type"))
        return diffs

    if isinstance(fa_val, dict) and isinstance(py_val, dict):
        all_keys = set(fa_val.keys()) | set(py_val.keys())
        for k in sorted(all_keys):
            sub = f"{path}.{k}" if path else k
            if k not in fa_val:
                diffs.append((sub, "MISSING", py_val[k], "missing-fa"))
            elif k not in py_val:
                # 忽略 detail/errorMessage 等错误字段差异
                if k in ("detail", "errorMessage"): continue
                diffs.append((sub, fa_val[k], "MISSING", "missing-py"))
            else:
                diffs.extend(deep_diff(fa_val[k], py_val[k], sub, quick))
                if quick: break  # 仅对比第1层

    elif isinstance(fa_val, list) and isinstance(py_val, list):
        if not fa_val and not py_val: return diffs
        min_len = min(len(fa_val), len(py_val))
        # 对比已有元素
        for i in range(min_len):
            diffs.extend(deep_diff(fa_val[i], py_val[i], f"{path}[{i}]", quick))
            if quick and i >= 1: break
        if len(fa_val) != len(py_val):
            diffs.append((f"{path}.length", len(fa_val), len(py_val), "length"))

    else:
        # 标量值对比
        fa_str = str(fa_val); py_str = str(py_val)
        if fa_str != py_str:
            severity = "value"
            # 判断哪些差异可忽略
            if fa_str.replace(" ", "") == py_str.replace(" ", ""):
                severity = "whitespace"
            elif "T" in fa_str and " " in py_str and fa_str[:10] == py_str[:10]:
                severity = "datetime-format"
            elif re.match(r'^\d+$', fa_str) and re.match(r'^\d+$', py_str):
                severity = "int-vs-str" if int(fa_str) == int(py_str) else "num-diff"
            diffs.append((path, fa_val, py_val, severity))

    return diffs

# ── 端点清单（仅 GET 返回 200 的端点做字段级对比）──
# 按功能域分组
ENDPOINTS_BY_DOMAIN = {
    "auth": [
        ("/auth/providers", "auth-providers"),
    ],
    "accounts": [
        ("/accounts/me", "accounts-me"),
        ("/accounts/workspaces", "accounts-ws"),
    ],
    "organizations": [
        ("/organizations", "orgs"),
        ("/organizations/members", "org-members"),
    ],
    "platform": [
        ("/platform/health", "health"),
    ],
    "languages": [
        ("/languages", "languages"),
        ("/timezones", "timezones"),
    ],
    "workspaces": [
        ("/workspaces", "ws-list"),
        (f"/workspaces/{WS}", "ws-detail"),
        (f"/workspaces/{WS}/stats-overview", "ws-stats"),
        (f"/workspaces/{WS}/disk-usage-stats", "ws-disk"),
        (f"/workspaces/{WS}/front-options", "ws-front-opt"),
        (f"/workspaces/{WS}/back-options", "ws-back-opt"),
    ],
    "users": [
        (f"/workspaces/{WS}/users", "users"),
        (f"/workspaces/{WS}/users/me", "users-me"),
        (f"/workspaces/{WS}/users/admin", "users-admin"),
    ],
    "groups": [
        (f"/workspaces/{WS}/groups", "groups"),
        (f"/workspaces/{WS}/user-group", "user-group"),
    ],
    "memberships": [
        (f"/workspaces/{WS}/memberships/users", "memberships-users"),
        (f"/workspaces/{WS}/memberships/usergroups", "memberships-groups"),
    ],
    "roles": [
        (f"/workspaces/{WS}/roles", "roles"),
        (f"/workspaces/{WS}/roles/inuse", "roles-inuse"),
    ],
    "workflow": [
        (f"/workspaces/{WS}/workflow-models", "wf-models"),
        (f"/workspaces/{WS}/workspace-workflows", "ws-workflows"),
    ],
    "parts": [
        (f"/workspaces/{WS}/parts?start=0&length=1", "parts-list"),
        (f"/workspaces/{WS}/parts/count", "parts-count"),
        (f"/workspaces/{WS}/parts/numbers", "parts-numbers"),
        (f"/workspaces/{WS}/parts/checkedout", "parts-co"),
        (f"/workspaces/{WS}/parts/search", "parts-search"),
        (f"/workspaces/{WS}/parts/parts_last_iter", "parts-last-iter"),
    ],
    "part_templates": [
        (f"/workspaces/{WS}/part-templates", "pt-templates"),
    ],
    "attributes": [
        (f"/workspaces/{WS}/attributes/part-iterations", "attr-part-iter"),
    ],
    "documents": [
        (f"/workspaces/{WS}/documents?start=0&length=1", "docs-list"),
        (f"/workspaces/{WS}/documents/count", "docs-count"),
        (f"/workspaces/{WS}/documents/checkedout", "docs-co"),
        (f"/workspaces/{WS}/documents/search", "docs-search"),
    ],
    "doc_templates": [
        (f"/workspaces/{WS}/document-templates", "dt-templates"),
    ],
    "folders": [
        (f"/workspaces/{WS}/folders", "folders"),
        (f"/workspaces/{WS}/folders/Workspace_2/documents", "folder-root-docs"),
    ],
    "products": [
        (f"/workspaces/{WS}/products", "products"),
        (f"/workspaces/{WS}/products/numbers", "products-numbers"),
    ],
    "product_baselines": [
        (f"/workspaces/{WS}/product-baselines", "pb-all"),
    ],
    "product_configs": [
        (f"/workspaces/{WS}/product-configurations", "pc-all"),
    ],
    "changes": [
        (f"/workspaces/{WS}/changes/issues", "issues"),
        (f"/workspaces/{WS}/changes/issues/link", "issues-link"),
        (f"/workspaces/{WS}/changes/requests", "requests"),
        (f"/workspaces/{WS}/changes/requests/link", "requests-link"),
        (f"/workspaces/{WS}/changes/orders", "orders"),
        (f"/workspaces/{WS}/changes/milestones", "milestones"),
    ],
    "tags": [
        (f"/workspaces/{WS}/tags", "tags"),
    ],
    "lov": [
        (f"/workspaces/{WS}/lov", "lov"),
    ],
}

# 动态端点——需运行时解析 ID
def _resolve_dynamic(token):
    """从 FA API 获取动态 ID。"""
    h = {"Authorization": f"Bearer {token}"}
    dyn = {}

    def _first(path, key):
        try:
            resp = urlopen(Request(f"{FA}{API}{path}", headers=h))
            data = json.loads(resp.read().decode())
            if data and key in data[0]:
                dyn[key] = data[0][key]
        except: pass

    _first(f"/workspaces/{WS}/parts?start=0&length=1", "partKey")
    _first(f"/workspaces/{WS}/documents?start=0&length=1", "id")
    _first(f"/workspaces/{WS}/products", "id")
    _first(f"/workspaces/{WS}/product-baselines", "id")

    dyn["doc_key"] = dyn.get("id", "")
    dyn["part_key"] = dyn.get("partKey", "")
    return dyn

def add_dynamic_endpoints(token):
    dyn = _resolve_dynamic(token)
    pk = dyn.get("part_key", "SEED-ASSEM-A")
    dk = dyn.get("doc_key", "SEED-DOC-A")
    ci = dyn.get("id", "ACLCI-B98DED")
    bl = dyn.get("id", "3")

    ENDPOINTS_BY_DOMAIN["parts"].extend([
        (f"/workspaces/{WS}/parts/{pk}", "part-detail"),
        (f"/workspaces/{WS}/parts/{pk}/instances", "part-instances"),
        (f"/workspaces/{WS}/parts/{pk}/baselines", "part-baselines"),
        (f"/workspaces/{WS}/parts/{pk}/used-by-as-component", "part-usedby-comp"),
    ])
    ENDPOINTS_BY_DOMAIN["documents"].extend([
        (f"/workspaces/{WS}/documents/{dk}", "doc-detail"),
    ])
    ENDPOINTS_BY_DOMAIN["products"].extend([
        (f"/workspaces/{WS}/products/{ci}", "ci-detail"),
        (f"/workspaces/{WS}/products/{ci}/filter", "ci-filter"),
        (f"/workspaces/{WS}/products/{ci}/path-choices", "ci-path-choices"),
        (f"/workspaces/{WS}/products/{ci}/versions-choices", "ci-vers-choices"),
    ])
    ENDPOINTS_BY_DOMAIN["product_baselines"].extend([
        (f"/workspaces/{WS}/product-baselines/{ci}/baselines", "pb-ci-list"),
        (f"/workspaces/{WS}/product-baselines/{bl}", "pb-detail"),
    ])
    ENDPOINTS_BY_DOMAIN["product_configs"].extend([
        (f"/workspaces/{WS}/product-configurations/{ci}/configurations", "pc-ci-list"),
    ])

# ── 运行 ──
def main():
    quick = "--quick" in sys.argv
    domain_filter = None
    for a in sys.argv:
        if a.startswith("--domain="):
            domain_filter = a.split("=")[1]

    print("Logging in...")
    tfa = login(FA); tpy = login(PY)
    if not tfa or not tpy:
        print("FATAL: login failed"); return

    print("Resolving dynamic IDs...")
    add_dynamic_endpoints(tfa)

    total_endpoints = 0
    total_diffs = 0
    by_severity = {}
    report_lines = []

    for domain, entries in sorted(ENDPOINTS_BY_DOMAIN.items()):
        if domain_filter and domain != domain_filter: continue
        domain_diffs = 0
        domain_ok = 0
        domain_err = 0

        for path, label in entries:
            fa_code, fa_data = get(FA, path, tfa)
            py_code, py_data = get(PY, path, tpy)
            total_endpoints += 1

            if fa_code != 200 or py_code != 200:
                domain_err += 1
                continue

            diffs = deep_diff(fa_data, py_data, "", quick)
            if not diffs:
                domain_ok += 1
            else:
                # 过滤可忽略的差异
                real_diffs = [d for d in diffs if d[3] not in ("whitespace", "datetime-format")]
                if real_diffs:
                    domain_diffs += len(real_diffs)
                    for dpath, fa_v, py_v, sev in real_diffs[:10]:  # 最多报10个
                        by_severity[sev] = by_severity.get(sev, 0) + 1
                        report_lines.append(f"    [{sev:12s}] {dpath:40s} FA={str(fa_v)[:50]:50s} PY={str(py_v)[:50]}")
                    report_lines.append(f"    ... (total {len(real_diffs)} field diffs)\n")
                else:
                    domain_ok += 1

        if domain_diffs:
            print(f"\n{'='*60}")
            print(f"  {domain} — {domain_diffs} field diffs, {domain_ok} OK, {domain_err} non-200")
            print(f"{'='*60}")
            for line in report_lines[-domain_diffs-1:]:
                print(line)

    print(f"\n{'='*60}")
    print(f"  全量字段对拍完成: {total_endpoints} 端点")
    print(f"  差异统计: {dict(by_severity)}")

if __name__ == "__main__":
    main()

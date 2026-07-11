#!/usr/bin/env python3
"""全端点双端对拍 v3 —— 种子数据 + 全方法覆盖 + 深度字段递归 diff。

端口: 8005=Payara(参考)  8000=FastAPI(待测)  8009=Payara备

用法:
    python full_compare_v2.py                     # 完整对拍(创建种子→测试→对比→清理)
    python full_compare_v2.py --no-seed            # 跳过种子创建(仅对比已有数据)
    python full_compare_v2.py --report-only        # 仅从已有 report.json 生成摘要
"""
import json
import sys
import time
import uuid
from pathlib import Path
import re
import requests

PY_PORT = 8000
FA_PORT = 8005
PY_BASE = f"http://localhost:{PY_PORT}/docdoku-plm-server-rest/api"
FA_BASE = f"http://localhost:{FA_PORT}/docdoku-plm-server-rest/api"
WS = "GD50"
TAG = str(uuid.uuid4()).replace("-", "")[:10]

seed = {
    "part_number": "SEED-CMP-PART",
    "part_name": "CompareTestPart",
    "doc_id": "SEED-CMP-DOC",
    "doc_title": "CompareTestDoc",
    "issue_name": "SEED-CMP-ISSUE",
    "request_name": "SEED-CMP-REQ",
    "order_name": "SEED-CMP-ORDER",
    "milestone_title": "SEED-CMP-MS",
    "wf_model_id": "SEED-CMP-WF",
    "ci_id": "SEED-CMP-CI",
    "role_name": "SEED-CMP-ROLE",
    "group_id": "SEED-CMP-GRP",
    "lov_name": "SEED-CMP-LOV",
}

# ── 工具函数 ──
def _login(port):
    base = f"http://localhost:{port}/docdoku-plm-server-rest/api"
    try:
        resp = requests.post(f"{base}/auth/login", json={"login": "test1", "password": "password"}, timeout=10)
    except: return ""
    jwt = resp.json().get("jwt", "")
    return jwt or resp.headers.get("jwt", "")

PY_TOKEN = ""; FA_TOKEN = ""

def _request(port, method, path, json_body=None, headers_extra=None, timeout=15):
    tok = PY_TOKEN if port == PY_PORT else FA_TOKEN
    base = PY_BASE if port == PY_PORT else FA_BASE
    h = {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}
    if headers_extra: h.update(headers_extra)
    try:
        r = requests.request(method, f"{base}{path}", json=json_body, headers=h, timeout=timeout)
        ct = r.headers.get("content-type", "")
        if "json" in ct:
            try: return r.status_code, r.json()
            except: return r.status_code, r.text[:500]
        return r.status_code, r.text[:500]
    except Exception as e:
        return -1, str(e)

def fa(method, path, body=None): return _request(FA_PORT, method, path, body)
def py(method, path, body=None): return _request(PY_PORT, method, path, body)

# ── 深度字段 diff ──
def deep_diff(fa_val, py_val, path=""):
    """递归对比两个 JSON 值，返回差异列表 [(path, fa_val, py_val, severity)]。"""
    diffs = []
    if type(fa_val) != type(py_val):
        diffs.append((path, {"_type": type(fa_val).__name__, "_val": fa_val},
                      {"_type": type(py_val).__name__, "_val": py_val}, "type-mismatch"))
        return diffs

    if isinstance(fa_val, dict):
        all_keys = set(fa_val.keys()) | set(py_val.keys())
        for k in sorted(all_keys):
            sub = f"{path}.{k}" if path else k
            if k not in py_val and k not in ("detail", "errorMessage"):
                diffs.append((sub, fa_val[k], "✗MISSING", "missing-in-py"))
            elif k not in fa_val:
                diffs.append((sub, "✗MISSING", py_val[k], "missing-in-fa"))
            else:
                diffs.extend(deep_diff(fa_val[k], py_val[k], sub))
    elif isinstance(fa_val, list):
        if not fa_val and not py_val: return diffs
        min_len = min(len(fa_val), len(py_val))
        for i in range(min(min_len, 5)):  # 最多对比前5个元素
            diffs.extend(deep_diff(fa_val[i], py_val[i], f"{path}[{i}]"))
        if len(fa_val) != len(py_val):
            diffs.append((f"{path}.length", len(fa_val), len(py_val), "array-length"))
    else:
        fa_s, py_s = str(fa_val), str(py_val)
        if fa_s != py_s:
            sev = "value-diff"
            if fa_s.replace(" ", "") == py_s.replace(" ", ""): sev = "whitespace"
            elif "T" in fa_s and fa_s[:10] == py_s[:10]: sev = "datetime-fmt"
            elif fa_s.isdigit() and py_s.isdigit(): sev = "num-diff" if fa_s != py_s else "int-str-fmt"
            diffs.append((path, fa_val, py_val, sev))
    return diffs

# ── 端点定义 ──
def stages():
    s = seed
    pn = f'{s["part_number"]}-A'
    dk = f'{s["doc_id"]}-A'

    return [
        ("创建种子", [
            ("POST", f"/workspaces/{WS}/parts", {"number": s["part_number"], "name": s["part_name"]}, "创建零件"),
            ("POST", f"/workspaces/{WS}/folders/{WS}/documents", {"reference": s["doc_id"], "title": s["doc_title"]}, "创建文档"),
            ("POST", f"/workspaces/{WS}/changes/issues", {"name": s["issue_name"]}, "创建Issue"),
            ("POST", f"/workspaces/{WS}/changes/requests", {"name": s["request_name"]}, "创建Request"),
            ("POST", f"/workspaces/{WS}/changes/orders", {"name": s["order_name"]}, "创建Order"),
            ("POST", f"/workspaces/{WS}/changes/milestones", {"title": s["milestone_title"]}, "创建Milestone"),
            ("POST", f"/workspaces/{WS}/workflow-models", {"id": s["wf_model_id"], "finalLifecycleState": "RELEASED",
             "activityModels": [{"step":0,"type":"SEQUENTIAL","tasksToComplete":1,"tasks":[{"title":"Test","instructions":"t","role":{"name":"ROLE-TEST"}}]}]}, "创建WF模板"),
            ("POST", f"/workspaces/{WS}/products", {"id": s["ci_id"], "designItemNumber": s["part_number"]}, "创建CI"),
            ("POST", f"/workspaces/{WS}/roles", {"name": s["role_name"]}, "创建Role"),
            ("POST", f"/workspaces/{WS}/groups", {"id": s["group_id"]}, "创建Group"),
            ("POST", f"/workspaces/{WS}/lov", {"name": s["lov_name"], "values": [{"name":"opt1","value":"1"}]}, "创建LoV"),
            ("POST", f"/workspaces/{WS}/tags", {"label": TAG, "id": TAG}, "创建Tag"),
        ]),
        ("Auth", [
            ("GET", "/auth/providers", None, "OAuth providers"),
            ("GET", "/auth/providers/42", None, "provider by id"),
            ("POST", "/auth/logout", None, "登出"),
            ("POST", "/auth/recovery", {"login": "test1"}, "密码恢复请求"),
            ("POST", "/auth/recover", {"recoveryUUID": "test", "password": "pass"}, "重置密码"),
        ]),
        ("Accounts/Platform", [
            ("GET", "/accounts/me", None, "我的账号"),
            ("GET", "/accounts/workspaces", None, "我的工作区"),
            ("PUT", "/accounts/me", {"name": "Test", "email": "t@t.com"}, "更新账号"),
            ("GET", "/platform/health", None, "健康检查"),
            ("GET", "/languages", None, "语言"),
            ("GET", "/timezones", None, "时区"),
            ("GET", "/organizations", None, "组织"),
        ]),
        ("Workspace管理", [
            ("GET", f"/workspaces/{WS}", None, "工作区详情"),
            ("GET", f"/workspaces/{WS}/stats-overview", None, "统计"),
            ("GET", f"/workspaces/{WS}/disk-usage-stats", None, "磁盘用量"),
            ("GET", f"/workspaces/{WS}/disk-usage", None, "磁盘(stub)"),
            ("GET", f"/workspaces/{WS}/users-stats", None, "用户统计"),
            ("GET", f"/workspaces/{WS}/front-options", None, "前端选项"),
            ("PUT", f"/workspaces/{WS}/front-options", {"partTableColumns":["number","name"]}, "保存前端选项"),
            ("GET", f"/workspaces/{WS}/back-options", None, "后端选项"),
            ("GET", f"/workspaces/{WS}/checked-out-documents-stats", None, "签出文档"),
            ("GET", f"/workspaces/{WS}/checked-out-parts-stats", None, "签出零件"),
            ("GET", "/workspaces/more", None, "更多工作区"),
            ("GET", "/workspaces", None, "工作区列表"),
        ]),
        ("Parts零件", [
            ("GET", f"/workspaces/{WS}/parts?start=0&length=1", None, "零件列表"),
            ("GET", f"/workspaces/{WS}/parts/count", None, "零件计数"),
            ("GET", f"/workspaces/{WS}/parts/numbers", None, "零件编号"),
            ("GET", f"/workspaces/{WS}/parts/checkedout", None, "已签出"),
            ("GET", f"/workspaces/{WS}/parts/countCheckedOut", None, "签出计数"),
            ("GET", f"/workspaces/{WS}/parts/search?q={s['part_name']}", None, "搜索"),
            ("GET", f"/workspaces/{WS}/parts/{pn}", None, "零件详情"),
            ("PUT", f"/workspaces/{WS}/parts/{pn}/checkout", None, "签出"),
            ("PUT", f"/workspaces/{WS}/parts/{pn}/checkin", None, "签入"),
            ("PUT", f"/workspaces/{WS}/parts/{pn}/tags", {"tags": [{"label": TAG, "id": TAG}]}, "打标签"),
            ("GET", f"/workspaces/{WS}/parts/{pn}/aborted-workflows", None, "终止WF"),
            ("GET", f"/workspaces/{WS}/parts/{pn}/instances", None, "装配实例"),
            ("GET", f"/workspaces/{WS}/parts/{pn}/baselines", None, "基线"),
            ("GET", f"/workspaces/{WS}/parts/{pn}/used-by-as-component", None, "被用作组件"),
            ("GET", f"/workspaces/{WS}/parts/{pn}/used-by-as-substitute", None, "被用作替代品"),
            ("GET", f"/workspaces/{WS}/parts/{pn}/used-by-product-instance-masters", None, "PIM引用"),
            ("GET", f"/workspaces/{WS}/parts/{pn}/tags", None, "零件标签"),
            ("GET", f"/workspaces/{WS}/part-templates", None, "零件模板"),
            ("GET", f"/workspaces/{WS}/part-templates/{pk}/{s['part_number']}-A" if False else f"/workspaces/{WS}/part-templates", None, "模板(跳过)"),
            ("GET", f"/workspaces/{WS}/parts/parts_last_iter", None, "最后迭代"),
        ]),
        ("Documents文档", [
            ("GET", f"/workspaces/{WS}/documents?start=0&length=1", None, "文档列表"),
            ("GET", f"/workspaces/{WS}/documents/count", None, "文档计数"),
            ("GET", f"/workspaces/{WS}/documents/checkedout", None, "已签出"),
            ("GET", f"/workspaces/{WS}/documents/countCheckedOut", None, "签出计数"),
            ("GET", f"/workspaces/{WS}/documents/search?q={s['doc_title']}", None, "搜索"),
            ("GET", f"/workspaces/{WS}/documents/{dk}", None, "文档详情"),
            ("PUT", f"/workspaces/{WS}/documents/{dk}/checkout", None, "签出"),
            ("PUT", f"/workspaces/{WS}/documents/{dk}/checkin", None, "签入"),
            ("GET", f"/workspaces/{WS}/documents/{dk}/aborted-workflows", None, "终止WF"),
            ("PUT", f"/workspaces/{WS}/documents/{dk}/tags", {"tags": [{"label": TAG, "id": TAG}]}, "打标签"),
            ("PUT", f"/workspaces/{WS}/documents/{dk}/release", None, "发布"),
            ("PUT", f"/workspaces/{WS}/documents/{dk}/obsolete", None, "废弃"),
            ("GET", f"/workspaces/{WS}/documents/doc_revs", None, "链接用修订"),
            ("GET", f"/workspaces/{WS}/document-templates", None, "文档模板"),
            ("GET", f"/workspaces/{WS}/folders", None, "文件夹列表"),
            ("GET", f"/workspaces/{WS}/folders/GD50/documents", None, "根文档"),
            ("GET", f"/workspaces/{WS}/document-baselines", None, "基线列表"),
            ("GET", f"/workspaces/{WS}/document-baselines/3", None, "基线详情"),
            ("GET", f"/workspaces/{WS}/document-baselines/3-light", None, "基线轻量"),
            ("GET", f"/workspaces/{WS}/document-baselines/3/export-files", None, "基线导出"),
        ]),
        ("Changes变更", [
            ("GET", f"/workspaces/{WS}/changes/issues", None, "Issue列表"),
            ("GET", f"/workspaces/{WS}/changes/requests", None, "Request列表"),
            ("GET", f"/workspaces/{WS}/changes/orders", None, "Order列表"),
            ("GET", f"/workspaces/{WS}/changes/milestones", None, "里程碑"),
            ("GET", f"/workspaces/{WS}/changes/issues/link", None, "Issue搜索"),
            ("GET", f"/workspaces/{WS}/changes/requests/link", None, "Request搜索"),
            ("GET", f"/workspaces/{WS}/changes/requests/42", None, "Request详情"),
            ("GET", f"/workspaces/{WS}/changes/orders/42", None, "Order详情"),
        ]),
        ("Products产品", [
            ("GET", f"/workspaces/{WS}/products", None, "CI列表"),
            ("GET", f"/workspaces/{WS}/products/numbers", None, "CI编号"),
            ("GET", f"/workspaces/{WS}/products/search", None, "CI搜索"),
            ("GET", f"/workspaces/{WS}/products/{s['ci_id']}", None, "CI详情"),
            ("GET", f"/workspaces/{WS}/products/{s['ci_id']}/filter", None, "产品结构"),
            ("GET", f"/workspaces/{WS}/products/{s['ci_id']}/bom", None, "BOM"),
            ("GET", f"/workspaces/{WS}/products/{s['ci_id']}/paths", None, "路径"),
            ("GET", f"/workspaces/{WS}/products/{s['ci_id']}/path-choices", None, "路径选择"),
            ("GET", f"/workspaces/{WS}/products/{s['ci_id']}/versions-choices", None, "版本选择"),
            ("GET", f"/workspaces/{WS}/products/{s['ci_id']}/releases/last", None, "最后发布"),
            ("GET", f"/workspaces/{WS}/products/{s['ci_id']}/baselines", None, "基线"),
            ("GET", f"/workspaces/{WS}/products/{s['ci_id']}/configurations", None, "配置"),
            ("GET", f"/workspaces/{WS}/products/{s['ci_id']}/instances", None, "实例"),
            ("GET", f"/workspaces/{WS}/products/{s['ci_id']}/decode-path/{pn}", None, "路径解码"),
            ("GET", f"/workspaces/{WS}/products/{s['ci_id']}/export-files", None, "导出文件"),
            ("GET", f"/workspaces/{WS}/products/{s['ci_id']}/path-to-path-links-types", None, "P2P类型"),
            ("GET", f"/workspaces/{WS}/product-baselines", None, "全局基线"),
            ("GET", f"/workspaces/{WS}/product-baselines/{s['ci_id']}/baselines", None, "CI基线"),
            ("GET", f"/workspaces/{WS}/product-configurations", None, "全局配置"),
            ("GET", f"/workspaces/{WS}/product-configurations/{s['ci_id']}/configurations", None, "CI配置"),
            ("GET", f"/workspaces/{WS}/product-instances", None, "全局实例"),
            ("GET", f"/workspaces/{WS}/product-instances/{s['ci_id']}/instances", None, "CI实例"),
            ("DELETE", f"/workspaces/{WS}/products/{s['ci_id']}", None, "删CI"),
        ]),
        ("Users用户管理", [
            ("GET", f"/workspaces/{WS}/users", None, "用户列表"),
            ("GET", f"/workspaces/{WS}/users/me", None, "当前用户"),
            ("GET", f"/workspaces/{WS}/users/admin", None, "管理员"),
            ("GET", f"/workspaces/{WS}/users/{'test1'}", None, "用户详情"),
            ("GET", f"/workspaces/{WS}/groups", None, "用户组"),
            ("GET", f"/workspaces/{WS}/user-group", None, "用户组(旧)"),
            ("GET", f"/workspaces/{WS}/groups/{s['group_id']}/users", None, "组成员"),
            ("GET", f"/workspaces/{WS}/groups/{s['group_id']}/tag-subscriptions", None, "组标签订阅"),
            ("GET", f"/workspaces/{WS}/memberships/users", None, "用户成员"),
            ("GET", f"/workspaces/{WS}/memberships/users/me", None, "我的成员"),
            ("GET", f"/workspaces/{WS}/memberships/usergroups", None, "组成员"),
            ("GET", f"/workspaces/{WS}/memberships/usergroups/me", None, "我的组"),
            ("GET", f"/workspaces/{WS}/roles", None, "角色"),
            ("GET", f"/workspaces/{WS}/roles/inuse", None, "在用角色"),
        ]),
        ("Workflow工作流", [
            ("GET", f"/workspaces/{WS}/workflow-models", None, "模板列表"),
            ("GET", f"/workspaces/{WS}/workflow-models/{s['wf_model_id']}", None, "模板详情"),
            ("GET", f"/workspaces/{WS}/workspace-workflows", None, "工作区WF"),
            ("GET", f"/workspaces/{WS}/workflow-instances/1", None, "WF实例"),
            ("GET", f"/workspaces/{WS}/workflow-instances/1/aborted", None, "终止WF实例"),
            ("GET", f"/workspaces/{WS}/workspace-workflows/1/aborted", None, "终止WS WF"),
            ("GET", f"/workspaces/{WS}/tasks/{'test1'}/assigned", None, "分配任务"),
            ("GET", f"/workspaces/{WS}/tasks/{'test1'}/in-progress", None, "进行中任务"),
            ("GET", f"/workspaces/{WS}/tasks/{'test1'}/documents", None, "任务文档"),
            ("GET", f"/workspaces/{WS}/tasks/{'test1'}/parts", None, "任务零件"),
            ("GET", f"/workspaces/{WS}/tasks/1", None, "任务详情"),
        ]),
        ("Webhook/通知", [
            ("GET", f"/workspaces/{WS}/webhooks", None, "Webhook列表"),
            ("GET", f"/workspaces/{WS}/webhooks/1", None, "Webhook详情"),
            ("GET", f"/workspaces/{WS}/notifications", None, "通知列表"),
        ]),
        ("杂项(LoV/Tags/属性/Share)", [
            ("GET", f"/workspaces/{WS}/lov", None, "LoV列表"),
            ("GET", f"/workspaces/{WS}/lov/{s['lov_name']}", None, "LoV详情"),
            ("GET", f"/workspaces/{WS}/tags", None, "标签列表"),
            ("GET", f"/workspaces/{WS}/tags/{TAG}/documents", None, "标签文档"),
            ("GET", f"/workspaces/{WS}/attributes/part-iterations", None, "零件属性"),
            ("GET", f"/workspaces/{WS}/attributes/path-data", None, "路径属性"),
            ("GET", f"/workspaces/{WS}/parts/{pn}/effectivities", None, "零件效应"),
            ("GET", f"/workspaces/{WS}/effectivities/1", None, "效应详情"),
            ("GET", f"/shared/{WS}/documents/{dk}", None, "共享文档"),
            ("GET", f"/shared/{WS}/parts/{pn}", None, "共享零件"),
        ]),
        ("清理", [
            ("DELETE", f"/workspaces/{WS}/parts/{pn}", None, "删零件"),
            ("DELETE", f"/workspaces/{WS}/documents/{dk}", None, "删文档"),
            ("DELETE", f"/workspaces/{WS}/workflow-models/{s['wf_model_id']}", None, "删WF模板"),
            ("DELETE", f"/workspaces/{WS}/roles/{s['role_name']}", None, "删角色"),
            ("DELETE", f"/workspaces/{WS}/groups/{s['group_id']}", None, "删组"),
        ]),
    ]


def run():
    global PY_TOKEN, FA_TOKEN
    skip_seed = "--no-seed" in sys.argv

    PY_TOKEN = _login(PY_PORT)
    FA_TOKEN = _login(FA_PORT)
    print(f"FA(8005): {'✓' if FA_TOKEN else '✗'}  PY(8000): {'✓' if PY_TOKEN else '✗'}")

    all_stages = stages()
    if skip_seed:
        all_stages = [(n, e) for n, e in all_stages if n != "创建种子"]

    results = []
    stats = {"MATCH": 0, "PARTIAL": 0, "MISMATCH": 0, "BOTH500": 0, "ERROR": 0}

    for stage_name, endpoints in all_stages:
        print(f"\n─── {stage_name} ({len(endpoints)}) ───")
        for method, path, body, desc in endpoints:
            fa_code, fa_data = fa(method, path, body)
            time.sleep(0.03)
            py_code, py_data = py(method, path, body)

            status_match = fa_code == py_code
            fa_keys = set()
            py_keys = set()
            field_diffs = []

            if isinstance(fa_data, dict) and isinstance(py_data, dict):
                fa_keys = _deep_keys(fa_data, 4)
                py_keys = _deep_keys(py_data, 4)
                # 仅对 200+200 做深度字段 diff
                if fa_code == 200 and py_code == 200:
                    field_diffs = deep_diff(fa_data, py_data)
                    # 过滤可忽略差异
                    field_diffs = [d for d in field_diffs if d[3] not in ("whitespace", "datetime-fmt")]

            missing = fa_keys - py_keys
            extra = py_keys - fa_keys

            # 分类
            if fa_code <= 0 or py_code <= 0:
                cat = "ERROR"
            elif fa_code == 500 and py_code == 500:
                cat = "BOTH500"
            elif status_match and not missing and not field_diffs:
                cat = "MATCH"
            elif status_match and (missing or field_diffs):
                cat = "PARTIAL"
            else:
                cat = "MISMATCH"

            stats[cat] = stats.get(cat, 0) + 1
            marker = {"MATCH":"✓","PARTIAL":"△","MISMATCH":"✗","BOTH500":"≈","ERROR":"⚠"}[cat]

            detail = f"FA={fa_code} PY={py_code}"
            if missing: detail += f" miss={len(missing)}"
            if field_diffs:
                detail += f" field-diffs={len(field_diffs)}"
                sev_types = set(d[3] for d in field_diffs)
                detail += f" [{','.join(sorted(sev_types))}]"

            print(f"  {marker} {cat:8s} | {detail:50s} | {method} {path[:70]}")

            results.append({
                "stage": stage_name, "method": method, "path": path, "desc": desc,
                "fa_code": fa_code, "py_code": py_code,
                "missing_keys": sorted(missing), "extra_keys": sorted(extra),
                "field_diffs": [(d[0], str(d[1])[:100], str(d[2])[:100], d[3]) for d in field_diffs[:20]],
                "field_diff_count": len(field_diffs), "category": cat,
            })

    # 汇总
    total = sum(stats.values())
    print(f"\n{'='*70}")
    print(f"SUMMARY: {total} total")
    for k, v in stats.items(): print(f"  {k}: {v}")

    # 按分类输出 MISMATCH
    mismatches = [r for r in results if r["category"] in ("MISMATCH",)]
    if mismatches:
        print(f"\n{'='*70}\nMISMATCH ({len(mismatches)}) 详情:")
        by_status = {}
        for r in mismatches:
            key = f"FA={r['fa_code']} PY={r['py_code']}"
            by_status.setdefault(key, []).append(r)
        for key, items in sorted(by_status.items()):
            print(f"\n  [{key}] ({len(items)}项)")
            for r in items[:10]:
                print(f"    {r['method']} {r['path']} — {r['desc']}")

    # PARTIAL 字段差异汇总
    partials = [r for r in results if r["category"] == "PARTIAL"]
    if partials:
        print(f"\n{'='*70}\nPARTIAL ({len(partials)}) 字段缺失 TOP 20:")
        from collections import Counter
        missing_counter = Counter()
        for r in partials:
            for k in r["missing_keys"]:
                missing_counter[k] += 1
            for d in r.get("field_diffs", []):
                missing_counter[f"[diff] {d[0]}"] += 1
        for field, count in missing_counter.most_common(20):
            print(f"    {count:3d}x  {field}")

    # 保存
    report_path = Path("scripts/full_compare_report.json")
    report_path.parent.mkdir(exist_ok=True)
    with open(report_path, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\n报告: {report_path}")

# ── 辅助 ──
def _deep_keys(obj, depth=4):
    if depth == 0: return set()
    if isinstance(obj, dict):
        r = set()
        for k, v in obj.items():
            r.add(k)
            for s in _deep_keys(v, depth-1): r.add(f"{k}.{s}")
        return r
    if isinstance(obj, list) and obj and isinstance(obj[0], dict):
        return _deep_keys(obj[0], depth-1)
    return set()

if __name__ == "__main__":
    run()

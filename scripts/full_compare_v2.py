#!/usr/bin/env python3
"""全端点双端对拍脚本 v2 —— 含 POST/PUT/DELETE + 种子数据 + 字段级对比。

用法:
  1. --record  仅 Payara 侧录制（保存为 JSON）
  2. --replay   回放录制到 FastAPI（对比 gap report）
  3. --full     录 + 回放（默认）

端口:
  8005 = Payara (参考后端)
  8000 = FastAPI (待测后端)
"""

import json
import sys
import time
import uuid
from pathlib import Path
from typing import Optional

import requests

PY_PORT = 8000
FA_PORT = 8005
PY_BASE = f"http://localhost:{PY_PORT}/docdoku-plm-server-rest/api"
FA_BASE = f"http://localhost:{FA_PORT}/docdoku-plm-server-rest/api"

WS = "Workspace_2"
TAG = str(uuid.uuid4()).replace("-", "")[:10]  # 本次录制唯一标识，自动清理

# ── 种子数据 ──────────────────────────
seed = {
    "part_number": "SEED-COMPARE-PART",
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
}


def _login(port: int) -> str:
    """登录 Payara (jwt header) 或 FastAPI (jwt body)。"""
    base = f"http://localhost:{port}/docdoku-plm-server-rest/api"
    try:
        resp = requests.post(
            f"{base}/auth/login",
            json={"login": "test1", "password": "password"},
            timeout=10,
        )
    except requests.ConnectionError:
        return ""

    # FastAPI
    jwt = resp.json().get("jwt", "")
    if jwt:
        return jwt
    # Payara
    jwt_head = resp.headers.get("jwt", "")
    if jwt_head:
        return jwt_head
    return ""


PY_TOKEN = ""
FA_TOKEN = ""


def _py(method: str, path: str, json_body: dict = None,
        extra_headers: dict = None, timeout: int = 15) -> tuple[int, dict | str]:
    """请求 FastAPI（8000），返回 (status, parsed_json_or_text)。"""
    global PY_TOKEN
    if not PY_TOKEN:
        PY_TOKEN = _login(PY_PORT)
    h = {"Authorization": f"Bearer {PY_TOKEN}"}
    if extra_headers:
        h.update(extra_headers)
    try:
        r = requests.request(method, f"{PY_BASE}{path}", json=json_body,
                             headers=h, timeout=timeout)
        if "application/json" in r.headers.get("content-type", ""):
            return r.status_code, try_json(r.text)
        return r.status_code, r.text[:1000]
    except Exception as e:
        return -1, str(e)


def _fa(method: str, path: str, json_body: dict = None,
        extra_headers: dict = None, timeout: int = 15) -> tuple[int, dict | str]:
    """请求 Payara（8005），返回 (status, parsed_json_or_text)。"""
    global FA_TOKEN
    if not FA_TOKEN:
        FA_TOKEN = _login(FA_PORT)
    h = {"Authorization": f"Bearer {FA_TOKEN}"}
    if extra_headers:
        h.update(extra_headers)
    try:
        r = requests.request(method, f"{FA_BASE}{path}", json=json_body,
                             headers=h, timeout=timeout)
        if "application/json" in r.headers.get("content-type", ""):
            return r.status_code, try_json(r.text)
        return r.status_code, r.text[:1000]
    except Exception as e:
        return -1, str(e)


def try_json(s: str):
    try:
        return json.loads(s)
    except (json.JSONDecodeError, TypeError):
        return s


def _keys(obj, depth=3):
    """递归提取对象所有 key 路径。"""
    if depth == 0 or not isinstance(obj, dict):
        return set()
    ks = set(obj.keys())
    for v in obj.values():
        ks.update(_keys(v, depth - 1))
    return ks


def _deep_keys(obj, depth=4):
    """提取嵌套 key 路径如 'partIterations.author.name'。"""
    if depth == 0:
        return set()
    if isinstance(obj, dict):
        result = set()
        for k, v in obj.items():
            result.add(k)
            sub = _deep_keys(v, depth - 1)
            for s in sub:
                result.add(f"{k}.{s}")
        return result
    if isinstance(obj, list) and obj and isinstance(obj[0], dict):
        return _deep_keys(obj[0], depth - 1)
    return set()


# ── 端点定义 ──────────────────────────

# 格式: (method, path_template, description, json_body or None)
# 每阶段一个列表

def seed_and_collect() -> list:
    """创建种子数据并收集端点列表。"""
    global PY_TOKEN, FA_TOKEN
    PY_TOKEN = _login(PY_PORT)
    FA_TOKEN = _login(FA_PORT)
    if not PY_TOKEN:
        print("[WARN] 8000 login failed")
    if not FA_TOKEN:
        print("[WARN] 8005 login failed")

    stages = []

    # ── 阶段 1: 创建种子数据 ──
    s = seed
    stages.append(("创建种子数据", [
        ("POST", f"/workspaces/{WS}/parts", {"number": s["part_number"], "name": s["part_name"]}, "创建零件"),
        ("POST", f"/workspaces/{WS}/folders/{WS}/documents", {"reference": s["doc_id"], "title": s["doc_title"]}, "创建文档"),
        ("POST", f"/workspaces/{WS}/changes/issues", {"name": s["issue_name"]}, "创建Issue"),
        ("POST", f"/workspaces/{WS}/changes/requests", {"name": s["request_name"]}, "创建Request"),
        ("POST", f"/workspaces/{WS}/changes/orders", {"name": s["order_name"]}, "创建Order"),
        ("POST", f"/workspaces/{WS}/changes/milestones", {"title": s["milestone_title"]}, "创建Milestone"),
        ("POST", f"/workspaces/{WS}/workflow-models", {"id": s["wf_model_id"], "finalLifecycleState": "RELEASED", "activityModels": [{"step": 0, "type": "SEQUENTIAL", "tasksToComplete": 1, "tasks": [{"title": "Test Task", "instructions": "test", "role": {"name": "ROLE-TEST"}}]}]}, "创建WorkflowModel"),
        ("POST", f"/workspaces/{WS}/products", {"id": s["ci_id"], "designItemNumber": s["part_number"]}, "创建CI"),
        ("POST", f"/workspaces/{WS}/roles", {"name": s["role_name"]}, "创建Role"),
        ("POST", f"/workspaces/{WS}/groups", {"id": s["group_id"]}, "创建UserGroup"),
    ]))

    # ── 阶段 2: Auth ──
    stages.append(("Auth", [
        ("GET", "/auth/providers", None, "OAuth providers"),
        ("POST", "/auth/logout", None, "登出"),
        ("POST", "/auth/recover", {"login": "test1", "password": "password"}, "密码恢复"),
    ]))

    # ── 阶段 3: Workspace / Admin ──
    stages.append(("Workspace管理", [
        ("GET", f"/workspaces/{WS}", None, "工作区详情"),
        ("GET", f"/workspaces/{WS}/stats-overview", None, "统计总览"),
        ("GET", f"/workspaces/{WS}/disk-usage-stats", None, "磁盘用量"),
        ("GET", f"/workspaces/{WS}/users-stats", None, "用户统计"),
        ("GET", f"/workspaces/{WS}/front-options", None, "前端选项"),
        ("PUT", f"/workspaces/{WS}/front-options", {"partTableColumns": ["number", "name"]}, "保存前端选项"),
        ("GET", "/workspaces/more", None, "更多工作区"),
    ]))

    # ── 阶段 4: Parts ──
    pn = f'{s["part_number"]}-A'
    stages.append(("Parts零件", [
        ("GET", f"/workspaces/{WS}/parts", None, "零件列表"),
        ("GET", f"/workspaces/{WS}/parts/count", None, "零件计数"),
        ("GET", f"/workspaces/{WS}/parts/checkedout", None, "已签出"),
        ("GET", f"/workspaces/{WS}/parts/search?q={s['part_name']}", None, "搜索"),
        ("GET", f"/workspaces/{WS}/parts/{pn}", None, "零件详情"),
        ("PUT", f"/workspaces/{WS}/parts/{pn}/checkout", None, "签出"),
        ("PUT", f"/workspaces/{WS}/parts/{pn}/checkin", None, "签入"),
        ("PUT", f"/workspaces/{WS}/parts/{pn}/tags", {"tags": [{"label": TAG, "id": TAG}]}, "打标签"),
        ("GET", f"/workspaces/{WS}/parts/{pn}/aborted-workflows", None, "终止工作流"),
        ("GET", f"/workspaces/{WS}/parts/{pn}/instances", None, "装配实例"),
        ("GET", f"/workspaces/{WS}/parts/{pn}/baselines", None, "基线"),
        ("GET", f"/workspaces/{WS}/parts/{pn}/used-by-as-component", None, "被用作组件"),
        ("GET", f"/workspaces/{WS}/parts/{pn}/used-by-as-substitute", None, "被用作替代品"),
        ("GET", f"/workspaces/{WS}/part-templates", None, "零件模板"),
    ]))

    # ── 阶段 5: Documents ──
    dk = f'{s["doc_id"]}-A'
    stages.append(("Documents文档", [
        ("GET", f"/workspaces/{WS}/documents", None, "文档列表"),
        ("GET", f"/workspaces/{WS}/documents/count", None, "文档计数"),
        ("GET", f"/workspaces/{WS}/documents/checkedout", None, "已签出"),
        ("GET", f"/workspaces/{WS}/documents/search?q={s['doc_title']}", None, "搜索"),
        ("GET", f"/workspaces/{WS}/documents/{dk}", None, "文档详情"),
        ("PUT", f"/workspaces/{WS}/documents/{dk}/checkout", None, "签出"),
        ("PUT", f"/workspaces/{WS}/documents/{dk}/checkin", None, "签入"),
        ("GET", f"/workspaces/{WS}/documents/{dk}/aborted-workflows", None, "终止工作流"),
        ("GET", f"/workspaces/{WS}/document-templates", None, "文档模板"),
        ("GET", f"/workspaces/{WS}/folders", None, "文件夹列表"),
        ("GET", f"/workspaces/{WS}/document-baselines", None, "基线列表"),
    ]))

    # ── 阶段 6: Changes ──
    stages.append(("Changes变更", [
        ("GET", f"/workspaces/{WS}/changes/issues", None, "Issue列表"),
        ("GET", f"/workspaces/{WS}/changes/requests", None, "Request列表"),
        ("GET", f"/workspaces/{WS}/changes/orders", None, "Order列表"),
        ("GET", f"/workspaces/{WS}/changes/milestones", None, "里程碑"),
        ("GET", f"/workspaces/{WS}/changes/issues/link?q={s['issue_name']}", None, "Issue搜索"),
        ("GET", f"/workspaces/{WS}/changes/requests/link?q={s['request_name']}", None, "Request搜索"),
        ("GET", f"/workspaces/{WS}/changes/orders/link?q={s['order_name']}", None, "Order搜索"),
    ]))

    # ── 阶段 7: Products ──
    stages.append(("Products产品", [
        ("GET", f"/workspaces/{WS}/products", None, "CI列表"),
        ("GET", f"/workspaces/{WS}/products/{s['ci_id']}", None, "CI详情"),
        ("GET", f"/workspaces/{WS}/products/{s['ci_id']}/filter", None, "产品结构"),
        ("GET", f"/workspaces/{WS}/products/{s['ci_id']}/baselines", None, "基线"),
        ("GET", f"/workspaces/{WS}/products/{s['ci_id']}/configurations", None, "配置"),
        ("GET", f"/workspaces/{WS}/products/{s['ci_id']}/instances", None, "实例"),
        ("GET", f"/workspaces/{WS}/products/{s['ci_id']}/decode-path/{pn}", None, "路径解码"),
        ("GET", f"/workspaces/{WS}/product-configurations", None, "全局配置"),
        ("GET", f"/workspaces/{WS}/product-instances", None, "全局实例"),
    ]))

    # ── 阶段 8: Users / Groups / Roles ──
    stages.append(("Users用户管理", [
        ("GET", f"/workspaces/{WS}/users", None, "用户列表"),
        ("GET", f"/workspaces/{WS}/users/me", None, "当前用户"),
        ("GET", f"/workspaces/{WS}/users/admin", None, "管理员"),
        ("GET", f"/workspaces/{WS}/groups", None, "用户组"),
        ("GET", f"/workspaces/{WS}/memberships/users", None, "用户成员资格"),
        ("GET", f"/workspaces/{WS}/memberships/usergroups", None, "组成员资格"),
        ("GET", f"/workspaces/{WS}/roles", None, "角色"),
        ("GET", f"/workspaces/{WS}/roles/inuse", None, "在用角色"),
        ("GET", f"/workspaces/{WS}/user-group", None, "用户组列表(旧)"),
    ]))

    # ── 阶段 9: Workflow / Tasks ──
    stages.append(("Workflow工作流", [
        ("GET", f"/workspaces/{WS}/workflow-models", None, "模板列表"),
        ("GET", f"/workspaces/{WS}/workflow-models/{s['wf_model_id']}", None, "模板详情"),
        ("GET", f"/workspaces/{WS}/tasks/test1/assigned", None, "分配任务"),
        ("GET", f"/workspaces/{WS}/tasks/test1/documents", None, "任务文档"),
        ("GET", f"/workspaces/{WS}/tasks/test1/parts", None, "任务零件"),
    ]))

    # ── 阶段 10: Webhook / Notifications ──
    stages.append(("Webhook通知", [
        ("GET", f"/workspaces/{WS}/webhooks", None, "Webhook"),
        ("GET", f"/workspaces/{WS}/notifications", None, "通知"),
    ]))

    # ── 阶段 11: Accounts ──
    stages.append(("Accounts账号", [
        ("GET", "/accounts/me", None, "我的账号"),
        ("GET", "/accounts/workspaces", None, "我的工作区"),
    ]))

    # ── 阶段 12: Admin ──
    stages.append(("Admin管理", [
        ("GET", "/admin/accounts-stats", None, "账号统计"),
        ("GET", "/admin/workspace-stats", None, "工作区统计"),
        ("GET", "/admin/disk-usage-stats", None, "磁盘统计"),
    ]))

    # ── 阶段 13: Organizations / Misc / LoV / Attributes ──
    stages.append(("杂项", [
        ("GET", "/languages", None, "语言"),
        ("GET", "/timezones", None, "时区"),
        ("GET", "/platform/health", None, "健康检查"),
        ("GET", "/organizations", None, "组织"),
        ("GET", f"/workspaces/{WS}/lov", None, "值列表"),
        ("GET", f"/workspaces/{WS}/tags", None, "标签"),
        ("GET", f"/workspaces/{WS}/attributes/part-iterations", None, "零件属性"),
        ("GET", f"/workspaces/{WS}/attributes/path-data", None, "路径属性"),
    ]))

    # ── 阶段 14: 清理 ──
    stages.append(("清理种子数据", [
        ("DELETE", f"/workspaces/{WS}/parts/{pn}", None, "删零件"),
        ("DELETE", f"/workspaces/{WS}/documents/{dk}", None, "删文档"),
        # issue/request/order/milestone 需要 ID
        ("DELETE", f"/workspaces/{WS}/workflow-models/{s['wf_model_id']}", None, "删WF模板"),
        ("DELETE", f"/workspaces/{WS}/products/{s['ci_id']}", None, "删CI"),
        ("DELETE", f"/workspaces/{WS}/roles/{s['role_name']}", None, "删角色"),
        ("DELETE", f"/workspaces/{WS}/groups/{s['group_id']}", None, "删组"),
    ]))

    return stages


def run_full():
    """录 + 回放 + 对比。"""
    print("=" * 70)
    print("全端点双端对拍 v2")
    print(f"Payara (8005) vs FastAPI (8000) | Workspace: {WS} | Tag: {TAG}")
    print("=" * 70)

    stages = seed_and_collect()

    results = []
    total = 0
    match = 0
    partial = 0
    mismatch = 0
    errors = 0

    for stage_name, endpoints in stages:
        print(f"\n--- {stage_name} ({len(endpoints)} 端点) ---")
        for method, path, body, desc in endpoints:
            total += 1
            label = f"[{total:03d}] {method} {path[:70]}"

            # Payara
            fa_code, fa_data = _fa(method, path, body)
            time.sleep(0.05)
            # FastAPI
            py_code, py_data = _py(method, path, body)

            # 对比
            status_match = fa_code == py_code
            fa_keys = _deep_keys(fa_data) if isinstance(fa_data, dict) else set()
            py_keys = _deep_keys(py_data) if isinstance(py_data, dict) else set()
            missing_keys = fa_keys - py_keys
            extra_keys = py_keys - fa_keys

            if fa_code <= 0 or py_code <= 0:
                status = "⚠ERROR"
                errors += 1
            elif fa_code == 500 and py_code == 500:
                status = "✓BOTH500"
                match += 1
            elif status_match and not missing_keys:
                status = "✓MATCH"
                match += 1
            elif status_match and missing_keys:
                status = f"△PARTIAL (miss={len(missing_keys)}: {sorted(list(missing_keys))[:5]})"
                partial += 1
            else:
                status = f"✗MISMATCH FA={fa_code} PY={py_code}"
                if missing_keys:
                    status += f" miss={list(missing_keys)[:3]}"
                mismatch += 1

            print(f"  {status} | {desc}")
            results.append({
                "method": method, "path": path, "desc": desc,
                "fa_code": fa_code, "py_code": py_code,
                "missing_keys": sorted(list(missing_keys)),
                "extra_keys": sorted(list(extra_keys)),
                "status": status,
            })

    print(f"\n{'='*70}")
    print(f"SUMMARY: {total} total | {match} MATCH | {partial} PARTIAL | {mismatch} MISMATCH | {errors} ERROR")
    print(f"Match rate: {match/total*100:.1f}%")

    # 输出 mismatch/partial 详情
    print(f"\n{'='*70}")
    print("MISMATCH / PARTIAL 详情:")
    for r in results:
        if "MISMATCH" in r["status"] or "PARTIAL" in r["status"]:
            print(f"  [{r['method']}] {r['path']}")
            print(f"    FA={r['fa_code']} PY={r['py_code']} | {r['desc']}")
            if r["missing_keys"]:
                print(f"    缺字段: {r['missing_keys'][:8]}")
            if r["extra_keys"]:
                print(f"    多余字段: {r['extra_keys'][:8]}")

    # 保存完整报告
    report_path = Path("scripts/full_compare_report.json")
    report_path.parent.mkdir(exist_ok=True)
    with open(report_path, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\n报告已保存: {report_path}")


if __name__ == "__main__":
    run_full()

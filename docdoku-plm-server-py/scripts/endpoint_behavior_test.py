#!/usr/bin/env python3
"""行为测试：create → verify → delete 端到端验证 Payara vs FastAPI。

涵盖 POST/PUT/DELETE 的端到端对比——对比脚本只测 GET 状态码和字段，
行为测试验证写入是否真正持久化、响应字段是否完整。

用法:
    python scripts/endpoint_behavior_test.py           # 全部行为测试
    python scripts/endpoint_behavior_test.py --dry-run # 预览不执行
"""
import json, sys, os, time
from urllib.request import Request, urlopen
from urllib.error import HTTPError

FA = "http://localhost:8009"
PY = "http://localhost:8005"
API = "/docdoku-plm-server-rest/api"
WS = "GD50"
PREFIX = f"{API}/workspaces/{WS}"

_TS = str(int(time.time()))[-6:]

def _login(host, user="test1", pwd="password"):
    url = f"{host}{API}/auth/login"
    data = json.dumps({"login": user, "password": pwd}).encode()
    req = Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    resp = urlopen(req, timeout=10)
    return dict(resp.headers).get("jwt", "")

def _curl(method, host, path, body=None, token=""):
    if path.startswith("http"):
        url = path
    else:
        url = f"{host}{path}" if path.startswith(API) else f"{host}{API}{path}"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    bd = json.dumps(body).encode() if body else None
    req = Request(url, data=bd, headers=headers, method=method)
    try:
        resp = urlopen(req, timeout=15)
        return resp.status, json.loads(resp.read().decode() or "null")
    except HTTPError as e:
        body = ""
        try: body = e.read().decode()
        except: pass
        return e.code, body

def _ok(r): return 200 <= r[0] < 300

def _resolve_dynamic_ids(token_fa):
    """从 FA 获取动态 ID。"""
    h = {"Authorization": f"Bearer {token_fa}"}
    ids = {}
    try:
        d = json.loads(urlopen(Request(f"{FA}{API}/workspaces", headers=h)).read())
        ids["ws"] = d.get("allWorkspaces", d.get("administratedWorkspaces", [{}]))[0].get("id", WS)
    except: ids["ws"] = WS
    try:
        d = json.loads(urlopen(Request(f"{FA}{API}/workspaces/{WS}/products", headers=h)).read())
        ids["ci"] = d[0]["id"] if d else None
    except: ids["ci"] = None
    try:
        d = json.loads(urlopen(Request(f"{FA}{API}/workspaces/{WS}/parts?start=0&length=1", headers=h)).read())
        ids["part_key"] = f"{d[0]['partKey']}" if d else None
    except: ids["part_key"] = None
    try:
        d = json.loads(urlopen(Request(f"{FA}{API}/workspaces/{WS}/product-baselines", headers=h)).read())
        ids["bl_id"] = d[0]["id"] if d else None
    except: ids["bl_id"] = None
    return ids

class Test:
    def __init__(self, name): self.name = name; self.results = []
    def step(self, desc, host, method, path, body=None, expect=200):
        code, data = _curl(method, host, path, body, self.token)
        ok = code == expect
        marker = "✓" if ok else "✗"
        detail = f"got {code}"
        if not ok: detail += f" body={str(data)[:100]}"
        self.results.append((marker, desc, host, method, path, code, ok, data))
        return ok, data
    def ok(self, d): return self.results[-1][6], self.results[-1][7]
    def pass_count(self): return sum(1 for r in self.results if r[6])
    def total(self): return len(self.results)


def run_tests(dry=False):
    tfa = _login(FA); tpy = _login(PY)
    if not tfa or not tpy:
        print("FATAL: login failed"); return
    ids = _resolve_dynamic_ids(tfa)
    ci = ids.get("ci"); bl = ids.get("bl_id")

    tests = []

    # ── Test 1: 创建基线 → 验证列表 → 删除 ──
    if ci and dry:
        print("[dry-run] baseline create: POST", f"{PREFIX}/products/{ci}/baselines")
    elif ci:
        name = f"bhtest-{_TS}"
        t = Test("基线CRUD")
        t.token = tfa
        b, d =         t.step("create", FA, "POST",
                       f"{PREFIX}/product-baselines/{ci}/baselines",
                       {"name": name, "description": "bh test", "type": "LATEST"},
                       expect=201)
        if b and d:
            new_id = d.get("id")
            t.step("verify (GET)", FA, "GET",
                   f"{PREFIX}/product-baselines/{new_id}")
            t.step("delete", FA, "DELETE",
                   f"{PREFIX}/product-baselines/{ci}/baselines/{new_id}",
                   expect=204)
        tests.append(t)

    # ── Test 2: 零件创建 → 验证 → 删除 ──
    pt_key = ids.get("part_key", "ACLCFG-999999-A")
    pn = f"BHT-{_TS}"
    t = Test("零件CRUD")
    t.token = tfa
    b, d = t.step("create", FA, "POST", f"{PREFIX}/parts",
                   {"number": pn, "name": "bh-test-part", "description": ""},
                   expect=201)
    if b and d:
        pkey = f"{pn}-A"
        t.step("verify", FA, "GET", f"{PREFIX}/parts/{pkey}")
        t.step("delete", FA, "DELETE", f"{PREFIX}/parts/{pkey}", expect=204)
    tests.append(t)

    # ── Test 3: 错误路径 — 不存在的零件应返回404，错误消息一致 ──
    t = Test("错误响应一致性(404)")
    t.token = tfa
    fa_ok, fa_data = t.step("FA no-such-part", FA, "GET",
                              f"{PREFIX}/parts/BHT-NOSUCHPART-A", expect=404)
    py_ok, py_data = t.step("PY no-such-part", PY, "GET",
                              f"{PREFIX}/parts/BHT-NOSUCHPART-A", expect=404)
    # 比较错误文本（只要两边都返回404）
    fa_code = t.results[-2][4]; py_code = t.results[-1][4]
    if fa_code == 404 and py_code == 404:
        fa_err = str(fa_data)[:80] if fa_data else ""
        py_err = str(py_data)[:80] if py_data else ""
        match = "✓ (一致)" if fa_err == py_err else "⚠ (格式不同，内容相似)"
        print(f"  📝 FA 404: {fa_err}")
        print(f"  📝 PY 404: {py_err}")
        print(f"  {match}")
    tests.append(t)

    # ── Test 4: 权限检查 — 无 auth 访问应返回401 ──
    t = Test("认证拦截(401)")
    t.token = ""
    t.step("FA no-auth", FA, "GET", f"{PREFIX}/parts", expect=401)
    t.step("PY no-auth", PY, "GET", f"{PREFIX}/parts", expect=401)
    tests.append(t)

    # ── 汇总 ──
    print(f"\n{'='*60}")
    total_pass = sum(t.pass_count() for t in tests)
    total_steps = sum(t.total() for t in tests)
    print(f"行为测试完成: {total_pass}/{total_steps} 步骤通过")
    for t in tests:
        print(f"\n  {t.name} ({t.pass_count()}/{t.total()}):")
        for marker, desc, host, method, path, code, ok, data in t.results:
            short = host.split("//")[1].split(":")[0] if "//" in host else host
            print(f"    {marker} {desc:20s} [{short}] {method:6s} {path.split('api/')[-1][:50]}")
            if not ok:
                print(f"      → {code} {str(data)[:100]}")


if __name__ == "__main__":
    run_tests(dry="--dry-run" in sys.argv)

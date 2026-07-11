"""与 Payara 对拍：同一操作对比 FastAPI(:8000) 与 Payara(:8001) 响应。

用法: python scripts/compare_with_payara.py <path> [--login test1] [--password password]
示例: python scripts/compare_with_payara.py /workspaces/GD50/parts/Assem1-A
"""
import sys
import json
import argparse
import urllib.request

PREFIX = "/docdoku-plm-server-rest/api"


def login(base, login_name, password):
    req = urllib.request.Request(
        f"{base}{PREFIX}/auth/login",
        data=json.dumps({"login": login_name, "password": password}).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    resp = urllib.request.urlopen(req)
    return resp.headers.get("jwt")


def fetch(base, path, token):
    req = urllib.request.Request(
        f"{base}{PREFIX}{path}", headers={"Authorization": f"Bearer {token}"})
    try:
        resp = urllib.request.urlopen(req)
        return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def diff_keys(p, f, prefix=""):
    if isinstance(p, dict) and isinstance(f, dict):
        for k in sorted(set(p) | set(f)):
            diff_keys(p.get(k), f.get(k), f"{prefix}.{k}")
    elif p != f:
        print(f"  {prefix}: Payara={repr(p)[:60]} | FastAPI={repr(f)[:60]}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--login", default="test1")
    ap.add_argument("--password", default="password")
    args = ap.parse_args()

    token = login("http://localhost:8000", args.login, args.password)
    ps, pb = fetch("http://localhost:8001", args.path, token)
    fs, fb = fetch("http://localhost:8000", args.path, token)
    print(f"Status: Payara={ps} FastAPI={fs}")
    if isinstance(pb, dict) and isinstance(fb, dict):
        print("Field diffs:")
        diff_keys(pb, fb)
    else:
        print(f"Payara body: {str(pb)[:200]}")
        print(f"FastAPI body: {str(fb)[:200]}")


if __name__ == "__main__":
    main()

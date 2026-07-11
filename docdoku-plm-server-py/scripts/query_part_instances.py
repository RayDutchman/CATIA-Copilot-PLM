#!/usr/bin/env python3
"""
查询指定 workspace 中某个 PartMaster 的子 instances 信息。
输出每个子件的零件编号、平移量 (tx, ty, tz) 单位 mm、旋转角 (rx, ry, rz) 单位 rad。

使用方式：
    python3 query_part_instances.py <workspace_id> <part_number>

示例：
    python3 query_part_instances.py GD50 Assem1

可选环境变量：
    PLM_BASE_URL   服务地址，默认 http://localhost:8001/docdoku-plm-server-rest/api
    PLM_LOGIN      登录名，默认 test1
    PLM_PASSWORD   密码，默认 password
"""

import sys
import os
import math
import json
import urllib.parse
import urllib.request
import urllib.error


# ──────────────────────────────────────────────
# 配置
# ──────────────────────────────────────────────
BASE_URL  = os.environ.get("PLM_BASE_URL", "http://localhost:8001/docdoku-plm-server-rest/api")
LOGIN     = os.environ.get("PLM_LOGIN",    "test1")
PASSWORD  = os.environ.get("PLM_PASSWORD", "password")


def get_jwt_token(login: str, password: str) -> str:
    """登录并返回 JWT token。"""
    url = f"{BASE_URL}/auth/login"
    body = json.dumps({"login": login, "password": password}).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as resp:
            token = resp.headers.get("jwt") or resp.headers.get("JWT")
            if not token:
                print("错误：登录成功但响应头中没有 jwt 字段", file=sys.stderr)
                sys.exit(1)
            return token
    except urllib.error.HTTPError as e:
        print(f"错误：登录失败 HTTP {e.code}", file=sys.stderr)
        sys.exit(1)


def api_get(token: str, url: str) -> dict | list:
    """发送 GET 请求并返回解析后的 JSON。"""
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"错误：HTTP {e.code} — {url}\n{body}", file=sys.stderr)
        sys.exit(1)


def get_part_revision(token: str, workspace_id: str, part_number: str) -> dict:
    """
    获取零件最新版本的详情（含所有迭代和 cadInstances）。

    策略：
      1. 用 GET /parts?q={part_number} 搜索，筛选出 number 精确匹配的条目，
         取版本号字母序最大的一个。
      2. 用 partKey（格式 "{number}-{version}"）拼出详情 URL 请求完整数据。
    """
    ws_encoded = urllib.parse.quote(workspace_id, safe="")
    q_encoded  = urllib.parse.quote(part_number,  safe="")

    search_url = f"{BASE_URL}/workspaces/{ws_encoded}/parts?q={q_encoded}"
    results    = api_get(token, search_url)

    if not isinstance(results, list):
        print(f"错误：搜索接口返回格式异常", file=sys.stderr)
        sys.exit(1)

    # 精确匹配零件编号（搜索结果可能包含模糊匹配项）
    matched = [r for r in results if r.get("number") == part_number]
    if not matched:
        print(f"错误：在 {workspace_id} 中未找到零件编号为 '{part_number}' 的零件", file=sys.stderr)
        sys.exit(1)

    # 按版本字母序取最新版本
    latest = sorted(matched, key=lambda r: r.get("version", ""))[-1]
    part_key = latest.get("partKey")  # 格式："{number}-{version}"

    if not part_key:
        print("错误：搜索结果中缺少 partKey 字段", file=sys.stderr)
        sys.exit(1)

    # 请求版本详情（含 partIterations / components / cadInstances）
    part_key_encoded = urllib.parse.quote(part_key, safe="")
    detail_url = f"{BASE_URL}/workspaces/{ws_encoded}/parts/{part_key_encoded}"
    return api_get(token, detail_url)


def rotation_matrix_to_euler_xyz(m: list[float]) -> tuple[float, float, float]:
    """
    将 3x3 旋转矩阵（行主序，9个元素）转换为 XYZ 欧拉角（单位 rad）。
    约定：R = Rx * Ry * Rz（CATIA 内旋 XYZ 顺序）。

    矩阵布局（与 API 返回的 matrix[0..8] 对应）：
        | m[0]  m[1]  m[2] |
        | m[3]  m[4]  m[5] |
        | m[6]  m[7]  m[8] |
    """
    # R = Rx(rx) * Ry(ry) * Rz(rz)
    # m[6] = -sin(ry)
    # m[7] =  cos(ry)*sin(rx)
    # m[8] =  cos(ry)*cos(rx)
    # m[3] =  sin(rz)*cos(ry)  …（不用）
    # m[0] =  cos(rz)*cos(ry)  …（不用）
    m00, m01, m02 = m[0], m[1], m[2]
    m10, m11, m12 = m[3], m[4], m[5]
    m20, m21, m22 = m[6], m[7], m[8]

    # ry
    ry = math.asin(-max(-1.0, min(1.0, m20)))

    cos_ry = math.cos(ry)
    if abs(cos_ry) > 1e-6:
        rx = math.atan2(m21, m22)
        rz = math.atan2(m10, m00)
    else:
        # 万向锁：ry = ±90°，rx 与 rz 耦合，令 rx = 0
        rx = 0.0
        rz = math.atan2(-m01, m11)

    return rx, ry, rz


def format_near_zero(value: float, threshold: float = 1e-10) -> float:
    """
    将绝对值小于 threshold 的浮点数归零。
    前端直接显示 tx/ty = -9.8e-15 这类浮点噪声（显示为 -9.8367），
    实际上这些值的物理意义是 0，阈值 1e-10 mm 远小于任何工程精度。
    """
    return 0.0 if abs(value) < threshold else value


def print_instances(workspace_id: str, part_number: str):
    """主逻辑：查询并打印子 instance 信息。"""
    print(f"正在登录 {BASE_URL} ...")
    token = get_jwt_token(LOGIN, PASSWORD)

    print(f"正在获取 {workspace_id} / {part_number} 的数据...\n")
    data = get_part_revision(token, workspace_id, part_number)

    # 取最新版本的最后一个迭代
    iterations = data.get("partIterations") or []
    if not iterations:
        print("未找到任何迭代数据。")
        return

    last_iter = iterations[-1]
    version   = last_iter.get("version", "?")
    iteration = last_iter.get("iteration", "?")
    components = last_iter.get("components") or []

    print(f"零件：{part_number}  版本 {version}  迭代 {iteration}")
    print(f"子件数量：{len(components)}")
    print("=" * 80)

    if not components:
        print("（无子件）")
        return

    for comp in components:
        comp_info    = comp.get("component") or {}
        comp_number  = comp_info.get("number", "—")
        comp_name    = comp_info.get("name", "")
        cad_instances = comp.get("cadInstances") or []

        # 子件标题
        name_display = f"  ({comp_name})" if comp_name and comp_name != comp_number else ""
        print(f"\n  零件编号：{comp_number}{name_display}")
        print(f"  实例数量：{len(cad_instances)}")

        if not cad_instances:
            print("    （无位置数据）")
            continue

        for idx, inst in enumerate(cad_instances, start=1):
            rotation_type = inst.get("rotationType", "ANGLE")

            # 平移量（直接读取，单位 mm）
            tx = format_near_zero(inst.get("tx") or 0.0)
            ty = format_near_zero(inst.get("ty") or 0.0)
            tz = format_near_zero(inst.get("tz") or 0.0)

            # 旋转：MATRIX 模式下从矩阵反算欧拉角，ANGLE 模式下直接读取
            if rotation_type == "MATRIX":
                matrix = inst.get("matrix")
                if matrix and len(matrix) == 9:
                    rx, ry, rz = rotation_matrix_to_euler_xyz(matrix)
                    rx = format_near_zero(rx)
                    ry = format_near_zero(ry)
                    rz = format_near_zero(rz)
                else:
                    rx = ry = rz = 0.0
            else:
                rx = format_near_zero(inst.get("rx") or 0.0)
                ry = format_near_zero(inst.get("ry") or 0.0)
                rz = format_near_zero(inst.get("rz") or 0.0)

            print(f"    [{idx}] Translation (mm) : tx={tx:>12.4f}  ty={ty:>12.4f}  tz={tz:>12.4f}")
            print(f"         Rotation   (rad): rx={rx:>12.6f}  ry={ry:>12.6f}  rz={rz:>12.6f}")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"用法：python3 {sys.argv[0]} <workspace_id> <part_number>", file=sys.stderr)
        sys.exit(1)

    print_instances(workspace_id=sys.argv[1], part_number=sys.argv[2])

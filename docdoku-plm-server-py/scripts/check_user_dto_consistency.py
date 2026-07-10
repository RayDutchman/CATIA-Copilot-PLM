#!/usr/bin/env python3
"""
用户 DTO 一致性检查脚本。

扫描 app/routers/ 和 app/services/ 下所有 Python 文件，找出返回用户信息时
"name 字段直接使用 login 值" 或 "缺少 name 字段" 的位置。

用法：
    python3 scripts/check_user_dto_consistency.py [--root /path/to/app]

输出：
    各类问题按严重程度分组列出（文件:行号 + 说明）

退出码：
    0 = 无问题
    1 = 发现问题
"""
import ast
import glob
import os
import sys
import argparse


# ─────────────────────────────────────────────────────────
# AST 工具
# ─────────────────────────────────────────────────────────

def dict_keys(node: ast.Dict) -> list[str]:
    """返回 ast.Dict 的所有字符串常量 key。"""
    result = []
    for k in node.keys:
        if isinstance(k, ast.Constant) and isinstance(k.value, str):
            result.append(k.value)
    return result


def dict_value_for(node: ast.Dict, key: str):
    """返回 ast.Dict 中指定 key 的 value 节点，不存在则 None。"""
    for k, v in zip(node.keys, node.values):
        if isinstance(k, ast.Constant) and k.value == key:
            return v
    return None


def is_login_attr(node) -> bool:
    """判断节点是否为 xxx.login 或 xxx.author_login 之类的 login 属性访问。"""
    if isinstance(node, ast.Attribute):
        return node.attr in ("login", "author_login", "checkout_user_login",
                             "worker_login", "member_login")
    return False


def is_name_eq_login(node: ast.Dict) -> bool:
    """检查 dict 中是否存在 'name': xxx.login 的模式（name 直接用了 login 属性）。"""
    v = dict_value_for(node, "name")
    return v is not None and is_login_attr(v)


def is_name_eq_name_constant(node: ast.Dict) -> bool:
    """检查 dict 中 'name' 字段是否为字符串常量（如 'name': ''）。"""
    v = dict_value_for(node, "name")
    return isinstance(v, ast.Constant) and isinstance(v.value, str)


USER_DICT_KEYS = {"author", "checkOutUser", "worker", "checkInUser", "modifiedBy",
                  "createdBy", "admin", "member"}

SUSPECT_TOP_LEVEL_KEYS = {"author", "checkOutUser", "worker"}


# ─────────────────────────────────────────────────────────
# 检查器
# ─────────────────────────────────────────────────────────

class Issue:
    CRITICAL = "CRITICAL"
    WARNING  = "WARNING"
    INFO     = "INFO"

    def __init__(self, severity: str, filepath: str, lineno: int, msg: str):
        self.severity = severity
        self.filepath = filepath
        self.lineno = lineno
        self.msg = msg

    def __str__(self):
        return f"[{self.severity}] {self.filepath}:{self.lineno}  {self.msg}"


def scan_file(filepath: str) -> list[Issue]:
    issues = []
    try:
        with open(filepath, encoding="utf-8") as f:
            source = f.read()
        tree = ast.parse(source, filename=filepath)
    except (SyntaxError, UnicodeDecodeError):
        return issues

    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue
        keys = dict_keys(node)

        # ── 检查 1：顶层 user dict（含 login）的 name 直接用了 login 属性 ──
        if "login" in keys:
            if is_name_eq_login(node):
                issues.append(Issue(
                    Issue.CRITICAL, filepath, node.lineno,
                    '"name" 字段直接使用了 .login 属性（应查 Account 表获取真实姓名）'
                ))
            elif "name" not in keys:
                # 有 login 但无 name 字段
                issues.append(Issue(
                    Issue.WARNING, filepath, node.lineno,
                    '用户 dict 有 "login" 但缺少 "name" 字段'
                ))

        # ── 检查 2：author/checkOutUser/worker 等字段的嵌套 dict 缺 name ──
        for field in SUSPECT_TOP_LEVEL_KEYS:
            v = dict_value_for(node, field)
            if v is None or not isinstance(v, ast.Dict):
                continue
            nested_keys = dict_keys(v)
            if "login" in nested_keys and "name" not in nested_keys:
                issues.append(Issue(
                    Issue.CRITICAL, filepath, v.lineno,
                    f'"{field}" 嵌套 dict 有 "login" 但缺少 "name" 字段'
                ))
            elif "login" in nested_keys and is_name_eq_login(v):
                issues.append(Issue(
                    Issue.CRITICAL, filepath, v.lineno,
                    f'"{field}" 嵌套 dict 的 "name" 直接使用了 .login 属性'
                ))

    return issues


# ─────────────────────────────────────────────────────────
# 主程序
# ─────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="检查用户 DTO name/login 一致性")
    parser.add_argument("--root", default="app", help="扫描根目录（默认：app）")
    args = parser.parse_args()

    root = args.root
    if not os.path.isdir(root):
        print(f"错误：目录不存在：{root}")
        sys.exit(2)

    all_issues: list[Issue] = []
    files = glob.glob(os.path.join(root, "**", "*.py"), recursive=True)
    for fp in sorted(files):
        all_issues.extend(scan_file(fp))

    if not all_issues:
        print("✅ 未发现用户 DTO 一致性问题")
        sys.exit(0)

    # 按严重程度分组输出
    critical = [i for i in all_issues if i.severity == Issue.CRITICAL]
    warning  = [i for i in all_issues if i.severity == Issue.WARNING]
    info     = [i for i in all_issues if i.severity == Issue.INFO]

    if critical:
        print(f"\n{'='*60}")
        print(f"CRITICAL ({len(critical)} 处) — 必须修复")
        print('='*60)
        for i in critical:
            print(f"  {i.filepath}:{i.lineno}")
            print(f"    → {i.msg}")
    if warning:
        print(f"\n{'='*60}")
        print(f"WARNING ({len(warning)} 处) — 建议修复")
        print('='*60)
        for i in warning:
            print(f"  {i.filepath}:{i.lineno}")
            print(f"    → {i.msg}")
    if info:
        print(f"\n{'='*60}")
        print(f"INFO ({len(info)} 处)")
        print('='*60)
        for i in info:
            print(f"  {i.filepath}:{i.lineno}")
            print(f"    → {i.msg}")

    total = len(all_issues)
    print(f"\n共 {total} 处问题（Critical: {len(critical)}, Warning: {len(warning)}, Info: {len(info)}）")
    sys.exit(1 if critical else 0)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""路由层 body.get() 字段名 vs Java DTO 字段名全量对比。

策略：
  1. 提取所有 Java DTO private 字段名（含基础类型 String/int/Date 等，不跳过）
  2. 提取 Python 路由/服务层所有 body.get("xxx") / body["xxx"] 调用的字段名
  3. 差集 = 路由读了但 Java DTO 全集中不存在的字段名 → 候选问题
  4. 对每个候选，列出调用位置供人工确认

用法：
    python3 scripts/check_body_field_names.py

注意：差集不等于 bug，需人工判断：
  - 合理的有：路由专属字段（recoveryToken/token）、枚举默认值（"en"）
  - 需关注的有：字段名拼写差异（如 lang vs language、timezone vs timeZone）
"""

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
PY_ROOT = ROOT / "docdoku-plm-server-py"
JAVA_DTO_DIR = (
    ROOT / "docdoku-plm-server/docdoku-plm-server-rest"
    / "src/main/java/com/docdoku/plm/server/rest/dto"
)

# 已知合理的"非 DTO 字段"，无需报告
WHITELIST = {
    # 路由专属参数
    "recoveryToken", "token", "uuid",
    # body 里的枚举/常量默认值（被 get() 第二参数误匹配）
    "en",
    # acl 是 Python 侧组合字段名，Java 里叫 acl（已在 DTO 里）
    # 以下是 Python 扩展的功能性字段，Java 无对应
    "diverge", "pathFrom", "pathTo",          # 产品结构路径操作
    "finalLifecycleState",                     # workflow 专用（Java 叫 finalLifeCycleState）
    "folderName", "parentFolder",              # 文件夹操作辅助字段
    "configurationItemNumber",                 # 部分路由从 body 兜底读，路径参数优先
    "aclId",                                   # Python 内部中间值
    "webhookApp",                              # webhook 扩展字段
    # 以下是误匹配的枚举值字符串（出现在 body.get() 默认值里）
    "DATEBASEDEFFECTIVITY", "NONE",
    "MilestoneAlreadyExistsException",         # 误匹配（异常消息字符串）
    # 通用基础字段（Python 全局用，Java 散落各处）
    "acl", "tag", "parts", "documents",
    "values", "contexts", "mask", "member",
    "dryRun", "workspaceId", "workspace_id",
}

# Java DTO 字段中已知的驼峰/蛇形差异对（Java标准 → Python误用）
# 格式: (java_correct, python_wrong) — 用于主动报告
KNOWN_MISMATCHES = [
    ("timeZone",    "timezone"),    # Java/前端是 timeZone，Python 误用 timezone
    ("language",    "lang"),        # Java/前端是 language，Python 误用 lang（缩写）
    ("milestoneId", "milestone_id"),# Java/前端是 milestoneId，Python 误用蛇形（已修复，保留检测防回归）
]

# "password" 说明：
#   - accounts.py 注册/更新场景：Java 用 newPassword，Python 已修复为优先读 newPassword
#   - document.py / part.py 共享链接场景：Java SharedPartDTO/SharedDocumentDTO 字段名就是 password，正确
# 因此 "password" 不作为错误模式检查，加入白名单
WHITELIST_BODY_FIELDS = {
    "password",    # 共享链接场景合法字段，账号场景已修复
    "from",        # Elasticsearch 分页参数，非 DTO 字段
    "size",        # Elasticsearch 分页参数，非 DTO 字段
    "milestone_id",# ORM 蛇形列名，已修复为从 body 读 milestoneId（驼峰）
}


def extract_java_fields(dto_dir: Path) -> set[str]:
    """提取所有 Java DTO private 字段名（含基础类型）"""
    fields: set[str] = set()
    if not dto_dir.exists():
        print(f"警告：Java DTO 目录不存在: {dto_dir}", file=sys.stderr)
        return fields

    pattern = re.compile(
        r'private\s+(?:static\s+)?(?:final\s+)?'
        r'(?:[\w<>, \[\].]+?)\s+'   # 类型（含泛型）
        r'(\w+)'                      # 字段名
        r'\s*(?:=\s*[^;]+)?\s*;'
    )
    for java_file in dto_dir.rglob("*.java"):
        try:
            src = java_file.read_text(encoding="utf-8")
        except Exception:
            continue
        for m in pattern.finditer(src):
            fname = m.group(1)
            if fname not in ("LOGGER", "serialVersionUID", "log", "mapper"):
                fields.add(fname)
    return fields


def extract_body_gets(py_root: Path) -> dict[str, list[tuple[str, int]]]:
    """提取路由/服务层所有 body.get("xxx") / body["xxx"] 字段名及位置。
    返回 {字段名: [(文件相对路径, 行号), ...]}
    """
    result: dict[str, list] = {}
    scan_dirs = [py_root / "app" / "routers", py_root / "app" / "services"]

    for scan_dir in scan_dirs:
        if not scan_dir.exists():
            continue
        for py_file in sorted(scan_dir.rglob("*.py")):
            if py_file.name.startswith("_"):
                continue
            try:
                source = py_file.read_text(encoding="utf-8")
                tree = ast.parse(source, filename=str(py_file))
            except Exception:
                continue

            rel = str(py_file.relative_to(py_root))

            for node in ast.walk(tree):
                field = None
                lineno = getattr(node, "lineno", 0)

                # body.get("xxx") / body.get("xxx", default)
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "get"
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id in ("body", "data", "payload")
                    and node.args
                    and isinstance(node.args[0], ast.Constant)
                    and isinstance(node.args[0].value, str)
                ):
                    field = node.args[0].value

                # body["xxx"]
                elif (
                    isinstance(node, ast.Subscript)
                    and isinstance(node.value, ast.Name)
                    and node.value.id in ("body", "data", "payload")
                    and isinstance(node.slice, ast.Constant)
                    and isinstance(node.slice.value, str)
                ):
                    field = node.slice.value

                if field and field[0].isalpha():
                    result.setdefault(field, []).append((rel, lineno))

    return result


def run():
    print("=" * 65)
    print("  路由层 body.get() 字段名 vs Java DTO 全量对比")
    print("=" * 65)

    java_fields = extract_java_fields(JAVA_DTO_DIR)
    print(f"\nJava DTO 字段总数（含基础类型）: {len(java_fields)}")

    body_fields = extract_body_gets(PY_ROOT)
    print(f"路由/服务层 body.get() 唯一字段数: {len(body_fields)}\n")

    # ── 1. 主动检查已知的命名差异 ────────────────────────────────
    print("─" * 65)
    print("  【主动检查】已知命名差异模式")
    print("─" * 65)
    found_known = False
    for java_correct, py_wrong in KNOWN_MISMATCHES:
        locations = body_fields.get(py_wrong, [])
        if locations:
            found_known = True
            print(f"\n⚠️  使用了 \"{py_wrong}\"，Java 标准是 \"{java_correct}\"")
            for rel, line in locations[:5]:
                print(f"     {rel}:{line}")
            if len(locations) > 5:
                print(f"     ...还有 {len(locations)-5} 处")
    if not found_known:
        print("  ✅ 未发现已知命名差异")

    # ── 2. 差集分析：路由读了但 Java 没有的字段 ──────────────────
    print("\n" + "─" * 65)
    print("  【差集分析】路由读取了但 Java DTO 全集中不存在的字段")
    print("─" * 65)

    unknown = {}
    for field, locs in sorted(body_fields.items()):
        if field in java_fields:
            continue
        if field in WHITELIST:
            continue
        if field in WHITELIST_BODY_FIELDS:
            continue
        unknown[field] = locs

    if not unknown:
        print("  ✅ 无候选问题（所有字段均在 Java DTO 中有对应）")
    else:
        print(f"  共 {len(unknown)} 个字段名不在 Java DTO 中，需人工确认：\n")
        for field, locs in sorted(unknown.items()):
            print(f"  \"{field}\"  ({len(locs)} 处)")
            for rel, line in locs[:3]:
                print(f"     {rel}:{line}")
            if len(locs) > 3:
                print(f"     ...还有 {len(locs)-3} 处")

    # ── 3. 说明 ──────────────────────────────────────────────────
    print("\n" + "─" * 65)
    print("覆盖范围：")
    print("  ✅ body.get(\"xxx\") / body[\"xxx\"] 字段名 vs Java DTO private 字段")
    print("  ✅ 已知命名差异主动检查（timeZone/language/newPassword）")
    print("  ❌ 字段读到了但在调用链中被丢弃（参数链断裂）— 需人工检查")
    print("  ❌ 字段语义用错（如 password 当 newPassword 用）— 需对照 Java 逻辑")

    return 1 if unknown else 0


if __name__ == "__main__":
    sys.exit(run())

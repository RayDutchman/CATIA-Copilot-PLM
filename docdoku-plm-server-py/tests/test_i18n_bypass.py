"""检测所有 Python 文件中硬编码中文/英文字符串绕过 i18n 的情况。

规则：
- raise HTTPException(status_code=..., detail=f"中文") → 必须使用 ApplicationException 子类 + i18n key
- raise HTTPException(status_code=..., detail=f"English") → 同上
- 例外：WebSocket 路径、URL 常量、f-string 中仅含变量名
"""

import ast
import os
import re
from pathlib import Path

APP_DIR = Path(__file__).parent.parent / "app"
EXCEPT_DIRS = {"__pycache__", ".git", "venv", "node_modules"}

# 已知 i18n exception 子类名（通过继承 ApplicationException 间接判断）
# 以及已知会用 HTTPException 但不违反 i18n 的场景
LEGIT_EXCEPTION_NAMES = {
    "ApplicationException", "AccessRightException", "NotAllowedException",
    "EntityConstraintException", "EntityNotFoundException",
    "EntityAlreadyExistsException", "CreationException",
    "WorkspaceNotEnabledException", "UserNotFoundException",
    "PartMasterNotFoundException", "PartRevisionNotFoundException",
    "PartIterationNotFoundException", "ConfigurationItemNotFoundException",
    "WorkspaceNotFoundException", "SharedEntityNotFoundException",
    "PlatformHealthException",
}

# 允许的 HTTPException 使用场景（非 i18n 违规）
ALLOWED_HTTP_PATTERNS = [
    r"未提供认证 token",
    r"token 无效或已过期",
    r"账号不存在或已禁用",
    r"Invalid.*key format",
    r"Method Not Allowed",
]


def _has_cjk(text: str) -> bool:
    """检测是否包含中文字符。"""
    return bool(re.search(r"[\u4e00-\u9fff]", text))


def _is_i18n_bypass(raise_call: str, detail: str) -> bool:
    """判断 HTTPException raise 是否绕过了 i18n。"""
    if _has_cjk(detail) or any(
        detail.strip().startswith(p) for p in ("Part ", "Iteration ", "Cannot ", "Access ", "Folder ", "Document ", "File ", "Configuration ")
    ):
        for pat in ALLOWED_HTTP_PATTERNS:
            if re.search(pat, detail):
                return False
        return True
    return False


def _extract_detail_arg(node, source: str) -> str | None:
    """从 AST HTTPException 调用中提取 detail 参数值。"""
    for kw in node.keywords:
        if kw.arg == "detail":
            if isinstance(kw.value, ast.Constant):
                return str(kw.value.value)
            elif isinstance(kw.value, ast.JoinedStr):
                parts = []
                for v in kw.value.values:
                    if isinstance(v, ast.Constant):
                        parts.append(str(v.value))
                    elif isinstance(v, ast.FormattedValue):
                        parts.append("{}")
                return "".join(parts)
    return None


def find_i18n_bypasses(path: Path) -> list[dict]:
    """扫描单个 Python 文件，返回硬编码 HTTPException 列表。"""
    findings = []
    source = path.read_text(encoding="utf-8")

    # 方法 1: AST 解析
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return findings

    for node in ast.walk(tree):
        if isinstance(node, ast.Raise):
            exc = node.exc
            if isinstance(exc, ast.Call):
                if isinstance(exc.func, ast.Name) and exc.func.id == "HTTPException":
                    detail = _extract_detail_arg(exc, source)
                    if detail and _is_i18n_bypass(source, detail):
                        findings.append({
                            "file": str(path.relative_to(APP_DIR.parent)),
                            "line": node.lineno,
                            "detail": detail[:80],
                        })

    # 方法 2: 补充 grep——检测 ApplicationException 子类但传了硬编码英文消息
    for i, line in enumerate(source.split("\n"), 1):
        m = re.search(r'raise\s+HTTPException\([^)]*detail\s*=\s*["\']([^"\']{3,})', line)
        if m:
            detail = m.group(1)
            if _has_cjk(detail) and not any(re.search(p, detail) for p in ALLOWED_HTTP_PATTERNS):
                # 避免重复（AST 已发现）
                if not any(f["line"] == i for f in findings):
                    findings.append({
                        "file": str(path.relative_to(APP_DIR.parent)),
                        "line": i,
                        "detail": detail[:80],
                    })

    return findings


def test_no_i18n_bypass_in_services():
    """所有 service 文件不应绕过 i18n 使用硬编码 HTTPException。"""
    all_findings = []
    for root, dirs, files in os.walk(APP_DIR):
        dirs[:] = [d for d in dirs if d not in EXCEPT_DIRS]
        for f in files:
            if f.endswith(".py") and not f.startswith("__"):
                all_findings.extend(find_i18n_bypasses(Path(root) / f))

    assert all_findings == [], (
        f"发现 {len(all_findings)} 处 i18n bypass:\n" +
        "\n".join(f"  {f['file']}:{f['line']} — {f['detail'][:60]}" for f in all_findings)
    )

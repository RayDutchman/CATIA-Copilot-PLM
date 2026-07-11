#!/usr/bin/env python3
"""检查 service 层是否使用了硬编码 HTTPException，应改用 app.core.exceptions 自定义异常。

使用方式：
    python scripts/check_hardcoded_exceptions.py            # 仅检查 app/services/
    python scripts/check_hardcoded_exceptions.py --all      # 检查全部 app/（含 routers）
"""

import ast
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
APP_DIR = Path(__file__).resolve().parents[1] / "app"

# 异常→状态码映射（对齐 exception_handlers.py）
EXCEPTION_MAP_404 = {
    "ConfigItem":     "ConfigurationItemNotFoundException",
    "User":           "UserNotFoundException",
    "Account":        "AccountNotFoundException",
    "PartMaster":     "PartMasterNotFoundException",
    "PartRevision":   "PartRevisionNotFoundException",
    "PartIteration":  "PartIterationNotFoundException",
    "Document":       "DocumentRevisionNotFoundException",
    "BinaryResource": "FileNotFoundException",
    "File":           "FileNotFoundException",
    "Folder":         "FolderNotFoundException",
    "Template":       "DocumentMasterTemplateNotFoundException",
    "Workspace":      "WorkspaceNotFoundException",
    "Workflow":       "WorkflowNotFoundException",
    "Tag":            "TagNotFoundException",
    "Path":           "PathDataMasterNotFoundException",
    "Baseline":       "BaselineNotFoundException",
    "Change":         "ChangeIssueNotFoundException",
    "Milestone":      "MilestoneNotFoundException",
    "Organization":   "OrganizationNotFoundException",
    "Role":           "RoleNotFoundException",
    "Task":           "TaskNotFoundException",
}

EXCEPTION_MAP_403 = (
    "AccessRightException", "NotAllowedException",
)
EXCEPTION_MAP_409 = "EntityAlreadyExistsException"
EXCEPTION_MAP_400 = "WrongInputException"
EXCEPTION_MAP_500 = "ApplicationException"


def _keyword_hint(msg: str) -> str | None:
    """从异常消息中提取关键字，匹配已知 NotFoundException。"""
    lower = msg.lower().replace("_", " ")
    for keyword, exc_name in EXCEPTION_MAP_404.items():
        if keyword.lower() in lower:
            return exc_name
    return None


def _suggest(status_code: int, msg: str) -> str:
    """根据状态码和消息推荐自定义异常类名。"""
    if status_code == 404:
        hint = _keyword_hint(msg)
        if hint:
            return hint
        return "EntityNotFoundException（或对应的子类）"
    if status_code == 403:
        return f"{EXCEPTION_MAP_403[0]} / {EXCEPTION_MAP_403[1]}"
    if status_code == 409:
        return EXCEPTION_MAP_409
    if status_code == 400:
        return EXCEPTION_MAP_400
    if status_code == 500:
        return EXCEPTION_MAP_500
    return "（手动确认）"


class HTTPExceptionFinder(ast.NodeVisitor):
    """AST 遍历器：查找 raise HTTPException(...) 调用。"""

    def __init__(self, filename: str):
        self.filename = filename
        self.violations: list[dict] = []

    def visit_Raise(self, node: ast.Raise):
        exc = node.exc
        if isinstance(exc, ast.Call):
            func = exc.func
            if isinstance(func, ast.Name) and func.id == "HTTPException":
                # 提取参数：HTTPException(xxx) 或 HTTPException(status_code=xxx, detail=...)
                args = exc.args
                keywords = {kw.arg: kw.value for kw in exc.keywords}

                code = None
                detail = ""

                # 位置参数模式: HTTPException(404, "msg")
                if len(args) >= 1 and isinstance(args[0], ast.Constant):
                    code = args[0].value
                if len(args) >= 2 and isinstance(args[1], ast.Constant):
                    detail = args[1].value

                # 关键字参数模式: HTTPException(status_code=404, detail="msg")
                if "status_code" in keywords:
                    kw_code = keywords["status_code"]
                    if isinstance(kw_code, ast.Constant):
                        code = kw_code.value
                if "detail" in keywords:
                    kw_detail = keywords["detail"]
                    if isinstance(kw_detail, ast.Constant):
                        detail = kw_detail.value

                self.violations.append({
                    "file": self.filename,
                    "line": node.lineno,
                    "status_code": code,
                    "detail": detail,
                })
        self.generic_visit(node)


def scan_directory(path: Path) -> list[dict]:
    """扫描目录下所有 .py 文件中的硬编码 HTTPException。"""
    all_violations = []
    for pyfile in sorted(path.rglob("*.py")):
        if pyfile.name.startswith("__"):
            continue
        content = pyfile.read_text(encoding="utf-8")
        try:
            tree = ast.parse(content, filename=str(pyfile))
        except SyntaxError:
            continue
        finder = HTTPExceptionFinder(str(pyfile.relative_to(REPO_ROOT)))
        finder.visit(tree)
        all_violations.extend(finder.violations)
    return all_violations


def main():
    scan_all = "--all" in sys.argv

    if scan_all:
        dirs = [APP_DIR]
        label = "app/"
    else:
        dirs = [APP_DIR / "services"]
        label = "app/services/"

    all_violations = []
    for d in dirs:
        if d.is_dir():
            all_violations.extend(scan_directory(d))

    if not all_violations:
        print(f"✅ {label} 下未发现硬编码 HTTPException。")
        return 0

    print(f"❌ {label} 下发现 {len(all_violations)} 处置编码 HTTPException：\n")
    for v in all_violations:
        suggestion = _suggest(v["status_code"], v["detail"])
        code_str = f"HTTP {v['status_code']}" if v["status_code"] else "???"
        detail_str = v["detail"] or "(动态内容，无法静态提取)"
        print(f"  📄 {v['file']}:{v['line']}")
        print(f"     代码: {code_str}  detail: {detail_str[:80]}")
        print(f"     建议: raise {suggestion}(...)")
        print()

    return 1


if __name__ == "__main__":
    sys.exit(main())

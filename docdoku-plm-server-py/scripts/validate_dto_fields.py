#!/usr/bin/env python3
"""Pydantic Schema → Java DTO 字段对齐 v2 —— 增强版。

改进:
- Java DTO 解析: 处理注解、List/数组、默认值、@JsonbProperty别名
- 递归嵌套 DTO 检查 (如 ComponentDTO.cadInstances.*.matrix)
- 区分请求/响应 DTO 误匹配

用法:
    python3 scripts/validate_dto_fields.py
"""

import ast
import re
import sys
from collections import defaultdict
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent / "app"
SCHEMAS_DIR = APP_DIR / "schemas"
PAYARA_DTO_DIR = Path(__file__).resolve().parent.parent.parent / \
    "docdoku-plm-server/docdoku-plm-server-rest/src/main/java/com/docdoku/plm/server/rest/dto"

# ── 配置 ──────────────────────────────────────────

# 手工映射: Python schema → Java DTO (名称差异大的)
MANUAL_MAP: dict[str, str] = {
    "PartCreationDTO": "PartCreationDTO",
    "PartRevisionDTO": "PartRevisionDTO",
    "PartIterationDTO": "PartIterationDTO",
    "PartIterationUpdateDTO": "PartIterationDTO",
    "LoginRequestDTO": None,
    "ConversionResultDTO": "ConversionResultDTO",
    "CADInstanceDTO": "CADInstanceDTO",
    "ComponentDTO": "ComponentDTO",
    "PartUsageLinkDTO": "PartUsageLinkDTO",
    "LightPartMasterDTO": "LightPartMasterDTO",
    "LightPartLinkDTO": "LightPartLinkDTO",
    "ConfigurationItemDTO": "ConfigurationItemDTO",
    "ProductInstanceDTO": "ProductInstanceDTO",
    "ProductInstanceIterationDTO": "ProductInstanceIterationDTO",
    "DocumentRevisionDTO": "DocumentRevisionDTO",
    "DocumentIterationDTO": "DocumentIterationDTO",
    "DocumentCreationDTO": "DocumentCreationDTO",
    "ChangeIssueDTO": "ChangeIssueDTO",
    "ChangeRequestDTO": "ChangeRequestDTO",
    "ChangeOrderDTO": "ChangeOrderDTO",
    "MilestoneDTO": "MilestoneDTO",
    "TaskDTO": "TaskDTO",
    "WorkflowDTO": "WorkflowDTO",
    "RoleDTO": "RoleDTO",
    "UserDTO": "UserDTO",
    "AccountDTO": "AccountDTO",
    "WorkspaceDTO": "WorkspaceDTO",
    "PathDataMasterDTO": "PathDataMasterDTO",
    "PathDataIterationDTO": "PathDataIterationDTO",
    "PathToPathLinkDTO": "PathToPathLinkDTO",
    "PartMasterTemplateDTO": "PartMasterTemplateDTO",
    "EffectivityDTO": "EffectivityDTO",
    "BaselinedPartDTO": "BaselinedPartDTO",
    "BaselinedDocumentDTO": "BaselinedDocumentDTO",
    "ProductBaselineDTO": "ProductBaselineDTO",
    "DocumentBaselineDTO": "DocumentBaselineDTO",
    "ModificationNotificationDTO": "ModificationNotificationDTO",
    "QueryDTO": "QueryDTO",
    "ImportDTO": "ImportDTO",
    "WorkspaceUserMembershipDTO": "WorkspaceUserMembershipDTO",
    "WebhookDTO": "WebhookDTO",
    "TagDTO": "TagDTO",
    "LayerDTO": "LayerDTO",
    "MarkerDTO": "MarkerDTO",
}

# Request-only DTOs: Python schema 包含 response 字段不算 bug
REQUEST_ONLY: set[str] = {
    "PartCreationDTO", "DocumentCreationDTO",
    "ProductBaselineCreationDTO", "DocumentBaselineCreationDTO",
    "ProductInstanceCreationDTO", "WorkspaceWorkflowCreationDTO",
    "PartIterationUpdateDTO",
}

# Python 独有字段（如 workspace_id 从路由参数推导），忽略
PY_ONLY = {"workspace_id", "workspaceId", "configurationItemId",
           "configurationItemKey", "acl", "id", "extra"}

PYDANTIC_INTERNAL = {"model_config", "model_fields", "model_computed_fields"}


# ── 步骤 1: 解析 Pydantic schema ──

def parse_all_pydantic() -> dict[str, tuple[dict[str, str], str, str, set[str]]]:
    """返回 {类名: ({字段→alias}, 文件路径, extra_mode, {嵌套schema引用})}"""
    result: dict = {}
    for pyfile in SCHEMAS_DIR.rglob("*.py"):
        if pyfile.name.startswith("_"):
            continue
        try:
            source = pyfile.read_text(encoding="utf-8")
        except Exception:
            continue
        tree = ast.parse(source, filename=str(pyfile))
        for node in ast.iter_child_nodes(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            fields, extra_mode, deps = {}, "forbid", set()
            for item in ast.iter_child_nodes(node):
                # model_config
                if isinstance(item, ast.Assign):
                    if isinstance(item.targets[0], ast.Name) and item.targets[0].id == "model_config":
                        if isinstance(item.value, ast.Call):
                            for kw in item.value.keywords:
                                if kw.arg == "extra" and isinstance(kw.value, ast.Constant):
                                    extra_mode = kw.value.value
                # annotated assign
                if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                    fname = item.target.id
                    if fname in PYDANTIC_INTERNAL:
                        continue
                    alias = fname
                    if item.value and isinstance(item.value, ast.Call):
                        for kw in item.value.keywords:
                            if kw.arg == "alias" and isinstance(kw.value, ast.Constant):
                                alias = kw.value.value
                    fields[fname] = alias
                    # 追踪嵌套 DTO 引用
                    ann = item.annotation
                    if isinstance(ann, ast.Name):
                        deps.add(ann.id)
                    elif isinstance(ann, ast.Attribute):
                        deps.add(ann.attr)
                    elif isinstance(ann, ast.Subscript):
                        s = _annotation_str(ann.slice)
                        if s:
                            deps.add(s)
            if fields:
                result[node.name] = (fields, str(pyfile.relative_to(APP_DIR.parent)), extra_mode, deps)
    return result


def _annotation_str(node) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


# ── 步骤 2: 解析 Java DTO (增强) ──

def parse_all_java() -> dict[str, dict[str, str]]:
    """返回 {Java类名: {Java字段名: JSON key}}"""
    result: dict[str, dict[str, str]] = {}
    if not PAYARA_DTO_DIR.exists():
        return result

    for java_file in PAYARA_DTO_DIR.rglob("*.java"):
        try:
            source = java_file.read_text(encoding="utf-8")
        except Exception:
            continue

        cm = re.search(r'public\s+class\s+(\w+)\s+(?:extends|implements|\{)', source)
        if not cm:
            continue
        java_class = cm.group(1)

        fields: dict[str, str] = {}
        # 策略: 先找所有 private 字段声明行
        field_lines = re.findall(
            r'(?:@\w+(?:\([^)]*\))?\s*)*'          # 可选的注解
            r'private\s+'                            # private
            r'(?:static\s+)?'                        # 可选的 static
            r'(?:final\s+)?'                         # 可选的 final
            r'(\w+(?:\.\w+)*)'                       # 类型 (支持 List, com.example.Type)
            r'(?:<(?:[\w\s,.]+)>)?'                   # 可选泛型 <Type>
            r'(?:\[\])?'                             # 可选数组 []
            r'\s+(\w+)'                              # 字段名
            r'(?:\s*=\s*[^;]+)?'                      # 可选默认值
            r'\s*;',
            source,
        )
        for raw in field_lines:
            fname = raw[1]
            ftype = raw[0]
            # 跳过集合/原始/基础类型字段
            if ftype in ("List", "Set", "Map", "Collection",
                         "int", "long", "float", "double", "boolean",
                         "String", "Date", "Integer", "Long", "Double",
                         "Boolean", "BigDecimal", "enum"):
                continue
            # 别名: 同一字段名前查找 @JsonbProperty / @JsonProperty
            alias = fname
            # 在 fname 之前搜索整个文件的别名注解
            pos = source.find(f"private {raw[0]} {fname}")
            if pos < 0:
                pos = source.find(fname)
            if pos > 0:
                before = source[max(0, pos - 500):pos]
                jm = re.findall(r'@(?:JsonbProperty|JsonProperty)\s*\(\s*"(\w+)"\s*\)', before)
                if jm:
                    alias = jm[-1]
            fields[fname] = alias

        if fields:
            result[java_class] = fields
    return result


# ── 步骤 3: 递归收集 DTO 引用链 ──

def transitive_closure(
    py_name: str, py_schemas: dict, deps_collected: set[str], depth: int = 0
):
    """收集 Python schema 引用的所有嵌套 DTO。"""
    if depth > 3 or py_name in deps_collected:
        return
    deps_collected.add(py_name)
    if py_name not in py_schemas:
        return
    _, _, _, deps = py_schemas[py_name]
    for dep in deps:
        base = dep.replace("DTO", "") + "DTO"
        for cand in (dep, base):
            if cand in py_schemas:
                transitive_closure(cand, py_schemas, deps_collected, depth + 1)


# ── 步骤 4: 匹配 + 对比 ──

def match_name(py_name: str) -> str | None:
    if py_name in MANUAL_MAP:
        return MANUAL_MAP[py_name]
    base = py_name.replace("DTO", "")
    for sfx in ("Update", "Creation", "Request"):
        base = base.replace(sfx, "")
    cand = base + "DTO"
    return cand


def compare():
    print("解析 Python schemas ...")
    py_schemas = parse_all_pydantic()
    print(f"  {len(py_schemas)} 个 Pydantic schema 类")

    print("解析 Java DTOs ...")
    java_dtos = parse_all_java()
    print(f"  {len(java_dtos)} 个 Java DTO 类")
    print()

    critical, warning = [], []

    for py_name, (py_fields, py_file, extra_mode, _) in sorted(py_schemas.items()):
        java_name = match_name(py_name)
        if java_name is None or java_name not in java_dtos:
            continue

        java_fields = java_dtos[java_name]

        # Python 接收的 key 集合
        py_keys: set[str] = set()
        for pf, pa in py_fields.items():
            py_keys.add(pf)
            py_keys.add(pa)

        # Java JSON key 集合
        java_keys = set(java_fields.values()) | set(java_fields.keys())
        java_keys -= PY_ONLY

        missing = java_keys - py_keys
        extra = py_keys - java_keys - PY_ONLY

        msgs = []
        severity = "WARNING"

        if missing and extra_mode == "forbid":
            severity = "CRITICAL"
            msgs.append(
                f"  缺字段 (extra=forbid → 422): {sorted(missing)}")
        elif missing:
            msgs.append(
                f"  缺字段 (extra=ignore → 丢弃): {sorted(missing)}")

        if extra and py_name not in REQUEST_ONLY:
            # 检查 extra 中是否包含蛇形命名变体（如 standard_part vs standardPart）
            real_extra = []
            for e in sorted(extra):
                snake = re.sub(r'([A-Z])', r'_\1', e).lower()
                if snake not in java_keys and e not in java_keys:
                    real_extra.append(e)
            if real_extra:
                msgs.append(f"  多余字段: {real_extra}")

        if msgs:
            entry = (
                py_name, java_name, py_file, severity,
                f"Java: {sorted(java_keys)[:15]}{'...' if len(java_keys) > 15 else ''}",
                msgs,
            )
            if severity == "CRITICAL":
                critical.append(entry)
            else:
                warning.append(entry)

    # 输出
    print(f"🔴 CRITICAL: {len(critical)}  (extra=forbid + 缺字段 → 422)")
    print(f"🟡 WARNING:  {len(warning)}  (字段不一致)\n")

    for sev, items in [("CRITICAL", critical), ("WARNING", warning)]:
        if not items:
            continue
        print(f"{'='*60}")
        print(f"  {sev}")
        print(f"{'='*60}")
        for py_name, java_name, py_file, _, jinfo, msgs in items:
            print(f"\n  {py_name} ↔ {java_name} ({py_file})")
            print(f"    {jinfo}")
            for m in msgs:
                print(m)

    return 1 if critical else 0


if __name__ == "__main__":
    sys.exit(compare())

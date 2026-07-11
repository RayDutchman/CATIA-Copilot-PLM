#!/usr/bin/env python3
"""Pydantic Schema → Java DTO 字段对齐验证脚本 v2。

策略: 扫描 app/schemas/ 下所有 Pydantic BaseModel 类，
按名称相似度匹配 Java DTO，逐字段对比。

用法:
    python3 scripts/validate_dto_fields.py
"""

import ast
import re
import os
import sys
from collections import defaultdict
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent / "app"
SCHEMAS_DIR = APP_DIR / "schemas"
PAYARA_DTO_DIR = Path(__file__).resolve().parent.parent.parent / \
    "docdoku-plm-server/docdoku-plm-server-rest/src/main/java/com/docdoku/plm/server/rest/dto"

# 手工映射: Python schema → Java DTO 名 (用于名称差异大的情况)
MANUAL_MAP: dict[str, str] = {
    "PartCreationDTO": "PartCreationDTO",
    "PartRevisionDTO": "PartRevisionDTO",
    "PartIterationDTO": "PartIterationDTO",
    "PartIterationUpdateDTO": "PartIterationDTO",
    "LoginRequestDTO": None,  # 无 Java DTO，Java 用 FormParam
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
    "WorkflowModelDTO": "WorkflowModelDTO",
    "WorkflowDTO": "WorkflowDTO",
    "ActivityDTO": "ActivityDTO",
    "RoleDTO": "RoleDTO",
    "UserDTO": "UserDTO",
    "UserGroupDTO": "UserGroupDTO",
    "AccountDTO": "AccountDTO",
    "WorkspaceDTO": "WorkspaceDTO",
    "WorkspaceUserMembershipDTO": "WorkspaceUserMembershipDTO",
    "PathDataMasterDTO": "PathDataMasterDTO",
    "PathDataIterationDTO": "PathDataIterationDTO",
    "PathDataIterationCreationDTO": "PathDataIterationCreationDTO",
    "PathToPathLinkDTO": "PathToPathLinkDTO",
    "PartMasterTemplateDTO": "PartMasterTemplateDTO",
    "DocumentMasterTemplateDTO": "DocumentMasterTemplateDTO",
    "EffectivityDTO": "EffectivityDTO",
    "BaselinedPartDTO": "BaselinedPartDTO",
    "BaselinedDocumentDTO": "BaselinedDocumentDTO",
    "ProductBaselineDTO": "ProductBaselineDTO",
    "DocumentBaselineDTO": "DocumentBaselineDTO",
    "ProductConfigurationDTO": "ProductConfigurationDTO",
    "ImportDTO": "ImportDTO",
    "ImportPreviewDTO": "ImportPreviewDTO",
    "QueryDTO": "QueryDTO",
    "QueryResultRowDTO": "QueryResultRowDTO",
    "NotificationDTO": "NotificationDTO",
    "ModificationNotificationDTO": "ModificationNotificationDTO",
    "SharedPartDTO": "SharedPartDTO",
    "SharedDocumentDTO": "SharedDocumentDTO",
    "WebhookDTO": "WebhookDTO",
    "TagDTO": "TagDTO",
    "LayerDTO": "LayerDTO",
    "MarkerDTO": "MarkerDTO",
}

# Java 集合包装类型: List<X> → 忽略
JAVA_COLLECTIONS = {
    "List", "Set", "Map", "Collection", "Iterable",
}

# Java 基础类型: 忽略
JAVA_PRIMITIVES = {
    "int", "long", "float", "double", "boolean", "char", "byte", "short",
    "Integer", "Long", "Float", "Double", "Boolean", "Character", "Byte", "Short",
    "String", "Date", "Timestamp", "BigDecimal", "BigInteger",
    "byte[]", "int[]", "double[]", "float[]", "boolean[]",
}

# Pydantic 内部字段: 忽略
PYDANTIC_INTERNAL = {"model_config", "model_fields", "model_computed_fields", "model_extra"}


# ── 步骤 1: 解析所有 Pydantic schema ──

def parse_all_pydantic_schemas() -> dict[str, tuple[dict[str, str], str, str]]:
    """返回 {Python类名: ({字段名: alias, ...}, 文件路径, extra_mode)}"""
    result: dict[str, tuple[dict[str, str], str, str]] = {}
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
            fields = {}
            extra_mode = "forbid"
            # 读取 model_config extra
            for item in ast.iter_child_nodes(node):
                if isinstance(item, ast.Assign) and isinstance(item.targets[0], ast.Name):
                    if item.targets[0].id == "model_config":
                        if isinstance(item.value, ast.Call):
                            for kw in item.value.keywords:
                                if kw.arg == "extra" and isinstance(kw.value, ast.Constant):
                                    extra_mode = kw.value.value
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
            if fields:
                result[node.name] = (fields, str(pyfile.relative_to(APP_DIR.parent)), extra_mode)
    return result


# ── 步骤 2: 解析所有 Java DTO ──

def parse_all_java_dtos() -> dict[str, dict[str, str]]:
    """返回 {Java类名: {Java字段名: JSON key}}"""
    result: dict[str, dict[str, str]] = {}
    if not PAYARA_DTO_DIR.exists():
        return result
    for java_file in PAYARA_DTO_DIR.rglob("*.java"):
        try:
            source = java_file.read_text(encoding="utf-8")
        except Exception:
            continue
        # 找 public class XxxDTO extends/implements ...
        class_match = re.search(r'public\s+class\s+(\w+)\s+(?:extends|implements)', source)
        if not class_match:
            continue
        java_class = class_match.group(1)

        fields: dict[str, str] = {}
        # @ApiModelProperty 后跟的字段声明
        api_pattern = re.compile(
            r'(?:@\w+(?:\([^)]*\))?\s*)*private\s+(List<)?(\w+)(>)?\s+(\w+)\s*;',
            re.MULTILINE,
        )
        for m in api_pattern.finditer(source):
            ftype_wrapper = m.group(1) or ""
            ftype = m.group(2)
            fname = m.group(4)
            if ftype in JAVA_PRIMITIVES or ftype in JAVA_COLLECTIONS:
                continue
            if ftype_wrapper:
                continue  # 跳过 List<DtoType> 嵌套
            fields[fname] = fname

        # @JsonProperty 别名
        json_prop = re.compile(r'@JsonProperty\s*\(\s*"(\w+)"\s*\)')
        for m in json_prop.finditer(source):
            alias = m.group(1)
            post = source[m.end():m.end() + 200]
            pm = re.search(r'private\s+\S+\s+(\w+)\s*;', post)
            if pm and pm.group(1) not in ("set", "get"):
                fields[pm.group(1)] = alias

        if fields:
            result[java_class] = fields
    return result


# ── 步骤 3: 名称匹配 → 字段对比 ──

def match_and_compare(
    py_schemas: dict,
    java_dtos: dict,
) -> list[tuple[str, str, str, str, list]]:
    issues: list[tuple[str, str, str, str, list]] = []

    for py_name, (py_fields, py_file, extra_mode) in py_schemas.items():
        # 确定目标 Java DTO 名
        java_name = MANUAL_MAP.get(py_name)
        if java_name is None and py_name in MANUAL_MAP:
            continue  # 明确标记为无对应 Java DTO

        if java_name is None:
            # 自动匹配: 去掉 DTO/Update/Creation/Request 后缀
            base = py_name.replace("DTO", "").replace("Update", "").replace("Creation", "").replace("Request", "")
            candidates = [py_name, base + "DTO"]
            java_name = None
            for c in candidates:
                if c in java_dtos:
                    java_name = c
                    break
        if java_name is None or java_name not in java_dtos:
            continue

        java_fields = java_dtos[java_name]
        # Python 可接受的 JSON key 集合（字段名 + alias）
        py_keys: set[str] = set()
        for py_field, py_alias in py_fields.items():
            py_keys.add(py_field)
            py_keys.add(py_alias)

        # Java JSON key 集合（字段名 + @JsonProperty 别名）
        java_keys: set[str] = set(java_fields.values()) | set(java_fields.keys())

        # 过滤基础字段（两个方向都忽略）
        base_keys = {
            "workspaceId", "workspace_id", "configurationItemId", "configurationItemKey",
            "partKey", "documentKey", "id",
        }

        missing_py = java_keys - py_keys - base_keys
        extra_py = py_keys - java_keys - base_keys

        msgs = []
        if missing_py:
            msgs.append(
                f"Python 缺失字段: {sorted(missing_py)} "
                f"(extra_mode={extra_mode}, 会被{'拒绝' if extra_mode == 'forbid' else '丢弃'})"
            )
        if extra_py:
            msgs.append(f"Python 多了字段(Java无): {sorted(extra_py)}")

        if msgs:
            issues.append((
                py_name,
                java_name,
                py_file,
                f"Java: {sorted(java_keys)[:12]}...",
                msgs,
            ))

    return issues


def main():
    print("解析 Python schemas ...")
    py_schemas = parse_all_pydantic_schemas()
    print(f"  找到 {len(py_schemas)} 个 Pydantic schema 类\n")

    print("解析 Java DTOs ...")
    java_dtos = parse_all_java_dtos()
    print(f"  找到 {len(java_dtos)} 个 Java DTO 类\n")

    issues = match_and_compare(py_schemas, java_dtos)
    if not issues:
        print("✅ 所有 Python schema 字段与 Java DTO 对齐")
        return 0

    # 分类
    critical = [i for i in issues if any("会被拒绝" in m for m in i[4])]
    warning = [i for i in issues if i not in critical]

    print(f"🔴 critical: {len(critical)} 个 schema 带 extra='forbid' 但缺字段（会导致 422）")
    print(f"🟡 warning : {len(warning)} 个 schema 字段不一致\n")

    for severity, items in [("CRITICAL", critical), ("WARNING", warning)]:
        if not items:
            continue
        print(f"{'='*60}")
        print(f"  {severity}")
        print(f"{'='*60}")
        for py_name, java_name, py_file, java_info, msgs in items:
            print(f"\n{py_name} ↔ {java_name}")
            print(f"  Python: {py_file}")
            print(f"  {java_info}")
            for m in msgs:
                print(f"  {m}")

    return 1


if __name__ == "__main__":
    sys.exit(main())

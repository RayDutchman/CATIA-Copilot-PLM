"""属性合并工具——对齐 Payara AttributesImporterUtils.java 合并语义 + LOV 校验。

提供属性值转换、LOV 查找、现有属性加载、合并（更新/新建）、以及 dry-run 判断。
纯逻辑模块；LOV 解析和现有属性读取需要数据库 Session。
"""
import datetime
from dataclasses import dataclass
from sqlalchemy import text

# ── 模块级映射（导出，Task 4 依赖） ──────────────────────────────────────────
TOKEN_TO_DTYPE = {
    "TEXT": "InstanceTextAttribute",
    "NUMBER": "InstanceNumberAttribute",
    "DATE": "InstanceDateAttribute",
    "BOOLEAN": "InstanceBooleanAttribute",
    "URL": "InstanceURLAttribute",
    "LONG_TEXT": "InstanceLongTextAttribute",
    "LOV": "InstanceListOfValuesAttribute",
}

TOKEN_TO_VALUECOL = {
    "TEXT": "textvalue",
    "NUMBER": "numbervalue",
    "DATE": "datevalue",
    "BOOLEAN": "booleanvalue",
    "URL": "urlvalue",
    "LONG_TEXT": "longtextvalue",
    "LOV": "indexvalue",
}

DTYPE_TO_TOKEN = {v: k for k, v in TOKEN_TO_DTYPE.items()}


@dataclass
class MergedAttribute:
    """合并后的属性（已做类型转换和 LOV 索引解析）。"""
    name: str
    type: str             # 规范 token: TEXT/NUMBER/DATE/BOOLEAN/URL/LONG_TEXT/LOV
    value: object = None  # str / float / datetime / bool / int(LOV索引) / None
    mandatory: bool = False
    locked: bool = False


# ── 值转换 ─────────────────────────────────────────────────────────────────

def convert_value(token: str, raw: str | None) -> object:
    """将原始字符串按类型 token 转换为 Python 类型。

    Raises ValueError: 值格式与类型不匹配时抛出，由调用方（merge_attributes）捕获。
    - 空值/None → 返回 None（LOV 由 resolve_lov_index 处理，不进入此分支）。
    """
    if raw is None or (isinstance(raw, str) and raw.strip() == ""):
        return None

    if token in ("TEXT", "LONG_TEXT", "URL"):
        return str(raw)

    if token == "NUMBER":
        return float(raw)

    if token == "BOOLEAN":
        return raw == "true"

    if token == "DATE":
        return datetime.datetime.strptime(raw, "%Y-%m-%d %H:%M:%S")

    # LOV 值转换由 resolve_lov_index 在 merge 中完成，此处返回 None
    if token == "LOV":
        return None

    return str(raw)


# ── LOV 值查找 ─────────────────────────────────────────────────────────────

def resolve_lov_index(db, workspace_id: str, lov_name: str, value: str) -> int | None:
    """在 lov_namevalue 表中查找 value 对应的 0-based 排序索引。

    匹配 name 字段，按 namevalue_order 排序后取第一个匹配项的下标。
    无匹配返回 None。
    """
    rows = db.execute(text(
        "SELECT name FROM lov_namevalue "
        "WHERE lov_name=:ln AND lov_workspace_id=:ws "
        "ORDER BY namevalue_order"
    ), {"ln": lov_name, "ws": workspace_id}).fetchall()

    for idx, row in enumerate(rows):
        if row[0] == value:
            return idx

    return None


# ── 现有属性加载 ───────────────────────────────────────────────────────────

def load_existing_attributes(db, workspace_id: str, part_number: str,
                              version: str, iteration: int) -> list[MergedAttribute]:
    """从 partiteration_attribute + instanceattribute 加载现有属性列表。

    按 attribute_order 排序，值取对应 TOKEN_TO_VALUECOL 列。
    """
    rows = db.execute(text(
        "SELECT ia.dtype, ia.name, ia.mandatory, ia.locked, "
        "       ia.textvalue, ia.longtextvalue, ia.numbervalue, ia.datevalue, "
        "       ia.booleanvalue, ia.urlvalue, ia.indexvalue "
        "FROM partiteration_attribute pia "
        "JOIN instanceattribute ia ON ia.id = pia.instanceattribute_id "
        "WHERE pia.workspace_id=:ws AND pia.partmaster_partnumber=:pn "
        "  AND pia.partrevision_version=:ver AND pia.iteration=:it "
        "ORDER BY pia.attribute_order"
    ), {
        "ws": workspace_id, "pn": part_number,
        "ver": version, "it": iteration,
    }).fetchall()

    result: list[MergedAttribute] = []
    for row in rows:
        dtype = row.dtype or "InstanceTextAttribute"
        token = DTYPE_TO_TOKEN.get(dtype, "TEXT")
        col = TOKEN_TO_VALUECOL.get(token, "textvalue")
        # 用 getattr 从 Row 对象取对应列的值
        value = getattr(row, col, None) if hasattr(row, col) else None
        result.append(MergedAttribute(
            name=row.name,
            type=token,
            value=value,
            mandatory=bool(row.mandatory),
            locked=bool(row.locked),
        ))
    return result


# ── 合并（核心算法，移植 Java updateAndCreateInstanceAttributes） ──────────

def merge_attributes(db, workspace_id: str,
                      existing: list[MergedAttribute],
                      parsed: list,  # list[ParsedAttribute]
                      part_number: str,
                      errors: list[str]) -> list[MergedAttribute]:
    """按 Java AttributesImporterUtils.updateAndCreateInstanceAttributes 语义合并。

    - result = list(existing) 保序，未被 Excel 提及的保留
    - available = list(existing) 用于匹配去重，命中即移除
    - 更新模式（attribute_id != None）：在 available 找 name+type 相同者 → 更新 value
    - 新建模式（attribute_id == None）：在 available 找不到 → append；找到 → DuplicateEntry
    - LOV 值走 resolve_lov_index（lov_name 缺失或值不存在记 LovValueNotFound，不用 ConversionError 包装）
    - 非 LOV 类型值转换失败（ValueError）记 ConversionError 并跳过该属性
    """
    result = list(existing)
    available = list(existing)  # 同一对象引用，修改 result 中的对象也反映在 available

    for pa in parsed:
        # 在 available 中按 name 相同且 type 相同匹配
        match = None
        for attr in available:
            if attr.name == pa.name and attr.type == pa.type:
                match = attr
                break

        if pa.attribute_id is not None:
            # ── 更新模式 ──
            if match is None:
                errors.append(
                    f"AttributeNotFound: part '{part_number}' "
                    f"attribute '{pa.name}' <{pa.type}>"
                )
                continue
            new_val = _resolve_value_safe(
                db, workspace_id, pa, part_number, errors,
            )
            if new_val is _SENTINEL_ERROR:
                continue
            match.value = new_val
            available.remove(match)
        else:
            # ── 新建模式 ──
            if match is not None:
                errors.append(
                    f"DuplicateEntry: part '{part_number}' "
                    f"attribute '{pa.name}' <{pa.type}>"
                )
                continue
            new_val = _resolve_value_safe(
                db, workspace_id, pa, part_number, errors,
            )
            if new_val is _SENTINEL_ERROR:
                continue
            result.append(MergedAttribute(
                name=pa.name,
                type=pa.type,
                value=new_val,
            ))

    return result


# 哨兵对象，标记 _resolve_value_safe 遇到错误（已记入 errors）
_SENTINEL_ERROR = object()


def _resolve_value_safe(db, workspace_id: str, pa,
                        part_number: str, errors: list[str]) -> object:
    """解析属性值，区分 LOV 错误和普通转换错误。

    LOV 值不存在或 lov_name 缺失 → 直接向 errors 追加 LovValueNotFound，返回哨兵。
    非 LOV 类型转换失败 → 向 errors 追加 ConversionError，返回哨兵。
    成功 → 返回解析后的值（int 索引 / str / float / datetime / bool）。
    """
    if pa.type == "LOV":
        if not pa.lov_name:
            errors.append(
                f"LovValueNotFound: part '{part_number}' "
                f"attribute '{pa.name}' has no LOV name"
            )
            return _SENTINEL_ERROR
        idx = resolve_lov_index(db, workspace_id, pa.lov_name, pa.value)
        if idx is None:
            errors.append(
                f"LovValueNotFound: part '{part_number}' "
                f"attribute '{pa.name}' value '{pa.value}' "
                f"not found in LOV '{pa.lov_name}'"
            )
            return _SENTINEL_ERROR
        return idx

    try:
        return convert_value(pa.type, pa.value)
    except ValueError as e:
        errors.append(
            f"ConversionError: part '{part_number}' "
            f"attribute '{pa.name}' <{pa.type}> value '{pa.value}': {e}"
        )
        return _SENTINEL_ERROR


# ── dry-run 判断 ───────────────────────────────────────────────────────────

def would_change(db, workspace_id: str,
                  existing: list[MergedAttribute],
                  parsed: list) -> bool:  # list[ParsedAttribute]
    """移植 Java checkIfUpdateOrCreateInstanceAttributes 逻辑。

    - 更新模式：能在 existing 中找到同 name+type → True
    - 新建模式：在 existing 中找不到同 name+type → True
    - 任意一项为 True 即返回 True。
    """
    for pa in parsed:
        found = any(
            attr.name == pa.name and attr.type == pa.type
            for attr in existing
        )
        if pa.attribute_id is not None:
            # 更新模式 → 必须有匹配
            if found:
                return True
        else:
            # 新建模式 → 必须无匹配（不能重复）
            if not found:
                return True

    return False

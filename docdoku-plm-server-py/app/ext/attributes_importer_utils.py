"""属性导入工具（对标 AttributesImporterUtils — 312 行属性校验与转换）。"""
import re
import logging
from datetime import datetime
from typing import Any
from app.ext.attribute_model import ImportAttribute, AttributeType

_logger = logging.getLogger(__name__)

# 类型转换优先级
_TYPE_INFERENCE = [
    (re.compile(r'^-?\d+(\.\d+)?$'), AttributeType.NUMBER),
    (re.compile(r'^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}:\d{2})?(:?\d+)?$'), AttributeType.DATE),
    (re.compile(r'^(true|false|yes|no|0|1)$', re.IGNORECASE), AttributeType.BOOLEAN),
    (re.compile(r'^https?://\S+$'), AttributeType.URL),
]


def infer_attribute_type(value: Any) -> AttributeType:
    """根据值内容推测属性类型。"""
    if isinstance(value, (int, float)):
        return AttributeType.NUMBER
    if isinstance(value, datetime):
        return AttributeType.DATE
    if isinstance(value, bool):
        return AttributeType.BOOLEAN
    sv = str(value).strip()
    if len(sv) > 200:
        return AttributeType.LONG_TEXT
    for pattern, atype in _TYPE_INFERENCE:
        if pattern.match(sv):
            return atype
    return AttributeType.TEXT


def convert_value(value: Any, target_type: AttributeType) -> Any:
    """将原始值转换为目标属性类型。"""
    try:
        if target_type == AttributeType.NUMBER:
            return float(value)
        elif target_type == AttributeType.DATE:
            if isinstance(value, datetime):
                return value
            v = str(value).replace("Z", "+00:00")
            return datetime.fromisoformat(v)
        elif target_type == AttributeType.BOOLEAN:
            sv = str(value).lower()
            return sv in ("true", "yes", "1")
        elif target_type == AttributeType.TEXT:
            return str(value)
        elif target_type == AttributeType.LONG_TEXT:
            return str(value)
        elif target_type == AttributeType.URL:
            return str(value)
        elif target_type == AttributeType.LOV:
            return str(value)
        else:
            return str(value)
    except (ValueError, TypeError):
        _logger.warning("属性值转换失败: %s → %s", value, target_type)
        return None


def validate_template_attributes(
    attributes: list[ImportAttribute],
    template_attrs: list[dict],
    attributes_locked: bool = False,
) -> list[str]:
    """校验导入属性是否匹配模板定义。

    返回错误消息列表，空列表表示校验通过。
    """
    errors: list[str] = []
    template_map: dict[str, dict] = {ta["name"]: ta for ta in template_attrs}

    # 检查模板中有但导入未提供的 mandatory 属性
    for ta in template_attrs:
        if ta.get("mandatory") and ta["name"] not in {a.name for a in attributes}:
            errors.append(f"缺少必填属性: {ta['name']}")

    # 检查 import 中的每个属性
    for attr in attributes:
        ta = template_map.get(attr.name)
        if ta is None:
            continue  # 模板未定义的属性跳过
        if ta.get("locked") != attr.locked and attributes_locked:
            errors.append(f"属性 {attr.name} 的 locked 状态与模板不一致")

    return errors

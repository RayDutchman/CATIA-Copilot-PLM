"""AttributesConsistencyUtils——属性一致性校验工具。

对齐 Java AttributesConsistencyUtils。
用于验证属性变更是否合法（locked/unlocked/mandatory 规则）。
"""
from typing import List


def has_valid_change(old_attributes: list, attributes_locked: bool,
                     new_attributes: list) -> bool:
    """验证属性变更是否合法。

    如果 locked：新旧列表必须完全相同（顺序、类型、名称均一致）。
    否则：检查 locked 属性在新列表中是否一致保留。
    """
    if attributes_locked:
        return _check_attributes_equality(old_attributes, new_attributes)
    return _locked_attributes_consistency(old_attributes, new_attributes)


def is_template_attributes_valid(attribute_templates: list,
                                  attributes_locked: bool) -> bool:
    """验证模板属性定义是否合法。

    locked 模式：所有属性必须 locked。
    mandatory 属性必须 locked。
    """
    for tpl in attribute_templates:
        if not hasattr(tpl, 'locked'):
            continue
        if attributes_locked:
            if not tpl.locked:
                return False
        if getattr(tpl, 'mandatory', False) and not tpl.locked:
            return False
    return True


def _check_attributes_equality(old_attrs: list, new_attrs: list) -> bool:
    """完全一致检查。"""
    if len(old_attrs) != len(new_attrs):
        return False
    for i, old in enumerate(old_attrs):
        new = new_attrs[i] if i < len(new_attrs) else None
        if new is None:
            return False
        if not _check_valid_attribute(old, new):
            return False
    return True


def _check_valid_attribute(old, new) -> bool:
    """检查单个属性变更是否合法。"""
    # 类型、名称必须一致
    old_type = type(old).__name__ if old else None
    new_type = type(new).__name__ if new else None
    if old_type != new_type:
        return False
    old_name = getattr(old, 'name', None)
    new_name = getattr(new, 'name', None)
    if old_name != new_name:
        return False
    # locked 属性值必须一致
    if getattr(old, 'locked', False):
        old_val = _attr_value(old)
        new_val = _attr_value(new)
        if old_val != new_val:
            return False
    return True


def _locked_attributes_consistency(old_attrs: list, new_attrs: list) -> bool:
    """non-locked 模式：检查 locked 属性在新列表中是否一致。"""
    old_map = _get_mapped_attributes(old_attrs)
    new_map = _get_mapped_attributes(new_attrs)
    for key, old in old_map.items():
        if getattr(old, 'locked', False):
            new = new_map.get(key)
            if new is None:
                return False
            if _attr_value(old) != _attr_value(new):
                return False
    return True


def _get_mapped_attributes(attrs: list) -> dict:
    """按 name 映射属性。"""
    result = {}
    for a in attrs or []:
        name = getattr(a, 'name', '')
        if name:
            result[name] = a
    return result


def _attr_value(attr) -> str:
    """取属性值字符串。"""
    if hasattr(attr, 'value'):
        return str(attr.value or '')
    if hasattr(attr, 'date_value'):
        return str(attr.date_value or '')
    if hasattr(attr, 'selected_value'):
        return str(attr.selected_value or '')
    return str(attr or '')

"""导入属性模型（对标 Attribute.java — 外部导入时使用的属性 DTO）。"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AttributeType(str, Enum):
    TEXT = "TEXT"
    NUMBER = "NUMBER"
    DATE = "DATE"
    BOOLEAN = "BOOLEAN"
    URL = "URL"
    LOV = "LOV"
    LONG_TEXT = "LONG_TEXT"


@dataclass
class ImportAttribute:
    """导入属性条目。"""
    name: str
    attribute_type: AttributeType = AttributeType.TEXT
    value: Any = None
    mandatory: bool = False
    locked: bool = False
    lov_name: str | None = None
    lov_workspace_id: str | None = None

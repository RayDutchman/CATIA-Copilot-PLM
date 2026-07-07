"""零件导入器（对标 PartImporter + PartImporterResult + PartToImport）。

支持从外部格式（Excel/CSV/XML）导入零件主记录 + 修订版。
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from app.ext.attribute_model import ImportAttribute
from app.ext.attributes_holder import AttributesHolder


@dataclass
class PartToImport(AttributesHolder):
    """待导入零件 DTO。"""
    part_number: str
    part_name: str = ""
    part_type: str = "Part"
    description: str = ""
    version: str = "A"
    status: int = 0                    # 0=WIP, 1=RELEASED
    standard_part: bool = False
    attributes: list[ImportAttribute] = field(default_factory=list)
    author_login: str = ""
    author_workspace_id: str = ""
    template_id: str | None = None
    workflow_model_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PartImportResult:
    """零件导入结果。"""
    success: bool
    total_count: int = 0
    created_count: int = 0
    updated_count: int = 0
    skipped_count: int = 0
    error_count: int = 0
    errors: list[str] = field(default_factory=list)
    part_numbers: list[str] = field(default_factory=list)


class PartImporter(ABC):
    """零件导入器抽象基类。

    子类实现 parse() 解析数据，基类 handle import_parts() 写 DB。
    """

    @abstractmethod
    def parse(self, data: bytes, filename: str) -> list[PartToImport]:
        """解析外部数据为零件列表。"""
        ...

    def validate(self, parts: list[PartToImport]) -> list[str]:
        """校验零件列表，返回错误消息。"""
        errors = []
        seen = set()
        for i, p in enumerate(parts):
            if not p.part_number:
                errors.append(f"零件 {i+1}: 缺少编号")
                continue
            if p.part_number in seen:
                errors.append(f"零件 {i+1}: 编号 {p.part_number} 重复")
            seen.add(p.part_number)
            if p.status not in (0, 1, 2):
                errors.append(f"零件 {p.part_number}: 无效状态 {p.status}")
        return errors

"""BOM 导入器（对标 BomImporter 接口 + BomImporterResult DTO）。"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from app.ext.attribute_model import ImportAttribute
from app.ext.attributes_holder import AttributesHolder


@dataclass
class BomImportRow(AttributesHolder):
    """BOM 中的一行（一个零件引用）。"""
    part_number: str
    part_name: str = ""
    quantity: float = 1.0
    unit: str = ""
    revision: str = "A"
    attributes: list[ImportAttribute] = field(default_factory=list)
    parent_number: str | None = None  # 父零件编号


@dataclass
class BomImportResult:
    """BOM 导入结果。"""
    success: bool
    total_rows: int = 0
    imported_count: int = 0
    skipped_count: int = 0
    error_count: int = 0
    errors: list[str] = field(default_factory=list)
    created_parts: list[str] = field(default_factory=list)  # 新建零件编号列表
    usage_links: list[dict] = field(default_factory=list)


class BomImporter(ABC):
    """BOM 导入器抽象基类。

    子类实现 parse() 解析特定格式（Excel/CSV/TXT），
    基类 handle import_bom() 负责 DB 写入。
    """

    @abstractmethod
    def parse(self, data: bytes, filename: str) -> list[BomImportRow]:
        """解析 BOM 数据为行列表。"""
        ...

    def validate(self, rows: list[BomImportRow]) -> list[str]:
        """校验 BOM 行数据，返回错误列表。"""
        errors = []
        seen = set()
        for i, row in enumerate(rows):
            if not row.part_number:
                errors.append(f"行{i+1}: 缺少零件编号")
                continue
            key = row.part_number
            if key in seen:
                errors.append(f"行{i+1}: 零件 {key} 重复")
            seen.add(key)
        return errors

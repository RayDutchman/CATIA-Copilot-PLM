"""路径数据导入器（对标 PathDataImporter + PathDataImporterResult + PathDataToImport）。

PathData 为产品实例中特定路径（装配路径）赋予自定义属性和文档链接。
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any
from app.ext.attribute_model import ImportAttribute
from app.ext.attributes_holder import AttributesHolder


@dataclass
class PathDataToImport(AttributesHolder):
    """待导入路径数据 DTO。"""
    path: str                              # 装配路径字符串 (如 u1-u4-u7)
    path_data_id: int | None = None        # 已有 PathDataMaster ID
    iteration_note: str = ""
    attributes: list[ImportAttribute] = field(default_factory=list)
    linked_documents: list[dict] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PathDataImportResult:
    """路径数据导入结果。"""
    success: bool
    total_count: int = 0
    created_count: int = 0
    updated_count: int = 0
    error_count: int = 0
    errors: list[str] = field(default_factory=list)


class PathDataImporter(ABC):
    """路径数据导入器抽象基类。"""

    @abstractmethod
    def parse(self, data: bytes, filename: str) -> list[PathDataToImport]:
        """解析外部数据为路径数据列表。"""
        ...

    def validate(self, entries: list[PathDataToImport]) -> list[str]:
        """校验路径数据。"""
        errors = []
        for i, e in enumerate(entries):
            if not e.path:
                errors.append(f"行 {i+1}: 缺少 path")
            if e.path and not e.path.startswith("u"):
                errors.append(f"行 {i+1}: 无效 path 格式: {e.path}")
        return errors

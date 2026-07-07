"""文档基线导出上下文（对标 DocumentBaselineFileExport DTO）。"""
from dataclasses import dataclass


@dataclass
class DocumentBaselineFileExport:
    workspace_id: str
    baseline_id: int

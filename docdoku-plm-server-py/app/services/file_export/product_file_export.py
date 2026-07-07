"""产品导出上下文（对标 ProductFileExport DTO）。"""
from dataclasses import dataclass, field


@dataclass
class ProductFileExport:
    workspace_id: str
    configuration_item_id: str
    ps_filter: dict | None = None  # ProductStructureFilter 描述
    serial_number: str | None = None
    baseline_id: int | None = None
    export_native_cad: bool = False
    export_document_links: bool = False
    binaries_in_tree: dict[str, set[str]] = field(default_factory=dict)

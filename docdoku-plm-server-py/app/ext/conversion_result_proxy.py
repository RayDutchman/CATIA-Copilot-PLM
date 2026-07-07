"""转换结果代理 DTO（对标 ConversionResultProxy — conversion-service 回调数据）。"""
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ConversionResultProxy:
    """conversion-service 回调返回的转换结果。"""
    workspace_id: str
    part_number: str
    version: str
    iteration: int
    success: bool
    output_path: str | None = None     # GLB 文件 vault 路径
    error_message: str | None = None
    geometries: list[dict[str, Any]] = field(default_factory=list)
    qualities: list[str] = field(default_factory=list)

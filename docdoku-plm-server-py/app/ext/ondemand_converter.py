"""按需格式转换（对标 OnDemandConverter — STEP→PDF/OBJ 等额外格式）。

与主转换流程不同，OnDemandConverter 处理非 3D 预览需求（如导出 PDF 图纸/OBJ 网格）。
"""
import logging
from dataclasses import dataclass

_logger = logging.getLogger(__name__)


@dataclass
class OnDemandConversionRequest:
    """按需转换请求。"""
    workspace_id: str
    part_number: str
    version: str
    iteration: int
    source_full_name: str     # vault 中源文件路径
    output_format: str        # 目标格式 (pdf, obj, dae 等)


class OnDemandConverterService:
    """按需转换服务（stub 实现，后续接入 external converter）。"""

    def convert(self, request: OnDemandConversionRequest) -> bytes | None:
        """执行按需转换，返回输出字节，不支持则返回 None。"""
        _logger.warning("按需转换仅 stub 实现: %s", request.output_format)
        return None

    def get_supported_formats(self) -> list[str]:
        return ["pdf", "obj", "dae"]


ondemand_converter = OnDemandConverterService()

"""按需转换服务——对标 Payara OnDemandConverterBean。

处理文档/零件的格式转换（PDF 等）。
"""
from sqlalchemy.orm import Session


class OnDemandConverterService:
    """按需格式转换服务。"""

    def get_document_converted_resource(self, db: Session,
                                         output_format: str,
                                         binary_resource_id: int) -> bytes:
        """获取文档的格式转换结果。"""
        # TODO: 实现与实际转换引擎的集成
        return b""

    def get_part_converted_resource(self, db: Session,
                                     output_format: str,
                                     binary_resource_id: int) -> bytes:
        """获取零件的格式转换结果。"""
        # TODO: 实现与实际转换引擎的集成
        return b""


ondemand_converter_service = OnDemandConverterService()

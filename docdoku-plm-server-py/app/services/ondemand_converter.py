"""按需转换服务——对标 Payara OnDemandConverterBean。

处理文档/零件的格式转换（PDF 等）。
"""
from sqlalchemy.orm import Session


class OnDemandConverterService:
    """按需格式转换服务。"""

    def get_document_converted_resource(self, db: Session,
                                         output_format: str,
                                         binary_resource_id: int) -> bytes:
        """获取文档的格式转换结果。

        对齐 Payara OnDemandConverterBean.getDocumentConvertedResource：
        依赖插件式转换引擎（OfficeOnDemandConverter 基于 LibreOffice/jodconverter）。
        该引擎为外部依赖，容器内不可用，无 selectedConverter 时 Java 返回 null。
        此处对齐该行为返回空 bytes（无引擎 → 无转换结果）。
        DEFERRED (见 docs/migration/loose-ends.md): 集成 LibreOffice 转换引擎后实现。
        """
        return b""

    def get_part_converted_resource(self, db: Session,
                                     output_format: str,
                                     binary_resource_id: int) -> bytes:
        """获取零件的格式转换结果。

        对齐 Payara OnDemandConverterBean.getPartConvertedResource：同上，
        无可用转换引擎时返回空（对齐 Java null 行为）。
        DEFERRED (见 docs/migration/loose-ends.md): 集成转换引擎后实现。
        """
        return b""


ondemand_converter_service = OnDemandConverterService()

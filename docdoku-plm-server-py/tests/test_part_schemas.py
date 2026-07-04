"""零件 Pydantic Schemas 测试。"""
from app.schemas.part import PartRevisionDTO, PartCreationDTO, ConversionDTO


def test_part_creation_dto_required_fields():
    """创建零件 DTO 只有 number 是必填。"""
    dto = PartCreationDTO(number="PART-001")
    assert dto.number == "PART-001"
    assert dto.name == ""
    assert dto.standard_part is False


def test_part_revision_dto_part_key():
    """partKey 应为 number-version 拼接。"""
    dto = PartRevisionDTO(
        workspaceId="WS1", number="PART-001", version="A",
        name="Test Part"
    )
    assert dto.partKey == "PART-001-A"


def test_conversion_dto_defaults():
    dto = ConversionDTO()
    assert dto.pending is False
    assert dto.succeed is False


def test_part_revision_status_field():
    """status 字段接受字符串 WIP/RELEASED/OBSOLETE。"""
    dto = PartRevisionDTO(
        workspaceId="WS1", number="P", version="A",
        name="x", status="RELEASED"
    )
    assert dto.status == "RELEASED"

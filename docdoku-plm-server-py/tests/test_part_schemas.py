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


# ── Task 10: DTO 字段固化测试 ────────────────────────────

def test_geometry_uri_format(db):
    """有 GLB 的 iteration 应返回 /api/files/{fullname} 格式的 geometryFileURI。"""
    from app.services.part_mapper import map_revision
    from app.services.product_service import ProductService
    svc = ProductService()
    pr = svc.get_revision(db, "Workspace_2", "Differential Axle 2010", "A")
    dto = map_revision(pr, db)
    it1 = next(i for i in dto.partIterations if i.iteration == 1)
    assert it1.geometryFileURI is not None
    assert it1.geometryFileURI.startswith("/api/files/Workspace_2/parts/")
    assert it1.geometryFileURI.endswith(".glb")


def test_user_dto_has_name_email_language(db):
    from app.services.part_mapper import map_revision
    from app.services.product_service import ProductService
    svc = ProductService()
    pr = svc.get_revision(db, "Workspace_2", "Differential Axle 2010", "A")
    dto = map_revision(pr, db)
    assert dto.author.name is not None
    assert dto.author.email is not None
    assert dto.author.language is not None

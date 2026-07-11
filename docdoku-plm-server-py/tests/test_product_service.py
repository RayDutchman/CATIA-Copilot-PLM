"""ProductService 业务逻辑测试。"""
import pytest
from app.services.product_manager import ProductService
from app.core.exceptions import EntityNotFoundException, PartMasterNotFoundException
from app.schemas.part import PartCreationDTO


WS = "GD50"  # 数据库中实际存在的 workspace


def test_list_revisions_returns_list(db):
    svc = ProductService()
    result = svc.list_revisions(db, WS, 0, 10)
    assert isinstance(result, list)


def test_count_parts_returns_int(db):
    svc = ProductService()
    count = svc.count_parts(db, WS)
    assert isinstance(count, int)
    assert count >= 0


def test_get_revision_not_found_raises_404(db):
    svc = ProductService()
    with pytest.raises(EntityNotFoundException) as exc:
        svc.get_revision(db, WS, "NONEXISTENT-PART", "A")
    assert exc.value.key == "PartRevisionNotFoundException"


def test_get_latest_revision_not_found_raises_404(db):
    svc = ProductService()
    with pytest.raises(PartMasterNotFoundException) as exc:
        svc.get_latest_revision(db, WS, "NONEXISTENT-PART")
    assert exc.value.key == "PartMasterNotFoundException"


def test_find_or_create_creates_when_missing(db):
    import uuid
    svc = ProductService()
    fake_number = f"TEST-{uuid.uuid4().hex[:8].upper()}"
    master = svc.find_or_create_part_master(db, WS, fake_number)
    assert master.number == fake_number
    # 清理
    db.delete(master)
    db.commit()

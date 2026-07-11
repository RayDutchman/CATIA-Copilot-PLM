from app.services.product_structure import ProductStructureService
from app.core.exceptions import EntityAlreadyExistsException
WS = "GD50"
svc = ProductStructureService()


def test_create_ci(db):
    ci = svc.create_ci(db, WS, "P3SVC-1", "Test", "Assem1", "test1")
    assert ci.id == "P3SVC-1"
    assert ci.partmaster_partnumber == "Assem1"
    svc.delete_ci(db, WS, "P3SVC-1")


def test_ci_already_exists(db):
    svc.create_ci(db, WS, "P3SVC-2", "T", "Assem1", "test1")
    try:
        svc.create_ci(db, WS, "P3SVC-2", "T", "Assem1", "test1")
        assert False
    except EntityAlreadyExistsException as e:
        assert "ConfigurationItem" in e.key
    svc.delete_ci(db, WS, "P3SVC-2")


def test_filter_structure(db):
    ci = svc.create_ci(db, WS, "P3SVC-3", "T", "Assem1", "test1")
    tree = svc.filter_product_structure(db, WS, "P3SVC-3")
    assert len(tree) == 1
    root = tree[0]
    assert root["number"] == "Assem1"
    assert "components" in root
    svc.delete_ci(db, WS, "P3SVC-3")

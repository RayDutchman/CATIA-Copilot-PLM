from app.core.database import SessionLocal
from app.models.product import ConfigurationItem, ProductBaseline
from app.models.part import CADInstance


def test_tables_exist():
    db = SessionLocal()
    assert ConfigurationItem.__tablename__ == "configurationitem"
    assert ProductBaseline.__tablename__ == "productbaseline"
    assert CADInstance.__tablename__ == "cadinstance"
    db.close()


def test_cadinstance_count():
    db = SessionLocal()
    count = db.query(CADInstance).count()
    assert count >= 100
    db.close()

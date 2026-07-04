"""零件 ORM 模型测试。"""
from app.core.database import engine
from sqlalchemy import inspect


def test_partmaster_table_exists():
    insp = inspect(engine)
    assert "partmaster" in insp.get_table_names()


def test_partrevision_table_exists():
    insp = inspect(engine)
    assert "partrevision" in insp.get_table_names()


def test_partiteration_table_exists():
    insp = inspect(engine)
    assert "partiteration" in insp.get_table_names()


def test_orm_query_partmaster(db):
    from app.models.part import PartMaster
    result = db.query(PartMaster).limit(1).all()
    assert isinstance(result, list)


def test_orm_query_partrevision(db):
    from app.models.part import PartRevision
    result = db.query(PartRevision).limit(1).all()
    assert isinstance(result, list)

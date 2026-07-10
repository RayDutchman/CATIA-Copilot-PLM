"""Task 4: PathData 查询执行器测试。"""
from app.core.database import SessionLocal
from app.services.query_executor import build_pathdata_where, run_pathdata_query


def test_build_pathdata_where_attr_exists():
    params = {}
    rule = {"condition": None, "field": "pd-attr-TEXT.color", "type": "string",
            "operator": "equal", "values": ["red"], "rules": []}
    where = build_pathdata_where(rule, params)
    assert "EXISTS" in where
    assert "pathdataiteration_attribute" in where
    assert "ia.textvalue =" in where
    assert "red" in params.values()
    assert "InstanceTextAttribute" in params.values()


def test_build_pathdata_where_and_nesting():
    params = {}
    rule = {"condition": "AND", "field": None, "operator": None, "type": None, "values": [],
            "rules": [
                {"condition": None, "field": "pd-attr-NUMBER.torque", "type": "double",
                 "operator": "greater", "values": ["10"], "rules": []},
                {"condition": None, "field": "pd-attr-BOOLEAN.active", "type": "boolean",
                 "operator": "equal", "values": ["true"], "rules": []},
            ]}
    where = build_pathdata_where(rule, params)
    assert " AND " in where
    assert 10.0 in params.values()
    assert True in params.values()


def test_run_pathdata_query_no_paths_returns_empty_set():
    db = SessionLocal()
    try:
        pii_key = {"workspace_id": "NO_SUCH_WS", "configurationitem_id": "NONE",
                   "serialnumber": "NONE", "iteration": 1}
        res = run_pathdata_query(db, pii_key, None)
        assert res == set()
    finally:
        db.close()

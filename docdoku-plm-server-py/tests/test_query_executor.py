"""Task 2: PartRevision 查询执行器测试。"""
from app.core.database import SessionLocal
from app.services.query_executor import run_part_query, build_part_where


def test_build_where_pm_number_equal():
    params = {"__ws": "WS"}
    joins = set()
    rule = {"condition": None, "field": "pm.number", "type": "string",
            "operator": "equal", "values": ["ABC"], "rules": []}
    where = build_part_where(rule, params, joins)
    assert "pm.partnumber" in where
    assert "ABC" in params.values()


def test_build_where_and_or_nesting():
    params = {"__ws": "WS"}
    joins = set()
    rule = {"condition": "OR", "field": None, "operator": None, "type": None, "values": [],
            "rules": [
                {"condition": None, "field": "pm.name", "type": "string",
                 "operator": "contains", "values": ["gear"], "rules": []},
                {"condition": None, "field": "pm.type", "type": "string",
                 "operator": "equal", "values": ["assembly"], "rules": []},
            ]}
    where = build_part_where(rule, params, joins)
    assert " OR " in where and where.strip().startswith("(")
    assert "%gear%" in params.values()


def test_build_where_attr_number_greater_uses_exists():
    params = {"__ws": "WS"}
    rule = {"condition": None, "field": "attr-NUMBER.weight", "type": "double",
            "operator": "greater", "values": ["5"], "rules": []}
    where = build_part_where(rule, params)
    assert "EXISTS" in where
    assert "instanceattribute" in where
    assert "ia.numbervalue >" in where
    assert 5.0 in params.values()
    assert "InstanceNumberAttribute" in params.values()


def test_build_where_date_equal_expands_to_day_range():
    params = {"__ws": "WS"}
    rule = {"condition": None, "field": "pr.creationDate", "type": "date",
            "operator": "equal", "values": ["2024-01-01"], "rules": []}
    where = build_part_where(rule, params)
    assert ">=" in where and "<" in where


def test_build_where_pr_status_maps_enum():
    params = {"__ws": "WS"}
    rule = {"condition": None, "field": "pr.status", "type": "status",
            "operator": "equal", "values": ["RELEASED"], "rules": []}
    where = build_part_where(rule, params)
    assert "pr.status =" in where
    assert 1 in params.values()


def test_build_where_pr_tags_uses_tag_join():
    params = {"__ws": "WS"}
    rule = {"condition": None, "field": "pr.tags", "type": "string",
            "operator": "equal", "values": ["urgent"], "rules": []}
    where = build_part_where(rule, params)
    assert "partrevision_tag" in where
    assert "urgent" in params.values()


def test_run_part_query_returns_list():
    db = SessionLocal()
    try:
        query = {"queryRule": {"condition": "AND", "rules": [], "field": None,
                               "operator": None, "type": None, "values": []},
                 "pathDataQueryRule": None, "contexts": []}
        res = run_part_query(db, "测试用工作区", query, "e", True)
        assert isinstance(res, list)
    finally:
        db.close()

import pytest
from sqlalchemy import text
from app.routers.parts import _save_query, _load_query_rule


def test_save_query_writes_rule_tree_and_selects(db):
    """保存查询：写入 queryrule 树、selects 等子表，可回读验证。"""
    body = {
        "name": "SEED-Q-SAVE-1",
        "queryRule": {
            "condition": "AND", "operator": None, "field": None, "type": None,
            "values": [],
            "rules": [
                {"condition": None, "field": "pm.number", "type": "string",
                 "operator": "equal", "values": ["SEED-PART-1"], "rules": []},
                {"condition": None, "field": "pr.status", "type": "status",
                 "operator": "equal", "values": ["1"], "rules": []},
            ],
        },
        "pathDataQueryRule": None,
        "selects": ["pm.number", "pr.version"],
        "orderByList": ["pm.number"],
        "groupedByList": [],
        "contexts": [],
    }
    # 用测试用工作区 和用户 e（userdata 中已存在的外键）
    qid = _save_query(db, "测试工作区", "e", body)
    db.commit()  # RollbackSession: flush 不真正提交，但同一事务内可读
    assert isinstance(qid, int) and qid > 0
    row = db.execute(text("SELECT name, queryrule_id FROM query WHERE id=:q"),
                     {"q": qid}).fetchone()
    assert row[0] == "SEED-Q-SAVE-1"
    rule = _load_query_rule(db, row[1])
    assert rule["condition"] == "AND"
    assert len(rule["rules"]) == 2
    assert {r["field"] for r in rule["rules"]} == {"pm.number", "pr.status"}
    selects = [s[0] for s in db.execute(
        text("SELECT selects FROM query_selects WHERE query_id=:q"), {"q": qid}).fetchall()]
    assert selects == ["pm.number", "pr.version"]

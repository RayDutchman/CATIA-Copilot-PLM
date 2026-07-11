"""Task 3: 自定义查询运行/保存端点测试（端到端）。"""
from fastapi.testclient import TestClient
from app.main import app

PREFIX = "/docdoku-plm-server-rest/api"
WS = "GD50"
client = TestClient(app)


def _token():
    r = client.post(f"{PREFIX}/auth/login", json={"login": "test1", "password": "password"})
    return r.headers.get("jwt")


def _empty_rule():
    return {"condition": "AND", "rules": [], "field": None,
            "operator": None, "type": None, "values": []}


def test_run_empty_query_returns_list():
    h = {"Authorization": f"Bearer {_token()}"}
    body = {"name": None, "queryRule": _empty_rule(), "pathDataQueryRule": None,
            "selects": ["pm.number", "pr.version"], "orderByList": [],
            "groupedByList": [], "contexts": []}
    r = client.post(f"{PREFIX}/workspaces/{WS}/parts/queries?export=JSON",
                    json=body, headers=h)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_csv_export_returns_400():
    h = {"Authorization": f"Bearer {_token()}"}
    body = {"name": None, "queryRule": _empty_rule(), "pathDataQueryRule": None,
            "selects": [], "orderByList": [], "groupedByList": [], "contexts": []}
    r = client.post(f"{PREFIX}/workspaces/{WS}/parts/queries?export=CSV",
                    json=body, headers=h)
    assert r.status_code == 400


def test_save_then_appears_in_get_queries():
    h = {"Authorization": f"Bearer {_token()}"}
    name = "SEED-Q-RUN-1"
    body = {"name": name,
            "queryRule": {"condition": "AND", "field": None, "operator": None,
                          "type": None, "values": [],
                          "rules": [{"condition": None, "field": "pm.type",
                                     "type": "string", "operator": "equal",
                                     "values": ["assembly"], "rules": []}]},
            "pathDataQueryRule": None, "selects": ["pm.number"],
            "orderByList": [], "groupedByList": [], "contexts": []}
    qid = None
    try:
        r = client.post(f"{PREFIX}/workspaces/{WS}/parts/queries?save=true&export=JSON",
                        json=body, headers=h)
        assert r.status_code == 200
        assert isinstance(r.json(), list)
        g = client.get(f"{PREFIX}/workspaces/{WS}/parts/queries", headers=h)
        assert g.status_code == 200
        saved = [q for q in g.json() if q.get("name") == name]
        assert saved, "保存的查询应出现在列表中"
        qid = saved[0]["id"]
        # 校验规则树回读
        rule = saved[0]["queryRule"]
        assert rule["rules"][0]["field"] == "pm.type"
    finally:
        if qid is not None:
            client.request("DELETE", f"{PREFIX}/parts/queries/{qid}", headers=h)

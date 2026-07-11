"""零件搜索测试。"""
from fastapi.testclient import TestClient
from app.main import app

PREFIX = "/docdoku-plm-server-rest/api"
WS = "GD50"
client = TestClient(app)


def _token():
    r = client.post(f"{PREFIX}/auth/login",
                    json={"login": "test1", "password": "password"})
    return r.headers.get("jwt")


def test_search_by_name_finds_seeded_part():
    token = _token(); h = {"Authorization": f"Bearer {token}"}
    resp = client.get(f"{PREFIX}/workspaces/{WS}/parts/search?name=Differential",
                      headers=h)
    assert resp.status_code == 200
    numbers = [r["number"] for r in resp.json()]
    assert any("Differential" in n for n in numbers)


def test_search_no_match_returns_empty():
    token = _token(); h = {"Authorization": f"Bearer {token}"}
    resp = client.get(f"{PREFIX}/workspaces/{WS}/parts/search?name=ZZZNOMATCH999",
                      headers=h)
    assert resp.status_code == 200
    assert resp.json() == []

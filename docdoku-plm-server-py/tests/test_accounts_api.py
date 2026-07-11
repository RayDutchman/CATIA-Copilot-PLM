from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
PREFIX = "/docdoku-plm-server-rest/api"


def _token():
    resp = client.post(f"{PREFIX}/auth/login",
                       json={"login": "test1", "password": "password"})
    return resp.headers.get("jwt", "")


def test_list_workspaces():
    resp = client.get(f"{PREFIX}/accounts/workspaces",
                      headers={"Authorization": f"Bearer {_token()}"})
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert any(w["id"] == "GD50" for w in data)

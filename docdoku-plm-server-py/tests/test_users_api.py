from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app, raise_server_exceptions=False)
PREFIX = "/docdoku-plm-server-rest/api"
WS = "GD50"


def _token():
    resp = client.post(f"{PREFIX}/auth/login",
                       json={"login": "test1", "password": "password"})
    return resp.headers.get("jwt", "")


def _h():
    return {"Authorization": f"Bearer {_token()}"}


def test_list_users():
    resp = client.get(f"{PREFIX}/workspaces/{WS}/users", headers=_h())
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert any(u["login"] == "test1" for u in data)


def test_who_am_i():
    resp = client.get(f"{PREFIX}/workspaces/{WS}/users/me", headers=_h())
    assert resp.status_code == 200
    assert resp.json()["login"] == "test1"


def test_list_groups():
    resp = client.get(f"{PREFIX}/workspaces/{WS}/groups", headers=_h())
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_list_memberships():
    resp = client.get(f"{PREFIX}/workspaces/{WS}/memberships/users", headers=_h())
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert any(m["member"]["login"] == "test1" for m in data)

from fastapi.testclient import TestClient
from app.main import app
PREFIX = "/docdoku-plm-server-rest/api"
WS = "GD50"
client = TestClient(app)


def _token():
    r = client.post(f"{PREFIX}/auth/login", json={"login":"test1","password":"password"})
    return r.headers.get("jwt")


def test_issue_create_list_delete():
    token = _token()
    h = {"Authorization": f"Bearer {token}"}
    resp = client.post(f"{PREFIX}/workspaces/{WS}/changes/issues",
                       json={"name": "API Issue", "description": "d"}, headers=h)
    assert resp.status_code == 201
    assert resp.json()["name"] == "API Issue"
    item_id = resp.json()["id"]
    # list
    lst = client.get(f"{PREFIX}/workspaces/{WS}/changes/issues", headers=h)
    assert any(i["id"] == item_id for i in lst.json())
    # delete
    d = client.request("DELETE",
                       f"{PREFIX}/workspaces/{WS}/changes/issues/{item_id}", headers=h)
    assert d.status_code == 204

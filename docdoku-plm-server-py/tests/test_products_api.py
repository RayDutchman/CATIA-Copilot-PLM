from fastapi.testclient import TestClient
from app.main import app
PREFIX = "/docdoku-plm-server-rest/api"
WS = "Workspace_2"
client = TestClient(app)

def _token():
    r = client.post(f"{PREFIX}/auth/login", json={"login":"test1","password":"password"})
    return r.headers.get("jwt")

def test_create_and_filter():
    token = _token(); h = {"Authorization": f"Bearer {token}"}
    resp = client.post(f"{PREFIX}/workspaces/{WS}/products/",
                       json={"id":"P3API-1","description":"T","partNumber":"Assem1"}, headers=h)
    assert resp.status_code == 201
    # filter
    resp2 = client.get(f"{PREFIX}/workspaces/{WS}/products/P3API-1/filter?depth=2", headers=h)
    assert resp2.status_code == 200
    tree = resp2.json()
    assert len(tree) >= 1
    assert tree[0]["number"] == "Assem1"
    # cleanup
    client.request("DELETE", f"{PREFIX}/workspaces/{WS}/products/P3API-1", headers=h)

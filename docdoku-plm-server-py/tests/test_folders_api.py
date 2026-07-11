from fastapi.testclient import TestClient
from app.main import app
PREFIX = "/docdoku-plm-server-rest/api"
WS = "GD50"
client = TestClient(app)


def _token():
    r = client.post(f"{PREFIX}/auth/login", json={"login":"test1","password":"password"})
    return r.headers.get("jwt")


def test_create_and_delete_folder():
    token = _token(); h = {"Authorization": f"Bearer {token}"}
    folder_name = f"P2FOLDER-{hash(token) % 100000}"
    resp = client.post(f"{PREFIX}/workspaces/{WS}/folders",
                       json={"name": folder_name}, headers=h)
    assert resp.status_code == 201
    path = resp.json()["path"]
    # 删除
    resp2 = client.request("DELETE",
                           f"{PREFIX}/workspaces/{WS}/folders/{path}", headers=h)
    assert resp2.status_code == 204

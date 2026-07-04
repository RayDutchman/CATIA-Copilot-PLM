from fastapi.testclient import TestClient
from app.main import app
PREFIX = "/docdoku-plm-server-rest/api"
WS = "Workspace_2"
client = TestClient(app)


def _token():
    r = client.post(f"{PREFIX}/auth/login", json={"login":"test1","password":"password"})
    return r.headers.get("jwt")


def _cleanup(h, doc_id, ver="A"):
    client.put(f"{PREFIX}/workspaces/{WS}/documents/{doc_id}-{ver}/checkin", headers=h)
    client.request("DELETE", f"{PREFIX}/workspaces/{WS}/documents/{doc_id}-{ver}", headers=h)


def test_create_and_delete():
    token = _token(); h = {"Authorization": f"Bearer {token}"}
    doc_id = "P2API-1"
    resp = client.post(f"{PREFIX}/workspaces/{WS}/documents",
                       json={"reference": doc_id, "title": "Test"}, headers=h)
    assert resp.status_code == 201
    _cleanup(h, doc_id)

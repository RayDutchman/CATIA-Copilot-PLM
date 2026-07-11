from fastapi.testclient import TestClient
from app.main import app
PREFIX = "/docdoku-plm-server-rest/api"
WS = "GD50"
client = TestClient(app)


def _token():
    r = client.post(f"{PREFIX}/auth/login", json={"login":"test1","password":"password"})
    return r.headers.get("jwt")


def test_create_list_delete():
    token = _token(); h = {"Authorization": f"Bearer {token}"}
    tid = f"P2TPL-{hash(token) % 100000}"
    # 创建
    resp = client.post(f"{PREFIX}/workspaces/{WS}/document-templates",
                       json={"reference": tid, "documentType": "doc"}, headers=h)
    assert resp.status_code == 201
    # 列表
    resp2 = client.get(f"{PREFIX}/workspaces/{WS}/document-templates", headers=h)
    assert any(t["id"] == tid for t in resp2.json())
    # 删除
    resp3 = client.request("DELETE",
                           f"{PREFIX}/workspaces/{WS}/document-templates/{tid}", headers=h)
    assert resp3.status_code == 200


def test_generate_id():
    """GET .../document-templates/{id}/generate_id 返回 generatedId。"""
    token = _token(); h = {"Authorization": f"Bearer {token}"}
    tid = f"P2GEN-{hash(token) % 100000}"
    client.post(f"{PREFIX}/workspaces/{WS}/document-templates",
                json={"reference": tid, "documentType": "doc", "idGenerated": True}, headers=h)
    resp = client.get(f"{PREFIX}/workspaces/{WS}/document-templates/{tid}/generate_id", headers=h)
    assert resp.status_code == 200
    assert resp.json() == {"generateId": f"{tid}-001"}
    client.request("DELETE", f"{PREFIX}/workspaces/{WS}/document-templates/{tid}", headers=h)

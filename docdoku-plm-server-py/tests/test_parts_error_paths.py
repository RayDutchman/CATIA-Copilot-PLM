from fastapi.testclient import TestClient
from app.main import app

PREFIX = "/docdoku-plm-server-rest/api"
WS = "Workspace_2"
client = TestClient(app, raise_server_exceptions=False)


def _token():
    resp = client.post(f"{PREFIX}/auth/login",
                       json={"login": "test1", "password": "password"})
    return resp.headers.get("jwt")


def test_delete_part_used_as_component_returns_403_zh():
    """test1 是 zh 用户，删被用作组件的零件应返回 403 + 中文消息。"""
    token = _token()
    resp = client.request(
        "DELETE",
        f"{PREFIX}/workspaces/{WS}/parts/Differential Axle 2010-A",
        headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403
    assert resp.json()["message"] == "您无法删除在装配体中用作组件的零件"

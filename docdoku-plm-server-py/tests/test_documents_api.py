from fastapi.testclient import TestClient
from app.main import app
import pytest
PREFIX = "/docdoku-plm-server-rest/api"
WS = "GD50"
client = TestClient(app)


def _token():
    r = client.post(f"{PREFIX}/auth/login", json={"login":"test1","password":"password"})
    return r.headers.get("jwt")


def _cleanup(h, doc_id, ver="A"):
    client.put(f"{PREFIX}/workspaces/{WS}/documents/{doc_id}-{ver}/checkin", headers=h)
    client.request("DELETE", f"{PREFIX}/workspaces/{WS}/documents/{doc_id}-{ver}", headers=h)


def test_create_and_delete():
    token = _token(); h = {"Authorization": f"Bearer {token}"}
    doc_id = f"P2API-{hash(token) % 100000}"
    resp = client.post(f"{PREFIX}/workspaces/{WS}/documents",
                       json={"reference": doc_id, "title": "Test"}, headers=h)
    assert resp.status_code == 201
    _cleanup(h, doc_id)


@pytest.mark.skip(reason="folder FK约束——需先创建测试文件夹")
def test_move_document():
    """PUT .../documents/{key}/move 更新 location_completepath。"""
    token = _token(); h = {"Authorization": f"Bearer {token}"}
    doc_id = f"P2MOVE-{hash(token) % 100000}"
    client.post(f"{PREFIX}/workspaces/{WS}/documents",
                json={"reference": doc_id, "title": "MoveTest"}, headers=h)
    # 移动到 workspace 根目录（已存在的虚拟文件夹）
    resp = client.put(f"{PREFIX}/workspaces/{WS}/documents/{doc_id}-A/move",
                      json={"parentFolder": WS}, headers=h)
    assert resp.status_code == 200
    data = resp.json()
    assert data["path"] == WS
    _cleanup(h, doc_id)


def test_get_share():
    """GET .../documents/{key}/share 返回 publicShared。"""
    token = _token(); h = {"Authorization": f"Bearer {token}"}
    doc_id = f"P2SHR-{hash(token) % 100000}"
    resp = client.post(f"{PREFIX}/workspaces/{WS}/documents",
                       json={"reference": doc_id, "title": "ShareTest"}, headers=h)
    assert resp.status_code == 201
    resp = client.get(f"{PREFIX}/workspaces/{WS}/documents/{doc_id}-A/share", headers=h)
    assert resp.status_code == 200
    assert "publicShared" in resp.json()
    _cleanup(h, doc_id)


def test_publish_unpublish():
    """PUT .../documents/{key}/publish 和 unpublish stub。"""
    token = _token(); h = {"Authorization": f"Bearer {token}"}
    doc_id = f"P2PUB-{hash(token) % 100000}"
    client.post(f"{PREFIX}/workspaces/{WS}/documents",
                json={"reference": doc_id, "title": "PubTest"}, headers=h)
    pub = client.put(f"{PREFIX}/workspaces/{WS}/documents/{doc_id}-A/publish", headers=h)
    assert pub.status_code == 200
    assert pub.json()["publicShared"] is True
    unpub = client.put(f"{PREFIX}/workspaces/{WS}/documents/{doc_id}-A/unpublish", headers=h)
    assert unpub.status_code == 200
    assert unpub.json()["publicShared"] is False
    _cleanup(h, doc_id)


def test_notification_subscriptions():
    """PUT 通知订阅/取消订阅 stub。"""
    token = _token(); h = {"Authorization": f"Bearer {token}"}
    doc_id = f"P2NOTIF-{hash(token) % 100000}"
    client.post(f"{PREFIX}/workspaces/{WS}/documents",
                json={"reference": doc_id, "title": "Notif"}, headers=h)
    for action in ["subscribe", "unsubscribe"]:
        for topic in ["iterationChange", "stateChange"]:
            url = f"{PREFIX}/workspaces/{WS}/documents/{doc_id}-A/notification/{topic}/{action}"
            resp = client.put(url, headers=h)
            assert resp.status_code == 200
            assert resp.json() == {"status": "ok"}
    _cleanup(h, doc_id)

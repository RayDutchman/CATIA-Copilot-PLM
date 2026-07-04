"""零件 API 端点测试。"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
PREFIX = "/docdoku-plm-server-rest/api"
WS = "Workspace_2"  # 数据库中实际存在的 workspace


def get_token():
    """用 test1 登录（Workspace_2 成员，admin 不是该 workspace 成员）。"""
    resp = client.post(f"{PREFIX}/auth/login",
                       json={"login": "test1", "password": "password"})
    return resp.headers["jwt"]


def test_list_parts_requires_auth():
    resp = client.get(f"{PREFIX}/workspaces/{WS}/parts")
    assert resp.status_code == 401


def test_list_parts_returns_list():
    token = get_token()
    resp = client.get(f"{PREFIX}/workspaces/{WS}/parts",
                      headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_count_parts():
    token = get_token()
    resp = client.get(f"{PREFIX}/workspaces/{WS}/parts/count",
                      headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert "count" in resp.json()


def test_create_and_get_and_delete_part():
    import uuid
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}
    number = f"TEST-{uuid.uuid4().hex[:8].upper()}"
    # 创建
    resp = client.post(f"{PREFIX}/workspaces/{WS}/parts",
                       json={"number": number, "name": "Test Part"},
                       headers=headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["number"] == number
    assert data["version"] == "A"
    assert data["checkOutUser"] is not None   # 创建后自动签出
    # 获取
    resp2 = client.get(f"{PREFIX}/workspaces/{WS}/parts/{number}-A",
                       headers=headers)
    assert resp2.status_code == 200
    # 签入后删除
    client.put(f"{PREFIX}/workspaces/{WS}/parts/{number}-A/checkin",
               headers=headers)
    resp3 = client.delete(f"{PREFIX}/workspaces/{WS}/parts/{number}-A",
                          headers=headers)
    assert resp3.status_code == 204


def test_latest_revision_not_found():
    token = get_token()
    resp = client.get(
        f"{PREFIX}/workspaces/{WS}/parts/NONEXISTENT-XYZ/latest-revision",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 404


def test_checkout_checkin_cycle():
    import uuid
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}
    number = f"CKO-{uuid.uuid4().hex[:6].upper()}"
    # 创建（自动签出）
    client.post(f"{PREFIX}/workspaces/{WS}/parts",
                json={"number": number}, headers=headers)
    # 签入
    resp = client.put(
        f"{PREFIX}/workspaces/{WS}/parts/{number}-A/checkin",
        headers=headers)
    assert resp.status_code == 200
    assert resp.json()["checkOutUser"] is None
    # 签出
    resp2 = client.put(
        f"{PREFIX}/workspaces/{WS}/parts/{number}-A/checkout",
        headers=headers)
    assert resp2.status_code == 200
    assert resp2.json()["checkOutUser"]["login"] == "test1"
    # 撤销签出
    resp3 = client.put(
        f"{PREFIX}/workspaces/{WS}/parts/{number}-A/undocheckout",
        headers=headers)
    assert resp3.status_code == 200
    assert resp3.json()["checkOutUser"] is None
    # 清理
    client.delete(f"{PREFIX}/workspaces/{WS}/parts/{number}-A",
                  headers=headers)

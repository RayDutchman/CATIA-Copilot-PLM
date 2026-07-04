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


def test_update_iteration_with_components():
    """验收标准 #3：更新迭代含子件的完整流程。"""
    import uuid
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}
    parent = f"ASM-{uuid.uuid4().hex[:6].upper()}"
    child = f"CHILD-{uuid.uuid4().hex[:6].upper()}"
    # 创建父件（自动签出）和子件
    client.post(f"{PREFIX}/workspaces/{WS}/parts",
                json={"number": parent, "name": "Assembly"}, headers=headers)
    client.post(f"{PREFIX}/workspaces/{WS}/parts",
                json={"number": child, "name": "Child"}, headers=headers)
    # 签入子件（创建时自动签出）
    client.put(f"{PREFIX}/workspaces/{WS}/parts/{child}-A/checkin",
               headers=headers)
    # 更新父件迭代，添加子件为 BOM 组件
    resp = client.put(
        f"{PREFIX}/workspaces/{WS}/parts/{parent}-A/iterations/1",
        json={"components": [{
            "amount": 2,
            "component": {"number": child, "name": "Child"},
        }]},
        headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    # 验证 BOM 写入
    assert len(data["partIterations"]) >= 1
    comps = data["partIterations"][-1]["components"]
    assert len(comps) == 1
    assert comps[0]["component"]["number"] == child
    assert comps[0]["amount"] == 2
    # 再次更新（替换 BOM），验证旧关联被清理
    child2 = f"CHILD2-{uuid.uuid4().hex[:6].upper()}"
    client.post(f"{PREFIX}/workspaces/{WS}/parts",
                json={"number": child2}, headers=headers)
    client.put(f"{PREFIX}/workspaces/{WS}/parts/{child2}-A/checkin",
               headers=headers)
    resp2 = client.put(
        f"{PREFIX}/workspaces/{WS}/parts/{parent}-A/iterations/1",
        json={"components": [{
            "amount": 1,
            "component": {"number": child2, "name": "Child2"},
        }]},
        headers=headers)
    assert resp2.status_code == 200
    comps2 = resp2.json()["partIterations"][-1]["components"]
    assert len(comps2) == 1
    assert comps2[0]["component"]["number"] == child2
    # 清理
    client.put(f"{PREFIX}/workspaces/{WS}/parts/{parent}-A/checkin",
               headers=headers)
    client.delete(f"{PREFIX}/workspaces/{WS}/parts/{parent}-A", headers=headers)
    client.delete(f"{PREFIX}/workspaces/{WS}/parts/{child}-A", headers=headers)
    client.delete(f"{PREFIX}/workspaces/{WS}/parts/{child2}-A", headers=headers)

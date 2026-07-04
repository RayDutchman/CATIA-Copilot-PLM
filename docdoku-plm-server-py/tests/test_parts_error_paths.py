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


# ── Task 8: 签出/签入/撤销签出对齐 ──────────────────────────

import uuid


def test_checkout_already_checked_out_returns_403():
    """对已签出的零件再签出应返回 403 + NotAllowedException37 翻译。"""
    token = _token()
    h = {"Authorization": f"Bearer {token}"}
    num = "ERRPATH-CO-" + uuid.uuid4().hex[:8]
    client.post(f"{PREFIX}/workspaces/{WS}/parts",
                json={"number": num, "name": "t"}, headers=h)
    # 新建即自动签出；再次签出应失败
    resp = client.put(f"{PREFIX}/workspaces/{WS}/parts/{num}-A/checkout", headers=h)
    assert resp.status_code == 403
    assert resp.json()["message"] == "该项目已被签出"
    # 清理：直接通过 API 删除（先签入再删，或直接 UNDO+DROP）
    client.put(f"{PREFIX}/workspaces/{WS}/parts/{num}-A/checkin", headers=h)
    client.request("DELETE", f"{PREFIX}/workspaces/{WS}/parts/{num}-A", headers=h)


# ── Task 9: createPartMaster/updatePartIteration 对齐 ──────────

def test_create_duplicate_part_returns_409():
    token = _token()
    h = {"Authorization": f"Bearer {token}"}
    num = "ERRPATH-DUP-" + uuid.uuid4().hex[:8]
    client.post(f"{PREFIX}/workspaces/{WS}/parts",
                json={"number": num, "name": "t"}, headers=h)
    # 重复创建
    resp = client.post(f"{PREFIX}/workspaces/{WS}/parts",
                       json={"number": num, "name": "t"}, headers=h)
    assert resp.status_code == 409
    assert resp.json()["message"] == f'零件"{num}"已存在'
    # 清理
    client.put(f"{PREFIX}/workspaces/{WS}/parts/{num}-A/checkin", headers=h)
    client.request("DELETE", f"{PREFIX}/workspaces/{WS}/parts/{num}-A", headers=h)

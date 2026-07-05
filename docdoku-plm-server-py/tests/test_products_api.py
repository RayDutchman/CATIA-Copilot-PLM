from fastapi.testclient import TestClient
from app.main import app
from app.core import i18n
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
    assert isinstance(tree, dict)
    assert tree["number"] == "Assem1"
    # cleanup
    client.request("DELETE", f"{PREFIX}/workspaces/{WS}/products/P3API-1", headers=h)


def test_ci_already_exists_returns_409():
    """创建重复 CI 应返回 409 + 中文 i18n 翻译。"""
    token = _token(); h = {"Authorization": f"Bearer {token}"}
    resp = client.post(f"{PREFIX}/workspaces/{WS}/products/",
                       json={"id": "P3DUP-1", "designItemNumber": "Assem1"}, headers=h)
    assert resp.status_code == 201
    resp2 = client.post(f"{PREFIX}/workspaces/{WS}/products/",
                        json={"id": "P3DUP-1", "designItemNumber": "Assem1"}, headers=h)
    assert resp2.status_code == 409
    expected = i18n.get("ConfigurationItemAlreadyExistsException", "zh", "P3DUP-1")
    assert resp2.text == expected
    client.request("DELETE", f"{PREFIX}/workspaces/{WS}/products/P3DUP-1", headers=h)


def test_ci_part_not_found_returns_404():
    """不存在的根零件应返回 404 中文提示。"""
    token = _token(); h = {"Authorization": f"Bearer {token}"}
    resp = client.post(f"{PREFIX}/workspaces/{WS}/products/",
                       json={"id": "P3NO-2", "designItemNumber": "ZZZ-NOPE-99999"}, headers=h)
    assert resp.status_code == 404
    assert "未找到零件" in resp.text


def test_ci_not_found_returns_404():
    """获取不存在的 CI 应返回 404。"""
    token = _token(); h = {"Authorization": f"Bearer {token}"}
    resp = client.get(f"{PREFIX}/workspaces/{WS}/products/P3-NOEXIST", headers=h)
    assert resp.status_code == 404

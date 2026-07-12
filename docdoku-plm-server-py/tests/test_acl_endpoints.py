"""ACL 端点测试——parts / documents / products / document-templates。"""
import uuid
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
PREFIX = "/docdoku-plm-server-rest/api"
WS = "GD50"
FULL_ACCESS = 2  # Java ACLPermission enum ordinal


def _token():
    resp = client.post(f"{PREFIX}/auth/login",
                       json={"login": "test1", "password": "password"})
    return resp.headers["jwt"]


def test_set_part_acl():
    token = _token()
    h = {"Authorization": f"Bearer {token}"}
    num = "ACLTEST-" + uuid.uuid4().hex[:6].upper()
    client.post(f"{PREFIX}/workspaces/{WS}/parts",
                json={"number": num, "name": "acl test part"}, headers=h)
    resp = client.put(f"{PREFIX}/workspaces/{WS}/parts/{num}-A/acl",
                      json={"userEntries": {"test1": FULL_ACCESS},
                            "groupEntries": {}},
                      headers=h)
    assert resp.status_code == 204


def test_set_doc_acl():
    token = _token()
    h = {"Authorization": f"Bearer {token}"}
    ref = "ACLDOC-" + uuid.uuid4().hex[:6].upper()
    client.post(f"{PREFIX}/workspaces/{WS}/documents",
                json={"reference": ref, "title": "acl test doc"}, headers=h)
    resp = client.put(f"{PREFIX}/workspaces/{WS}/documents/{ref}-A/acl",
                      json={"userEntries": {"test1": FULL_ACCESS},
                            "groupEntries": {}},
                      headers=h)
    assert resp.status_code == 204


def test_set_config_acl():
    token = _token()
    h = {"Authorization": f"Bearer {token}"}
    num = "ACLCFG-" + uuid.uuid4().hex[:6].upper()
    ci_id = "ACLCI-" + uuid.uuid4().hex[:6].upper()
    # 先创建零件
    client.post(f"{PREFIX}/workspaces/{WS}/parts",
                json={"number": num, "name": "acl test part"}, headers=h)
    # 创建 CI（引用零件）
    client.post(f"{PREFIX}/workspaces/{WS}/products",
                json={"id": ci_id, "description": "acl test ci",
                      "designItemNumber": num}, headers=h)
    # 创建配置
    cfg_resp = client.post(f"{PREFIX}/workspaces/{WS}/products/{ci_id}/configurations",
                           json={"name": "acl test config"}, headers=h)
    cfg_id = cfg_resp.json()["id"]
    resp = client.put(f"{PREFIX}/workspaces/{WS}/products/{ci_id}/configurations/{cfg_id}/acl",
                      json={"userEntries": {"test1": FULL_ACCESS},
                            "groupEntries": {}},
                      headers=h)
    assert resp.status_code in (200, 201)
    data = resp.json()
    assert "aclId" in data
    assert isinstance(data["aclId"], int)


def test_set_template_acl():
    token = _token()
    h = {"Authorization": f"Bearer {token}"}
    tpl_id = "ACLTPL-" + uuid.uuid4().hex[:6].upper()
    client.post(f"{PREFIX}/workspaces/{WS}/document-templates",
                json={"reference": tpl_id, "documentType": "doc", "mask": "M-***",
                      "idGenerated": False},
                headers=h)
    resp = client.put(f"{PREFIX}/workspaces/{WS}/document-templates/{tpl_id}/acl",
                      json={"userEntries": {"test1": FULL_ACCESS},
                            "groupEntries": {}},
                      headers=h)
    assert resp.status_code in (200, 201)
    data = resp.json()
    assert "aclId" in data
    assert isinstance(data["aclId"], int)


def test_part_acl_auth_required():
    resp = client.put(f"{PREFIX}/workspaces/{WS}/parts/NOEXIST-A/acl",
                      json={"userEntries": {}, "groupEntries": {}})
    assert resp.status_code == 401


def test_doc_acl_auth_required():
    resp = client.put(f"{PREFIX}/workspaces/{WS}/documents/NOEXIST-A/acl",
                      json={"userEntries": {}, "groupEntries": {}})
    assert resp.status_code == 401

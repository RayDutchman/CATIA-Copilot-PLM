"""P5 Task 10: Auth 补全端点测试。"""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app, raise_server_exceptions=False)
PREFIX = "/docdoku-plm-server-rest/api"


def test_logout():
    """GET /auth/logout 返回 204 No Content。"""
    resp = client.get(f"{PREFIX}/auth/logout")
    assert resp.status_code == 204


def test_recovery_unknown_user():
    """POST /auth/recovery 对不存在的用户也返回 204（不暴露用户存在性）。"""
    resp = client.post(f"{PREFIX}/auth/recovery", json={"login": "nonexistent_user_12345"})
    assert resp.status_code == 204


def test_recovery_known_user():
    """POST /auth/recovery 对已知用户返回 204。"""
    resp = client.post(f"{PREFIX}/auth/recovery", json={"login": "admin"})
    assert resp.status_code == 204


def test_provider_not_found():
    """GET /auth/providers/{id} 当前无配置，返回 404。"""
    resp = client.get(f"{PREFIX}/auth/providers/google")
    assert resp.status_code == 404


def test_oauth_not_implemented():
    """POST /auth/oauth 当前无 OAuth 配置，返回 501。"""
    resp = client.post(f"{PREFIX}/auth/oauth", json={"provider": "google"})
    assert resp.status_code == 501


def test_recover_missing_fields():
    """POST /auth/recover 缺少必填字段返回 500（CreationException）。"""
    resp = client.post(f"{PREFIX}/auth/recover", json={"login": "admin"})
    assert resp.status_code == 500


def test_recover_unknown_user():
    """POST /auth/recover 用户不存在返回 404。"""
    resp = client.post(f"{PREFIX}/auth/recover", json={"login": "nobody", "password": "x"})
    assert resp.status_code == 404

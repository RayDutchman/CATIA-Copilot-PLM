import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
PREFIX = "/docdoku-plm-server-rest/api"

def test_login_success_returns_jwt_header():
    """登录成功后，响应头中必须包含 jwt 字段（Backbone 前端依赖此行为）。"""
    resp = client.post(f"{PREFIX}/auth/login",
                       json={"login": "admin", "password": "password"})
    assert resp.status_code == 200
    assert "jwt" in resp.headers
    assert len(resp.headers["jwt"]) > 10

def test_login_returns_account_dto():
    """登录响应体包含账号信息。"""
    resp = client.post(f"{PREFIX}/auth/login",
                       json={"login": "admin", "password": "password"})
    body = resp.json()
    assert body["login"] == "admin"
    assert "email" in body

def test_login_wrong_password():
    """密码错误返回 403。"""
    resp = client.post(f"{PREFIX}/auth/login",
                       json={"login": "admin", "password": "wrongpass"})
    assert resp.status_code == 403

def test_login_unknown_user():
    """不存在的用户返回 403。"""
    resp = client.post(f"{PREFIX}/auth/login",
                       json={"login": "nobody", "password": "x"})
    assert resp.status_code == 403

def test_me_requires_auth():
    """/accounts/me 无 token 返回 401。"""
    resp = client.get(f"{PREFIX}/accounts/me")
    assert resp.status_code == 401

def test_me_with_valid_token():
    """/accounts/me 携带有效 token 返回账号信息。"""
    login_resp = client.post(f"{PREFIX}/auth/login",
                              json={"login": "admin", "password": "password"})
    token = login_resp.headers["jwt"]
    me_resp = client.get(f"{PREFIX}/accounts/me",
                          headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200
    assert me_resp.json()["login"] == "admin"

import time
from app.core.security import create_token, verify_token, hash_password, verify_password

def test_create_and_verify_token():
    """创建 token 后能正确验证并取出 payload。"""
    token = create_token("admin", "ADMIN_ROLE_ID")
    payload = verify_token(token)
    assert payload["login"] == "admin"
    assert payload["groupName"] == "ADMIN_ROLE_ID"

def test_token_subject_is_nested_json():
    """subject 必须是嵌套 JSON 字符串（与 Payara JWTokenManager 兼容）。"""
    from jose import jwt as jose_jwt
    from app.core.config import settings
    token = create_token("user1", "REGULAR_USER_ROLE_ID")
    import json
    raw = jose_jwt.decode(token, settings.JWT_KEY, algorithms=["HS256"])
    subject = json.loads(raw["sub"])
    assert subject["login"] == "user1"
    assert subject["groupName"] == "REGULAR_USER_ROLE_ID"

def test_hash_password_is_md5():
    """密码哈希必须是 MD5（与现有 credential 表兼容）。"""
    import hashlib
    hashed = hash_password("changeit")
    assert hashed == hashlib.md5("changeit".encode()).hexdigest()

def test_verify_password():
    """验证密码正确和错误的情况。"""
    hashed = hash_password("secret")
    assert verify_password("secret", hashed) is True
    assert verify_password("wrong", hashed) is False

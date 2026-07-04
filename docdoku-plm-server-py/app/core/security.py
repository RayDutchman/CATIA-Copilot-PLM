"""JWT 创建与验证，与 Payara JWTokenManager 行为完全兼容。"""
import json
import hashlib
import time
from jose import jwt, JWTError
from app.core.config import settings


def create_token(login: str, group_name: str) -> str:
    """
    创建 JWT token。
    subject 为嵌套 JSON 字符串，与 Payara JWTokenManager.createAuthToken() 兼容。
    """
    now = int(time.time())
    subject = json.dumps({"login": login, "groupName": group_name})
    payload = {
        "sub": subject,
        "iat": now,
        "exp": now + settings.JWT_EXPIRE_SECONDS,
    }
    return jwt.encode(payload, settings.JWT_KEY, algorithm="HS256")


def verify_token(token: str) -> dict:
    """
    验证并解析 JWT token。
    返回 {"login": str, "groupName": str, "exp": int}。
    抛出 JWTError 若 token 无效或过期。
    """
    raw = jwt.decode(token, settings.JWT_KEY, algorithms=["HS256"])
    subject = json.loads(raw["sub"])
    return {
        "login": subject["login"],
        "groupName": subject["groupName"],
        "exp": raw["exp"],
    }


def should_refresh_token(exp: int) -> bool:
    """判断 token 是否需要刷新（到期前 JWT_REFRESH_BEFORE_SECONDS 秒内）。"""
    remaining = exp - int(time.time())
    return 0 < remaining < settings.JWT_REFRESH_BEFORE_SECONDS


def hash_password(password: str) -> str:
    """MD5 哈希密码，与现有 credential 表存储格式兼容。"""
    return hashlib.md5(password.encode()).hexdigest()


def verify_password(plain: str, hashed: str) -> bool:
    """验证明文密码是否匹配 MD5 哈希。"""
    return hash_password(plain) == hashed

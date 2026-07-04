"""FastAPI 依赖项：数据库会话、当前用户认证。"""
from typing import Annotated
from fastapi import Depends, HTTPException, status, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import verify_token, create_token, should_refresh_token
from app.models.auth import Account

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    response: Response,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)] = None,
    db: Session = Depends(get_db),
) -> Account:
    """
    从 Authorization: Bearer <token> 头中提取并验证 JWT。
    若 token 即将过期，在响应头 jwt 中返回刷新后的新 token（与 Payara JWTSAM 兼容）。
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供认证 token",
        )
    try:
        payload = verify_token(credentials.credentials)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="token 无效或已过期",
        )

    # 自动刷新即将过期的 token
    if should_refresh_token(payload["exp"]):
        new_token = create_token(payload["login"], payload["groupName"])
        response.headers["jwt"] = new_token

    account = db.query(Account).filter(Account.login == payload["login"]).first()
    if account is None or not account.enabled:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="账号不存在或已禁用",
        )
    return account

"""认证相关路由：登录、登出、当前用户信息。"""
from typing import List
import hashlib
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.security import verify_password, create_token
from app.core.exceptions import (
    AccessRightException, EntityNotFoundException, CreationException,
)
from app.models.auth import Account, UserGroupMapping
from app.models.user_mgmt import Credential
from app.schemas.auth import LoginRequestDTO, AccountDTO

router = APIRouter()


@router.post("/auth/login", response_model=AccountDTO)
@router.post("/auth/login/", response_model=AccountDTO, include_in_schema=False)
def login(body: LoginRequestDTO, response: Response, db: Session = Depends(get_db)):
    """
    用户登录。
    成功后在响应头 jwt 中返回 token（Backbone 前端从此 header 读取）。
    与 Payara AuthResource.login() 行为完全一致。
    """
    account = db.query(Account).filter(Account.login == body.login).first()
    credential = db.query(Credential).filter(Credential.login == body.login).first()

    if not account or not credential or not account.enabled:
        raise AccessRightException("AccessRightException")

    if not verify_password(body.password, credential.password):
        raise AccessRightException("AccessRightException")

    # 从 usergroupmapping 表查询角色组（与 Payara UserGroupMapping 一致）
    mapping = db.query(UserGroupMapping).filter(UserGroupMapping.login == account.login).first()
    group_name = mapping.groupname if mapping else "REGULAR_USER_ROLE_ID"
    token = create_token(account.login, group_name)
    is_admin = db.query(UserGroupMapping).filter(
        UserGroupMapping.login == account.login,
        UserGroupMapping.groupname == "admin"
    ).first() is not None

    # JWT 通过响应头返回，与 Payara AuthResource 行为一致
    response.headers["jwt"] = token
    return {
        "login": account.login,
        "email": account.email or "",
        "name": account.name or "",
        "language": account.language or "en",
        "timeZone": account.timezone or "",
        "enabled": bool(account.enabled) if account.enabled is not None else True,
        "admin": is_admin,
    }


@router.get("/auth/logout", status_code=204)
@router.get("/auth/logout/", status_code=204, include_in_schema=False)
def logout():
    """登出。JWT 无状态，客户端删除本地 token 即可。返回 204。"""
    return None


@router.get("/auth/providers", response_model=List[dict])
@router.get("/auth/providers/", include_in_schema=False)
def list_providers():
    """返回外部认证提供商列表（与 Payara 一致，当前为空）。"""
    return []


@router.get("/accounts/me", response_model=AccountDTO)
@router.get("/accounts/me/", include_in_schema=False)
def get_me(current_user: Account = Depends(get_current_user),
           db: Session = Depends(get_db)):
    """返回当前登录用户的账号信息。"""
    is_admin = db.query(UserGroupMapping).filter(
        UserGroupMapping.login == current_user.login,
        UserGroupMapping.groupname == "admin"
    ).first() is not None
    return {
        "login": current_user.login,
        "email": current_user.email or "",
        "name": current_user.name or "",
        "language": current_user.language or "en",
        "timeZone": current_user.timezone or "",
        "enabled": bool(current_user.enabled) if current_user.enabled is not None else True,
        "admin": is_admin,
    }


@router.get("/auth/providers/{provider_id}", response_model=dict)
@router.get("/auth/providers/{provider_id}/", include_in_schema=False)
def get_provider(provider_id: str):
    """获取单个 OAuth provider。当前无 OAuth 配置，返回 404。"""
    raise EntityNotFoundException("OAuthProviderNotFoundException", provider_id)


@router.post("/auth/recovery")
@router.post("/auth/recovery/", include_in_schema=False)
def send_password_recovery(body: dict, db: Session = Depends(get_db)):
    """发送密码恢复邮件。MVP: 不实际发邮件，只返回 204。"""
    login = body.get("login", "")
    acc = db.query(Account).filter(Account.login == login).first()
    if not acc:
        return Response(status_code=204)
    return Response(status_code=204)


@router.post("/auth/recover")
@router.post("/auth/recover/", include_in_schema=False)
def execute_recover(body: dict, db: Session = Depends(get_db)):
    """执行密码恢复。MVP: 直接更新密码。"""
    login = body.get("login", "")
    new_password = body.get("password", "")
    if not login or not new_password:
        raise CreationException("CreationException")
    cred = db.query(Credential).filter(Credential.login == login).first()
    if not cred:
        raise EntityNotFoundException("AccountNotFoundException", login)
    cred.password = hashlib.md5(new_password.encode()).hexdigest()
    db.commit()
    return Response(status_code=204)


@router.post("/auth/oauth", response_model=dict)
@router.post("/auth/oauth/", include_in_schema=False)
def oauth_login(body: dict):
    """OAuth 登录。当前无 OAuth 配置，返回 501。"""
    raise HTTPException(status_code=501, detail="OAuth not configured")


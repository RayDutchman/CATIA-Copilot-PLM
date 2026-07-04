"""认证相关路由：登录、登出、当前用户信息。"""
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.security import verify_password, create_token
from app.core.config import settings
from app.models.auth import Account, Credential, UserGroupMapping
from app.schemas.auth import LoginRequestDTO, AccountDTO

router = APIRouter()


@router.post("/auth/login", response_model=AccountDTO)
def login(body: LoginRequestDTO, response: Response, db: Session = Depends(get_db)):
    """
    用户登录。
    成功后在响应头 jwt 中返回 token（Backbone 前端从此 header 读取）。
    与 Payara AuthResource.login() 行为完全一致。
    """
    account = db.query(Account).filter(Account.login == body.login).first()
    credential = db.query(Credential).filter(Credential.login == body.login).first()

    if not account or not credential or not account.enabled:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="认证失败")

    if not verify_password(body.password, credential.password):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="认证失败")

    # 从 usergroupmapping 表查询角色组（与 Payara UserGroupMapping 一致）
    mapping = db.query(UserGroupMapping).filter(UserGroupMapping.login == account.login).first()
    group_name = mapping.groupname if mapping else "users"
    token = create_token(account.login, group_name)

    # JWT 通过响应头返回，与 Payara AuthResource 行为一致
    response.headers["jwt"] = token
    return account


@router.get("/auth/logout", status_code=204)
def logout():
    """登出。JWT 无状态，客户端删除本地 token 即可。返回 204。"""
    return None


@router.get("/accounts/me", response_model=AccountDTO)
def get_me(current_user: Account = Depends(get_current_user)):
    """返回当前登录用户的账号信息。"""
    return current_user

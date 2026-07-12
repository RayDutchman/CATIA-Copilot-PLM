from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.exceptions import UserNotFoundException
from app.models.auth import Account
from app.services.user_manager import user_mgmt_service
from app.schemas.part import UserDTO
from app.schemas.user_mgmt import (
    UserStatsDTO, WorkspaceAdminDTO, TagSubscriptionDTO,
)

router = APIRouter(prefix="/docdoku-plm-server-rest/api")
PREFIX = "/workspaces/{ws}"


def _user_to_dict(u):
    return {"login": u["login"], "workspaceId": u["workspaceId"],
            "name": u.get("name", ""), "email": u.get("email", ""),
            "language": u.get("language", "")}


# ============ 用户统计 ============

@router.get(f"{PREFIX}/users-stats", response_model=UserStatsDTO)
@router.get(f"{PREFIX}/users-stats/", include_in_schema=False)
def users_stats(ws: str, db: Session = Depends(get_db),
                current_user: Account = Depends(get_current_user)):
    return user_mgmt_service.get_users_stats(db, ws)


# ============ 用户列表 & 详情 ============

@router.get(f"{PREFIX}/users", response_model=List[UserDTO])
@router.get(f"{PREFIX}/users/", include_in_schema=False)
def list_users(ws: str, db: Session = Depends(get_db),
               current_user: Account = Depends(get_current_user)):
    return [_user_to_dict(u) for u in user_mgmt_service.list_users(db, ws)]


@router.get(f"{PREFIX}/users/me", response_model=UserDTO)
@router.get(f"{PREFIX}/users/me/", include_in_schema=False)
def who_am_i(ws: str, db: Session = Depends(get_db),
             current_user: Account = Depends(get_current_user)):
    return user_mgmt_service.who_am_i(db, ws, current_user.login)


@router.get(f"{PREFIX}/users/admin", response_model=WorkspaceAdminDTO)
@router.get(f"{PREFIX}/users/admin/", include_in_schema=False)
def get_admin(ws: str, db: Session = Depends(get_db),
              current_user: Account = Depends(get_current_user)):
    """返回工作区管理员用户信息（Payara: GET /workspaces/{ws}/users/admin）"""
    return user_mgmt_service.get_admin_user(db, ws)


# ============ 用户 tag 订阅 ============

@router.get(f"{PREFIX}/users/{{login}}/tag-subscriptions", response_model=List[TagSubscriptionDTO])
@router.get(f"{PREFIX}/users/{{login}}/tag-subscriptions/", include_in_schema=False)
def user_tag_subscriptions(ws: str, login: str, db: Session = Depends(get_db),
                           current_user: Account = Depends(get_current_user)):
    acc = db.query(Account).filter(Account.login == login).first()
    if not acc:
        raise UserNotFoundException("UserNotFoundException", login)
    return user_mgmt_service.get_user_tag_subscriptions(db, ws, login)


@router.put(f"{PREFIX}/users/{{login}}/tag-subscriptions/{{tagName}}", response_model=TagSubscriptionDTO)
@router.put(f"{PREFIX}/users/{{login}}/tag-subscriptions/{{tagName}}/", include_in_schema=False)
def user_tag_subscription_put(ws: str, login: str, tagName: str,
                               body: dict = None,
                               db: Session = Depends(get_db),
                               current_user: Account = Depends(get_current_user)):
    acc = db.query(Account).filter(Account.login == login).first()
    if not acc:
        raise UserNotFoundException("UserNotFoundException", login)
    on_iter = (body or {}).get("onIterationChange", False)
    on_state = (body or {}).get("onStateChange", False)
    return user_mgmt_service.set_user_tag_subscription(
        db, ws, login, tagName, on_iter, on_state)


@router.delete(f"{PREFIX}/users/{{login}}/tag-subscriptions/{{tagName}}", status_code=204)
@router.delete(f"{PREFIX}/users/{{login}}/tag-subscriptions/{{tagName}}/", status_code=204, include_in_schema=False)
def user_tag_subscription_delete(ws: str, login: str, tagName: str,
                                 db: Session = Depends(get_db),
                                 current_user: Account = Depends(get_current_user)):
    user_mgmt_service.delete_user_tag_subscription(db, ws, login, tagName)

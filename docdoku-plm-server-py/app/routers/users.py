from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.exceptions import AccessRightException, UserNotFoundException, WorkspaceNotFoundException
from app.models.auth import Account
from app.services.user_manager import user_mgmt_service
from app.schemas.part import UserDTO
from app.schemas.user_mgmt import (
    UserStatsDTO, WorkspaceAdminDTO, TagSubscriptionDTO,
)

router = APIRouter(prefix="/docdoku-plm-server-rest/api")
PREFIX = "/workspaces/{ws}"


def _check_is_admin(db: Session, ws: str, current_user: Account):
    is_global_admin = db.execute(text(
        "SELECT 1 FROM usergroupmapping WHERE login=:l AND groupname='admin'"
    ), {"l": current_user.login}).first()
    if is_global_admin:
        return
    is_ws_admin = db.execute(text(
        "SELECT 1 FROM workspace WHERE id=:w AND admin_login=:l"
    ), {"w": ws, "l": current_user.login}).first()
    if not is_ws_admin:
        raise AccessRightException("AccessRightException", current_user.login)


def _user_to_dict(u):
    return {"login": u["login"], "workspaceId": u["workspaceId"],
            "name": u.get("name", ""), "email": u.get("email", ""),
            "language": u.get("language", "")}


# ============ 用户统计 ============

@router.get(f"{PREFIX}/users-stats", response_model=UserStatsDTO)
@router.get(f"{PREFIX}/users-stats/", include_in_schema=False)
def users_stats(ws: str, db: Session = Depends(get_db),
                current_user: Account = Depends(get_current_user)):
    users = db.execute(text(
        "SELECT COUNT(*) FROM userdata WHERE workspace_id=:w"
    ), {"w": ws}).scalar() or 0
    active_users = db.execute(text(
        "SELECT COUNT(*) FROM workspaceusermembership "
        "WHERE workspace_id = :w"
    ), {"w": ws}).scalar() or 0
    groups = db.execute(text(
        "SELECT COUNT(*) FROM usergroup WHERE workspace_id=:w"
    ), {"w": ws}).scalar() or 0
    active_groups = db.execute(text(
        "SELECT COUNT(*) FROM workspaceusergroupmembership WHERE workspace_id=:w"
    ), {"w": ws}).scalar() or 0
    return {
        "users": users,
        "activeusers": active_users,
        "inactiveusers": users - active_users,
        "groups": groups,
        "activegroups": active_groups,
        "inactivegroups": groups - active_groups,
    }


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
    r = db.execute(text(
        "SELECT a.login, a.name, a.email, a.language "
        "FROM account a JOIN workspace w ON a.login = w.admin_login "
        "WHERE w.id = :ws"
    ), {"ws": ws}).fetchone()
    if not r:
        raise WorkspaceNotFoundException("WorkspaceNotFoundException")
    return {"login": r[0], "name": r[1] or "", "email": r[2] or "",
            "language": r[3] or "", "workspaceId": ws}


@router.get(f"{PREFIX}/users/{{login}}", response_model=UserDTO)
@router.get(f"{PREFIX}/users/{{login}}/", include_in_schema=False)
def get_user(ws: str, login: str, db: Session = Depends(get_db),
             current_user: Account = Depends(get_current_user)):
    acc = db.query(Account).filter(Account.login == login).first()
    if not acc:
        raise UserNotFoundException("UserNotFoundException")
    return {
        "login": acc.login,
        "name": acc.name or "",
        "email": acc.email or "",
        "language": acc.language or "en",
        "workspaceId": ws,
    }


# ============ 用户 tag 订阅 ============

@router.get(f"{PREFIX}/users/{{login}}/tag-subscriptions", response_model=List[TagSubscriptionDTO])
@router.get(f"{PREFIX}/users/{{login}}/tag-subscriptions/", include_in_schema=False)
def user_tag_subscriptions(ws: str, login: str, db: Session = Depends(get_db),
                           current_user: Account = Depends(get_current_user)):
    acc = db.query(Account).filter(Account.login == login).first()
    if not acc:
        raise UserNotFoundException("UserNotFoundException")
    rows = db.execute(text(
        "SELECT tag_workspace_id, tag_label, oniterationchange, onstatechange "
        "FROM tagusersubscription "
        "WHERE subscriber_login = :l AND subscriber_workspace_id = :ws"
    ), {"l": login, "ws": ws}).fetchall()
    return [{
        "tag": r[1],
        "onIterationChange": bool(r[2]) if r[2] is not None else False,
        "onStateChange": bool(r[3]) if r[3] is not None else False,
    } for r in rows]


@router.put(f"{PREFIX}/users/{{login}}/tag-subscriptions/{{tagName}}", response_model=TagSubscriptionDTO)
@router.put(f"{PREFIX}/users/{{login}}/tag-subscriptions/{{tagName}}/", include_in_schema=False)
def user_tag_subscription_put(ws: str, login: str, tagName: str,
                               body: dict = None,
                               db: Session = Depends(get_db),
                               current_user: Account = Depends(get_current_user)):
    _check_is_admin(db, ws, current_user)
    acc = db.query(Account).filter(Account.login == login).first()
    if not acc:
        raise UserNotFoundException("UserNotFoundException")
    on_iter = (body or {}).get("onIterationChange", False)
    on_state = (body or {}).get("onStateChange", False)
    db.execute(text(
        "INSERT INTO tag (workspace_id, label) VALUES (:ws, :tag) ON CONFLICT DO NOTHING"
    ), {"ws": ws, "tag": tagName})
    db.execute(text(
        "INSERT INTO tagusersubscription "
        "(tag_workspace_id, tag_label, subscriber_login, subscriber_workspace_id, "
        " oniterationchange, onstatechange) "
        "VALUES (:ws, :tag, :l, :ws, :oi, :os) "
        "ON CONFLICT (tag_workspace_id, tag_label, subscriber_login, subscriber_workspace_id) "
        "DO UPDATE SET oniterationchange = :oi2, onstatechange = :os2"
    ), {"ws": ws, "tag": tagName, "l": login,
        "oi": on_iter, "oi2": on_iter, "os": on_state, "os2": on_state})
    db.commit()
    return {"tag": tagName, "onIterationChange": on_iter, "onStateChange": on_state}


@router.delete(f"{PREFIX}/users/{{login}}/tag-subscriptions/{{tagName}}", status_code=204)
@router.delete(f"{PREFIX}/users/{{login}}/tag-subscriptions/{{tagName}}/", status_code=204, include_in_schema=False)
def user_tag_subscription_delete(ws: str, login: str, tagName: str,
                                 db: Session = Depends(get_db),
                                 current_user: Account = Depends(get_current_user)):
    _check_is_admin(db, ws, current_user)
    db.execute(text(
        "DELETE FROM tagusersubscription "
        "WHERE tag_workspace_id = :ws AND tag_label = :tag "
        "AND subscriber_login = :l AND subscriber_workspace_id = :ws"
    ), {"ws": ws, "tag": tagName, "l": login})
    db.commit()

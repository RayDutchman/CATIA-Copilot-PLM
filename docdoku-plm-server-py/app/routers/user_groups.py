from typing import List
from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.exceptions import EntityNotFoundException, NotAllowedException
from app.models.auth import Account
from app.services.user_manager import user_mgmt_service
from app.schemas.user_mgmt import (
    UserGroupDTO, UserGroupMemberDTO, TagSubscriptionDTO,
)

router = APIRouter(prefix="/docdoku-plm-server-rest/api")
PREFIX = "/workspaces/{ws}"


def _group_to_dict(g):
    return {"id": g.id, "workspaceId": g.workspace_id}


# ============ 用户组 CRUD ============

@router.get(f"{PREFIX}/groups", response_model=List[UserGroupDTO])
@router.get(f"{PREFIX}/groups/", include_in_schema=False)
def list_groups(ws: str, db: Session = Depends(get_db),
                current_user: Account = Depends(get_current_user)):
    return [_group_to_dict(g) for g in user_mgmt_service.list_groups(db, ws)]


@router.post(f"{PREFIX}/groups", status_code=201, response_model=UserGroupDTO)
@router.post(f"{PREFIX}/groups/", status_code=201, include_in_schema=False)
def create_group(ws: str, body: dict, db: Session = Depends(get_db),
                 current_user: Account = Depends(get_current_user)):
    g = user_mgmt_service.create_group(db, ws, body.get("id", ""))
    return _group_to_dict(g)


@router.delete(f"{PREFIX}/groups/{{group_id}}", status_code=204)
@router.delete(f"{PREFIX}/groups/{{group_id}}/", status_code=204, include_in_schema=False)
def delete_group(ws: str, group_id: str, db: Session = Depends(get_db),
                 current_user: Account = Depends(get_current_user)):
    user_mgmt_service.delete_group(db, ws, group_id)


@router.get(f"{PREFIX}/groups/{{group_id}}/users", response_model=List[UserGroupMemberDTO])
@router.get(f"{PREFIX}/groups/{{group_id}}/users/", include_in_schema=False)
def get_users_in_group(ws: str, group_id: str, db: Session = Depends(get_db),
                       current_user: Account = Depends(get_current_user)):
    rows = db.execute(text(
        "SELECT a.login, a.name, a.email, a.language "
        "FROM account a "
        "JOIN usergroupmapping m ON a.login = m.login "
        "WHERE m.groupname = :gid"
    ), {"gid": group_id}).fetchall()
    return [{"login": r[0], "name": r[1], "email": r[2], "language": r[3]} for r in rows]


@router.put(f"{PREFIX}/enable-group")
@router.put(f"{PREFIX}/enable-group/", include_in_schema=False)
def enable_group(ws: str, body: dict, db: Session = Depends(get_db),
                 current_user: Account = Depends(get_current_user)):
    """启用工作组：写入 workspaceusergroupmembership 表"""
    group_id = body.get("id", "")
    if not group_id:
        raise NotAllowedException("NotAllowedException9", group_id)
    existing = db.execute(text(
        "SELECT id FROM usergroup WHERE id = :gid AND workspace_id = :ws"
    ), {"gid": group_id, "ws": ws}).fetchone()
    if not existing:
        raise EntityNotFoundException("UserGroupNotFoundException", group_id)
    db.execute(text(
        "INSERT INTO workspaceusergroupmembership "
        "(workspace_id, member_id, member_workspace_id, readonly) "
        "VALUES (:ws, :gid, :ws, false) "
        "ON CONFLICT (workspace_id, member_id, member_workspace_id) DO NOTHING"
    ), {"ws": ws, "gid": group_id})
    db.commit()
    return Response(status_code=204)


@router.put(f"{PREFIX}/disable-group")
@router.put(f"{PREFIX}/disable-group/", include_in_schema=False)
def disable_group(ws: str, body: dict, db: Session = Depends(get_db),
                  current_user: Account = Depends(get_current_user)):
    """禁用工作组：删除 workspaceusergroupmembership 记录"""
    group_id = body.get("id", "")
    if not group_id:
        raise NotAllowedException("NotAllowedException9", group_id)
    existing = db.execute(text(
        "SELECT id FROM usergroup WHERE id = :gid AND workspace_id = :ws"
    ), {"gid": group_id, "ws": ws}).fetchone()
    if not existing:
        raise EntityNotFoundException("UserGroupNotFoundException", group_id)
    db.execute(text(
        "DELETE FROM workspaceusergroupmembership "
        "WHERE workspace_id = :ws AND member_id = :gid"
    ), {"ws": ws, "gid": group_id})
    db.commit()
    return Response(status_code=204)


@router.put(f"{PREFIX}/group-access")
@router.put(f"{PREFIX}/group-access/", include_in_schema=False)
def set_group_access(ws: str, body: dict, db: Session = Depends(get_db),
                     current_user: Account = Depends(get_current_user)):
    """设置工作组访问权限"""
    group_id = body.get("member", {}).get("id", "") or body.get("memberId", "")
    if not group_id:
        raise NotAllowedException("NotAllowedException9", group_id)
    group = db.execute(text(
        "SELECT id FROM usergroup WHERE id = :gid AND workspace_id = :ws"
    ), {"gid": group_id, "ws": ws}).fetchone()
    if not group:
        raise EntityNotFoundException("UserGroupNotFoundException", group_id)
    read_only = body.get("readOnly", False)
    db.execute(text(
        "INSERT INTO workspaceusergroupmembership "
        "(workspace_id, member_id, member_workspace_id, readonly) "
        "VALUES (:ws, :gid, :ws, :ro) "
        "ON CONFLICT (workspace_id, member_id, member_workspace_id) "
        "DO UPDATE SET readonly = :ro2"
    ), {"ws": ws, "gid": group_id, "ro": read_only, "ro2": read_only})
    db.commit()
    return {"status": "ok"}


# ============ 工作组 tag 订阅 ============

@router.get(f"{PREFIX}/groups/{{groupId}}/tag-subscriptions")
@router.get(f"{PREFIX}/groups/{{groupId}}/tag-subscriptions/", include_in_schema=False)
def group_tag_subscriptions(ws: str, groupId: str, db: Session = Depends(get_db),
                            current_user: Account = Depends(get_current_user)):
    group = db.execute(text(
        "SELECT id FROM usergroup WHERE id = :gid AND workspace_id = :ws"
    ), {"gid": groupId, "ws": ws}).fetchone()
    if not group:
        raise EntityNotFoundException("UserGroupNotFoundException", groupId)
    rows = db.execute(text(
        "SELECT tag_workspace_id, tag_label, oniterationchange, onstatechange "
        "FROM tagusergroupsubscription "
        "WHERE subscriber_id = :gid AND subscriber_workspace_id = :ws"
    ), {"gid": groupId, "ws": ws}).fetchall()
    return [{
        "tag": r[1],
        "onIterationChange": bool(r[2]) if r[2] is not None else False,
        "onStateChange": bool(r[3]) if r[3] is not None else False,
    } for r in rows]


@router.put(f"{PREFIX}/groups/{{groupId}}/tag-subscriptions/{{tagName}}")
@router.put(f"{PREFIX}/groups/{{groupId}}/tag-subscriptions/{{tagName}}/", include_in_schema=False)
def group_tag_subscription_put(ws: str, groupId: str, tagName: str,
                                body: dict = None,
                                db: Session = Depends(get_db),
                                current_user: Account = Depends(get_current_user)):
    group = db.execute(text(
        "SELECT id FROM usergroup WHERE id = :gid AND workspace_id = :ws"
    ), {"gid": groupId, "ws": ws}).fetchone()
    if not group:
        raise EntityNotFoundException("UserGroupNotFoundException", groupId)
    on_iter = (body or {}).get("onIterationChange", False)
    on_state = (body or {}).get("onStateChange", False)
    db.execute(text(
        "INSERT INTO tag (workspace_id, label) VALUES (:ws, :tag) ON CONFLICT DO NOTHING"
    ), {"ws": ws, "tag": tagName})
    db.execute(text(
        "INSERT INTO tagusergroupsubscription "
        "(tag_workspace_id, tag_label, subscriber_id, subscriber_workspace_id, "
        " oniterationchange, onstatechange) "
        "VALUES (:ws, :tag, :gid, :ws, :oi, :os) "
        "ON CONFLICT (tag_workspace_id, tag_label, subscriber_id, subscriber_workspace_id) "
        "DO UPDATE SET oniterationchange = :oi2, onstatechange = :os2"
    ), {"ws": ws, "tag": tagName, "gid": groupId,
        "oi": on_iter, "oi2": on_iter, "os": on_state, "os2": on_state})
    db.commit()
    return {"tag": tagName, "onIterationChange": on_iter, "onStateChange": on_state}


@router.delete(f"{PREFIX}/groups/{{groupId}}/tag-subscriptions/{{tagName}}", status_code=204)
@router.delete(f"{PREFIX}/groups/{{groupId}}/tag-subscriptions/{{tagName}}/", status_code=204, include_in_schema=False)
def group_tag_subscription_delete(ws: str, groupId: str, tagName: str,
                                   db: Session = Depends(get_db),
                                   current_user: Account = Depends(get_current_user)):
    db.execute(text(
        "DELETE FROM tagusergroupsubscription "
        "WHERE tag_workspace_id = :ws AND tag_label = :tag "
        "AND subscriber_id = :gid AND subscriber_workspace_id = :ws"
    ), {"ws": ws, "tag": tagName, "gid": groupId})
    db.commit()


# ============ 用户组查询 ============

@router.get(f"{PREFIX}/user-group")
@router.get(f"{PREFIX}/user-group/", include_in_schema=False)
def workspace_user_group(ws: str, db: Session = Depends(get_db),
                         current_user: Account = Depends(get_current_user)):
    rows = db.execute(text(
        "SELECT g.id, g.workspace_id FROM usergroup g WHERE g.workspace_id = :ws"
    ), {"ws": ws}).fetchall()
    return [{"id": r[0], "workspaceId": r[1]} for r in rows]

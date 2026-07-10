from typing import List
from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.exceptions import (
    AccessRightException, EntityNotFoundException, NotAllowedException,
    UserNotFoundException, WorkspaceNotFoundException,
)
from app.models.auth import Account
from app.services.user_manager import user_mgmt_service
from app.schemas.user_mgmt import (
    WorkspaceMembershipDTO, WorkspaceUserGroupMembershipDTO, UserGroupDTO,
)
from app.schemas.admin import WorkspaceDTO

router = APIRouter(prefix="/docdoku-plm-server-rest/api")
PREFIX = "/workspaces/{ws}"


def _check_workspace_admin(db: Session, ws: str, current_user: Account):
    """验证当前用户是全局管理员或工作区管理员，否则 403。"""
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


def _group_to_dict(g):
    return {"id": g.id, "workspaceId": g.workspace_id}


def _workspace_to_dict(r) -> dict:
    return {
        "id": r[0],
        "description": r[1] or "",
        "enabled": bool(r[2]) if r[2] is not None else True,
        "folderLocked": bool(r[3]) if r[3] is not None else False,
        "admin": r[4] or "",
        "creationDate": None,
    }


# ============ 成员关系 ============

@router.get(f"{PREFIX}/memberships/users", response_model=List[WorkspaceMembershipDTO])
@router.get(f"{PREFIX}/memberships/users/", include_in_schema=False)
def list_user_memberships(ws: str, db: Session = Depends(get_db),
                          current_user: Account = Depends(get_current_user)):
    return user_mgmt_service.list_memberships(db, ws)


@router.get(f"{PREFIX}/memberships/users/me", response_model=List[WorkspaceMembershipDTO])
@router.get(f"{PREFIX}/memberships/users/me/", include_in_schema=False)
def my_memberships(ws: str, db: Session = Depends(get_db),
                   current_user: Account = Depends(get_current_user)):
    all_m = user_mgmt_service.list_memberships(db, ws)
    return [m for m in all_m if m["member"]["login"] == current_user.login]


@router.get(f"{PREFIX}/memberships/usergroups", response_model=List[WorkspaceUserGroupMembershipDTO])
@router.get(f"{PREFIX}/memberships/usergroups/", include_in_schema=False)
def list_group_memberships(ws: str, db: Session = Depends(get_db),
                           current_user: Account = Depends(get_current_user)):
    rows = db.execute(text(
        "SELECT wgm.workspace_id, wgm.member_id, wgm.readonly "
        "FROM workspaceusergroupmembership wgm "
        "WHERE wgm.workspace_id = :ws"
    ), {"ws": ws}).fetchall()
    if not rows:
        return []
    return [{"workspaceId": r[0], "memberId": r[1],
             "readOnly": bool(r[2]) if r[2] is not None else False,
             "member": {"id": r[1]}} for r in rows]


@router.get(f"{PREFIX}/memberships/usergroups/me")
@router.get(f"{PREFIX}/memberships/usergroups/me/", include_in_schema=False)
def my_group_memberships(ws: str, db: Session = Depends(get_db),
                         current_user: Account = Depends(get_current_user)):
    rows = db.execute(text(
        "SELECT g.id, g.workspace_id FROM usergroup g "
        "JOIN usergroupmapping m ON g.id = m.groupname "
        "WHERE g.workspace_id = :ws AND m.login = :l"
    ), {"ws": ws, "l": current_user.login}).fetchall()
    return [{"workspaceId": r[1], "memberId": r[0]} for r in rows]


# ============ 用户管理操作 ============

@router.put(f"{PREFIX}/add-user")
@router.put(f"{PREFIX}/add-user/", include_in_schema=False)
def add_user(ws: str, body: dict, db: Session = Depends(get_db),
             current_user: Account = Depends(get_current_user)):
    login = body.get("login", "")
    if not login:
        raise NotAllowedException("NotAllowedException9", login)
    acc = db.query(Account).filter(Account.login == login).first()
    if not acc:
        raise UserNotFoundException("UserNotFoundException", login)
    user_mgmt_service.add_user(db, ws, login, body.get("group"))
    return Response(status_code=204)


@router.put(f"{PREFIX}/remove-from-workspace", response_model=WorkspaceDTO)
@router.put(f"{PREFIX}/remove-from-workspace/", include_in_schema=False)
def remove_user(ws: str, body: dict, db: Session = Depends(get_db),
                current_user: Account = Depends(get_current_user)):
    login = body.get("login", "")
    if not login:
        raise NotAllowedException("NotAllowedException9", login)
    user_mgmt_service.remove_user_from_workspace(db, ws, login)
    r = db.execute(text(
        "SELECT id, description, enabled, folderlocked, admin_login "
        "FROM workspace WHERE id = :id"
    ), {"id": ws}).fetchone()
    if not r:
        raise WorkspaceNotFoundException("WorkspaceNotFoundException", ws)
    return _workspace_to_dict(r)


@router.put(f"{PREFIX}/remove-from-group/{{gid}}")
@router.put(f"{PREFIX}/remove-from-group/{{gid}}/", include_in_schema=False)
def remove_from_group(ws: str, gid: str, body: dict,
                       db: Session = Depends(get_db),
                       current_user: Account = Depends(get_current_user)):
    """从工作组移除用户"""
    login = body.get("login", "")
    if not login:
        raise NotAllowedException("NotAllowedException9", login)
    group = db.execute(text(
        "SELECT id FROM usergroup WHERE id = :gid AND workspace_id = :ws"
    ), {"gid": gid, "ws": ws}).fetchone()
    if not group:
        raise EntityNotFoundException("UserGroupNotFoundException", gid)
    db.execute(text(
        "DELETE FROM usergroupmapping WHERE login = :l AND groupname = :g"
    ), {"l": login, "g": gid})
    db.commit()
    return _group_to_dict(user_mgmt_service.list_groups(db, ws)[0])


@router.put(f"{PREFIX}/admin", response_model=WorkspaceDTO)
@router.put(f"{PREFIX}/admin/", include_in_schema=False)
def set_admin(ws: str, body: dict, db: Session = Depends(get_db),
              current_user: Account = Depends(get_current_user)):
    """设置工作区管理员"""
    _check_workspace_admin(db, ws, current_user)
    login = body.get("login", "")
    if not login:
        raise NotAllowedException("NotAllowedException9", login)
    acc = db.query(Account).filter(Account.login == login).first()
    if not acc:
        raise UserNotFoundException("UserNotFoundException", login)
    ws_row = db.execute(text(
        "SELECT id FROM workspace WHERE id = :id"
    ), {"id": ws}).fetchone()
    if not ws_row:
        raise WorkspaceNotFoundException("WorkspaceNotFoundException", ws)
    db.execute(text(
        "UPDATE workspace SET admin_login = :login WHERE id = :id"
    ), {"login": login, "id": ws})
    db.commit()
    r = db.execute(text(
        "SELECT id, description, enabled, folderlocked, admin_login "
        "FROM workspace WHERE id = :id"
    ), {"id": ws}).fetchone()
    return _workspace_to_dict(r)


@router.put(f"{PREFIX}/enable-user")
@router.put(f"{PREFIX}/enable-user/", include_in_schema=False)
def enable_user(ws: str, body: dict, db: Session = Depends(get_db),
                current_user: Account = Depends(get_current_user)):
    _check_workspace_admin(db, ws, current_user)
    login = body.get("login", "")
    if not login:
        raise NotAllowedException("NotAllowedException9", login)
    user_mgmt_service.enable_user(db, ws, login)
    return Response(status_code=204)


@router.put(f"{PREFIX}/disable-user")
@router.put(f"{PREFIX}/disable-user/", include_in_schema=False)
def disable_user(ws: str, body: dict, db: Session = Depends(get_db),
                 current_user: Account = Depends(get_current_user)):
    _check_workspace_admin(db, ws, current_user)
    login = body.get("login", "")
    if not login:
        raise NotAllowedException("NotAllowedException9", login)
    user_mgmt_service.disable_user(db, ws, login)
    return Response(status_code=204)


@router.put(f"{PREFIX}/user-access")
@router.put(f"{PREFIX}/user-access/", include_in_schema=False)
def set_user_access(ws: str, body: dict, db: Session = Depends(get_db),
                    current_user: Account = Depends(get_current_user)):
    """设置用户工作区访问权限。

    对齐 Java WorkspaceResource.setUserAccess → UserManagerBean.grantUserAccess：
    - 前端发送 {login, membership: "READ_ONLY"|"FULL_ACCESS"}
    - 只写 workspaceusermembership.readonly，不触及 account.enabled（全局字段）
    """
    _check_workspace_admin(db, ws, current_user)
    login = body.get("member", {}).get("login", "") or body.get("login", "")
    if not login:
        raise NotAllowedException("NotAllowedException9", login)

    # 对齐 Java UserDTO.getMembership() == WorkspaceMembership.READ_ONLY
    membership = body.get("membership", "")
    if membership:
        read_only = (membership == "READ_ONLY")
    else:
        # 兼容旧的 readOnly 布尔字段（向后兼容）
        read_only = body.get("readOnly", False)

    db.execute(text(
        "INSERT INTO workspaceusermembership "
        "(workspace_id, member_login, member_workspace_id, readonly) "
        "VALUES (:ws, :l, :ws, :ro) "
        "ON CONFLICT (workspace_id, member_login, member_workspace_id) "
        "DO UPDATE SET readonly = :ro2"
    ), {"ws": ws, "l": login, "ro": read_only, "ro2": read_only})
    db.commit()
    return {"status": "ok"}

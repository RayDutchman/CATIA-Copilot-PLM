from typing import List
from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.exceptions import (
    NotAllowedException, UserNotFoundException, WorkspaceNotFoundException,
)
from app.models.auth import Account
from app.services.user_manager import user_mgmt_service
from app.services.workspace_manager import workspace_service
from app.schemas.user_mgmt import (
    WorkspaceMembershipDTO, WorkspaceUserGroupMembershipDTO, UserGroupDTO,
)
from app.schemas.admin import WorkspaceDTO

router = APIRouter(prefix="/docdoku-plm-server-rest/api")
PREFIX = "/workspaces/{ws}"


def _check_workspace_admin(db: Session, ws: str, current_user: Account):
    """验证当前用户是全局管理员或工作区管理员，否则 403。"""
    workspace_service.check_workspace_admin(db, ws, current_user.login)


def _group_to_dict(g):
    return {"id": g.id, "workspaceId": g.workspace_id}


def _workspace_to_dict(r) -> dict:
    return {
        "id": r[0],
        "description": r[1] or "",
        "enabled": bool(r[2]) if r[2] is not None else True,
        "folderLocked": bool(r[3]) if r[3] is not None else False,
    }


# ============ 成员关系 ============

@router.get(f"{PREFIX}/memberships/users", response_model=List[WorkspaceMembershipDTO])
@router.get(f"{PREFIX}/memberships/users/", include_in_schema=False)
def list_user_memberships(ws: str, db: Session = Depends(get_db),
                          current_user: Account = Depends(get_current_user)):
    return user_mgmt_service.list_memberships(db, ws)


@router.get(f"{PREFIX}/memberships/users/me", response_model=WorkspaceMembershipDTO)
@router.get(f"{PREFIX}/memberships/users/me/", include_in_schema=False)
def my_memberships(ws: str, db: Session = Depends(get_db),
                   current_user: Account = Depends(get_current_user)):
    """获取当前用户在工作区中的成员关系。对齐 Java getWorkspaceSpecificUserMemberShips → 返回单个 WorkspaceUserMemberShipDTO（workspaceId/member/readOnly，无 permission 字段）"""
    return user_mgmt_service.get_my_membership(db, ws, current_user.login)


@router.get(f"{PREFIX}/memberships/usergroups", response_model=List[WorkspaceUserGroupMembershipDTO])
@router.get(f"{PREFIX}/memberships/usergroups/", include_in_schema=False)
def list_group_memberships(ws: str, db: Session = Depends(get_db),
                           current_user: Account = Depends(get_current_user)):
    return user_mgmt_service.list_group_memberships(db, ws)


@router.get(f"{PREFIX}/memberships/usergroups/me")
@router.get(f"{PREFIX}/memberships/usergroups/me/", include_in_schema=False)
def my_group_memberships(ws: str, db: Session = Depends(get_db),
                         current_user: Account = Depends(get_current_user)):
    return user_mgmt_service.get_my_group_memberships(db, ws, current_user.login)


# ============ 用户管理操作 ============

@router.put(f"{PREFIX}/add-user")
@router.put(f"{PREFIX}/add-user/", include_in_schema=False)
def add_user(ws: str, body: dict, db: Session = Depends(get_db),
             current_user: Account = Depends(get_current_user),
             group: str = Query(None)):
    _check_workspace_admin(db, ws, current_user)
    login = body.get("login", "")
    if not login:
        raise NotAllowedException("NotAllowedException9", login)
    acc = db.query(Account).filter(Account.login == login).first()
    if not acc:
        raise UserNotFoundException("UserNotFoundException", login)
    user_mgmt_service.add_user(db, ws, login, group)
    return Response(status_code=204)


@router.put(f"{PREFIX}/remove-from-workspace", response_model=WorkspaceDTO)
@router.put(f"{PREFIX}/remove-from-workspace/", include_in_schema=False)
def remove_user(ws: str, body: dict, db: Session = Depends(get_db),
                current_user: Account = Depends(get_current_user)):
    _check_workspace_admin(db, ws, current_user)
    login = body.get("login", "")
    if not login:
        raise NotAllowedException("NotAllowedException9", login)
    user_mgmt_service.remove_user_from_workspace(db, ws, login)
    r = workspace_service.get_workspace_admin(db, ws)
    return _workspace_to_dict(r)


@router.put(f"{PREFIX}/remove-from-group/{{gid}}")
@router.put(f"{PREFIX}/remove-from-group/{{gid}}/", include_in_schema=False)
def remove_from_group(ws: str, gid: str, body: dict,
                       db: Session = Depends(get_db),
                       current_user: Account = Depends(get_current_user)):
    """从工作组移除用户。对齐 Java WorkspaceResource.removeUserFromGroup → 返回被操作 UserGroupDTO"""
    _check_workspace_admin(db, ws, current_user)
    login = body.get("login", "")
    if not login:
        raise NotAllowedException("NotAllowedException9", login)
    return user_mgmt_service.remove_from_group(db, ws, gid, login)


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
    workspace_service.get_workspace_admin(db, ws)  # 存在性校验
    user_mgmt_service.set_workspace_admin(db, ws, login)
    r = workspace_service.get_workspace_admin(db, ws)
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
    - 返回更新后的 UserDTO（login/name/email/language/workspaceId/membership）
    - membership 为 null → 400
    """
    _check_workspace_admin(db, ws, current_user)
    login = body.get("member", {}).get("login", "") or body.get("login", "")
    if not login:
        raise NotAllowedException("NotAllowedException9", login)

    membership = body.get("membership", "")
    if not membership:
        raise NotAllowedException("NotAllowedException9", login)

    read_only = (membership == "READ_ONLY")

    user_mgmt_service.set_user_access(db, ws, login, read_only)

    mem_row = db.execute(text(
        "SELECT readonly FROM workspaceusermembership "
        "WHERE workspace_id = :ws AND member_login = :l AND member_workspace_id = :ws"
    ), {"ws": ws, "l": login}).fetchone()
    if not mem_row:
        raise NotAllowedException("NotAllowedException9", login)

    acc = db.query(Account).filter(Account.login == login).first()
    return {
        "login": login,
        "name": acc.name or "" if acc else "",
        "email": acc.email or "" if acc else "",
        "language": acc.language or "" if acc else "",
        "workspaceId": ws,
        "membership": "READ_ONLY" if mem_row[0] else "FULL_ACCESS",
    }

from typing import List
from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.exceptions import NotAllowedException
from app.models.auth import Account
from app.services.user_manager import user_mgmt_service
from app.schemas.user_mgmt import (
    UserGroupDTO, UserGroupMemberDTO, TagSubscriptionDTO,
)
from app.routers.workspace_memberships import _check_workspace_admin

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
    _check_workspace_admin(db, ws, current_user)
    g = user_mgmt_service.create_group(db, ws, body.get("id", ""))
    return _group_to_dict(g)


@router.delete(f"{PREFIX}/groups/{{group_id}}", status_code=204)
@router.delete(f"{PREFIX}/groups/{{group_id}}/", status_code=204, include_in_schema=False)
def delete_group(ws: str, group_id: str, db: Session = Depends(get_db),
                 
                 current_user: Account = Depends(get_current_user)):
    _check_workspace_admin(db, ws, current_user)
    user_mgmt_service.delete_group(db, ws, group_id)


@router.get(f"{PREFIX}/groups/{{group_id}}/users", response_model=List[UserGroupMemberDTO])
@router.get(f"{PREFIX}/groups/{{group_id}}/users/", include_in_schema=False)
def get_users_in_group(ws: str, group_id: str, db: Session = Depends(get_db),
                       current_user: Account = Depends(get_current_user)):
    return user_mgmt_service.get_users_in_group(db, group_id)


@router.put(f"{PREFIX}/enable-group")
@router.put(f"{PREFIX}/enable-group/", include_in_schema=False)
def enable_group(ws: str, body: dict, db: Session = Depends(get_db),
                 
                 current_user: Account = Depends(get_current_user)):
    """启用工作组：写入 workspaceusergroupmembership 表"""
    _check_workspace_admin(db, ws, current_user)
    group_id = body.get("id", "")
    if not group_id:
        raise NotAllowedException("NotAllowedException9", group_id)
    user_mgmt_service.enable_group(db, ws, group_id)
    return Response(status_code=204)


@router.put(f"{PREFIX}/disable-group")
@router.put(f"{PREFIX}/disable-group/", include_in_schema=False)
def disable_group(ws: str, body: dict, db: Session = Depends(get_db),
                  current_user: Account = Depends(get_current_user)):
    """禁用工作组：删除 workspaceusergroupmembership 记录"""
    _check_workspace_admin(db, ws, current_user)
    group_id = body.get("id", "")
    if not group_id:
        raise NotAllowedException("NotAllowedException9", group_id)
    user_mgmt_service.disable_group(db, ws, group_id)
    return Response(status_code=204)


@router.put(f"{PREFIX}/group-access")
@router.put(f"{PREFIX}/group-access/", include_in_schema=False)
def set_group_access(ws: str, body: dict, db: Session = Depends(get_db),
                     
                     current_user: Account = Depends(get_current_user)):
    """设置工作组访问权限。对齐 Java WorkspaceResource.setGroupAccess → 返回 WorkspaceUserGroupMemberShipDTO（workspaceId/memberId/readOnly）"""
    _check_workspace_admin(db, ws, current_user)
    group_id = body.get("member", {}).get("id", "") or body.get("memberId", "")
    if not group_id:
        raise NotAllowedException("NotAllowedException9", group_id)
    read_only = body.get("readOnly", False)
    return user_mgmt_service.set_group_access(db, ws, group_id, read_only)


# ============ 工作组 tag 订阅 ============

@router.get(f"{PREFIX}/groups/{{groupId}}/tag-subscriptions")
@router.get(f"{PREFIX}/groups/{{groupId}}/tag-subscriptions/", include_in_schema=False)
def group_tag_subscriptions(ws: str, groupId: str, db: Session = Depends(get_db),
                            current_user: Account = Depends(get_current_user)):
    return user_mgmt_service.get_group_tag_subscriptions(db, ws, groupId)


@router.put(f"{PREFIX}/groups/{{groupId}}/tag-subscriptions/{{tagName}}")
@router.put(f"{PREFIX}/groups/{{groupId}}/tag-subscriptions/{{tagName}}/", include_in_schema=False)
def group_tag_subscription_put(ws: str, groupId: str, tagName: str,
                                body: dict = None,
                                db: Session = Depends(get_db),
                                
                                current_user: Account = Depends(get_current_user)):
    on_iter = (body or {}).get("onIterationChange", False)
    on_state = (body or {}).get("onStateChange", False)
    return user_mgmt_service.set_group_tag_subscription(
        db, ws, groupId, tagName, on_iter, on_state)


@router.delete(f"{PREFIX}/groups/{{groupId}}/tag-subscriptions/{{tagName}}", status_code=204)
@router.delete(f"{PREFIX}/groups/{{groupId}}/tag-subscriptions/{{tagName}}/", status_code=204, include_in_schema=False)
def group_tag_subscription_delete(ws: str, groupId: str, tagName: str,
                                   db: Session = Depends(get_db),
                                   
                                   current_user: Account = Depends(get_current_user)):
    user_mgmt_service.delete_group_tag_subscription(db, ws, groupId, tagName)


# ============ 用户组查询 ============

@router.get(f"{PREFIX}/user-group")
@router.get(f"{PREFIX}/user-group/", include_in_schema=False)
def workspace_user_group(ws: str, db: Session = Depends(get_db),
                         current_user: Account = Depends(get_current_user)):
    return user_mgmt_service.get_workspace_user_groups(db, ws)

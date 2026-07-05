from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.auth import Account
from app.services.user_mgmt_service import user_mgmt_service

router = APIRouter(prefix="/docdoku-plm-server-rest/api")
PREFIX = "/workspaces/{ws}"


def _user_to_dict(u):
    return {"login": u["login"], "workspaceId": u["workspaceId"],
            "name": u.get("name", ""), "email": u.get("email", ""),
            "enabled": u.get("enabled", True),
            "language": u.get("language", "")}


def _group_to_dict(g):
    return {"id": g.id, "workspaceId": g.workspace_id}


@router.get(f"{PREFIX}/users-stats")
def users_stats(ws: str, db: Session = Depends(get_db),
                current_user: Account = Depends(get_current_user)):
    from sqlalchemy import text
    total = db.execute(text("SELECT COUNT(*) FROM userdata WHERE workspace_id=:w"), {"w": ws}).scalar()
    return {"totalUsers": total or 0}


@router.get(f"{PREFIX}/users")
def list_users(ws: str, db: Session = Depends(get_db),
               current_user: Account = Depends(get_current_user)):
    return [_user_to_dict(u) for u in user_mgmt_service.list_users(db, ws)]


@router.get(f"{PREFIX}/users/me")
def who_am_i(ws: str, db: Session = Depends(get_db),
             current_user: Account = Depends(get_current_user)):
    return user_mgmt_service.who_am_i(db, ws, current_user.login)


@router.get(f"{PREFIX}/groups")
def list_groups(ws: str, db: Session = Depends(get_db),
                current_user: Account = Depends(get_current_user)):
    return [_group_to_dict(g) for g in user_mgmt_service.list_groups(db, ws)]


@router.post(f"{PREFIX}/groups", status_code=201)
@router.post(f"{PREFIX}/groups/", status_code=201, include_in_schema=False)
def create_group(ws: str, body: dict, db: Session = Depends(get_db),
                 current_user: Account = Depends(get_current_user)):
    g = user_mgmt_service.create_group(db, ws, body.get("id", ""))
    return _group_to_dict(g)


@router.delete(f"{PREFIX}/groups/{{group_id}}", status_code=204)
def delete_group(ws: str, group_id: str, db: Session = Depends(get_db),
                 current_user: Account = Depends(get_current_user)):
    user_mgmt_service.delete_group(db, ws, group_id)


@router.get(f"{PREFIX}/memberships/users")
def list_user_memberships(ws: str, db: Session = Depends(get_db),
                          current_user: Account = Depends(get_current_user)):
    return user_mgmt_service.list_memberships(db, ws)


@router.get(f"{PREFIX}/memberships/users/me")
def my_memberships(ws: str, db: Session = Depends(get_db),
                   current_user: Account = Depends(get_current_user)):
    all_m = user_mgmt_service.list_memberships(db, ws)
    return [m for m in all_m if m["member"]["login"] == current_user.login]


@router.get(f"{PREFIX}/memberships/usergroups")
def list_group_memberships(ws: str, db: Session = Depends(get_db),
                           current_user: Account = Depends(get_current_user)):
    from app.models.user_mgmt import UserGroup
    groups = db.query(UserGroup).filter(UserGroup.workspace_id == ws).all()
    return [{"workspaceId": ws, "memberId": g.id, "readOnly": False, "member": {"id": g.id}} for g in groups]


@router.get(f"{PREFIX}/memberships/usergroups/me")
def my_group_memberships(ws: str, db: Session = Depends(get_db),
                         current_user: Account = Depends(get_current_user)):
    from sqlalchemy import text
    rows = db.execute(text(
        "SELECT g.id, g.workspace_id FROM usergroup g "
        "JOIN usergroupmapping m ON g.id = m.groupname "
        "WHERE g.workspace_id = :ws AND m.login = :l"
    ), {"ws": ws, "l": current_user.login}).fetchall()
    return [{"workspaceId": r[1], "memberId": r[0]} for r in rows]


@router.put(f"{PREFIX}/add-user")
@router.put(f"{PREFIX}/add-user/", include_in_schema=False)
def add_user(ws: str, body: dict, db: Session = Depends(get_db),
             current_user: Account = Depends(get_current_user)):
    user_mgmt_service.add_user(db, ws, body.get("login", ""), body.get("group"))
    return {"status": "ok"}


@router.put(f"{PREFIX}/remove-from-workspace")
@router.put(f"{PREFIX}/remove-from-workspace/", include_in_schema=False)
def remove_user(ws: str, body: dict, db: Session = Depends(get_db),
                current_user: Account = Depends(get_current_user)):
    user_mgmt_service.remove_user_from_workspace(db, ws, body.get("login", ""))
    return {"status": "ok"}


@router.get(f"{PREFIX}/users/{{login}}/tag-subscriptions")
def user_tag_subscriptions(ws: str, login: str, db: Session = Depends(get_db),
                           current_user: Account = Depends(get_current_user)):
    return []


@router.put(f"{PREFIX}/users/{{login}}/tag-subscriptions/{{tagName}}")
@router.put(f"{PREFIX}/users/{{login}}/tag-subscriptions/{{tagName}}/", include_in_schema=False)
def user_tag_subscription_put(ws: str, login: str, tagName: str,
                              db: Session = Depends(get_db),
                              current_user: Account = Depends(get_current_user)):
    return {"status": "ok"}


@router.delete(f"{PREFIX}/users/{{login}}/tag-subscriptions/{{tagName}}", status_code=204)
@router.delete(f"{PREFIX}/users/{{login}}/tag-subscriptions/{{tagName}}/", status_code=204, include_in_schema=False)
def user_tag_subscription_delete(ws: str, login: str, tagName: str,
                                 db: Session = Depends(get_db),
                                 current_user: Account = Depends(get_current_user)):
    pass


@router.get(f"{PREFIX}/groups/{{group_id}}/users")
def get_users_in_group(ws: str, group_id: str, db: Session = Depends(get_db),
                       current_user: Account = Depends(get_current_user)):
    from sqlalchemy import text
    rows = db.execute(text(
        "SELECT a.login, a.name, a.email, a.language "
        "FROM account a "
        "JOIN usergroupmapping m ON a.login = m.login "
        "WHERE m.groupname = :gid"
    ), {"gid": group_id}).fetchall()
    return [{"login": r[0], "name": r[1], "email": r[2], "language": r[3]} for r in rows]


@router.get(f"{PREFIX}/groups/{{groupId}}/tag-subscriptions")
def group_tag_subscriptions(ws: str, groupId: str, db: Session = Depends(get_db),
                            current_user: Account = Depends(get_current_user)):
    return []


@router.put(f"{PREFIX}/groups/{{groupId}}/tag-subscriptions/{{tagName}}")
@router.put(f"{PREFIX}/groups/{{groupId}}/tag-subscriptions/{{tagName}}/", include_in_schema=False)
def group_tag_subscription_put(ws: str, groupId: str, tagName: str,
                               db: Session = Depends(get_db),
                               current_user: Account = Depends(get_current_user)):
    return {"status": "ok"}


@router.delete(f"{PREFIX}/groups/{{groupId}}/tag-subscriptions/{{tagName}}", status_code=204)
@router.delete(f"{PREFIX}/groups/{{groupId}}/tag-subscriptions/{{tagName}}/", status_code=204, include_in_schema=False)
def group_tag_subscription_delete(ws: str, groupId: str, tagName: str,
                                  db: Session = Depends(get_db),
                                  current_user: Account = Depends(get_current_user)):
    pass


@router.put(f"{PREFIX}/enable-user")
@router.put(f"{PREFIX}/enable-user/", include_in_schema=False)
def enable_user(ws: str, body: dict, db: Session = Depends(get_db),
                current_user: Account = Depends(get_current_user)):
    user_mgmt_service.enable_user(db, ws, body.get("login", ""))
    return {"status": "ok"}


@router.put(f"{PREFIX}/user-access")
@router.put(f"{PREFIX}/user-access/", include_in_schema=False)
def set_user_access(ws: str, body: dict, db: Session = Depends(get_db),
                    current_user: Account = Depends(get_current_user)):
    """设置用户访问权限：'只读'(readOnly=true→disable) 或 '完全访问'(false→enable)"""
    login = body.get("member", {}).get("login", "")
    read_only = body.get("readOnly", False)
    from sqlalchemy import text
    # Payara: readOnly=true → account.enabled=false
    db.execute(text("UPDATE account SET enabled = :en WHERE login = :l"),
               {"en": not read_only, "l": login})
    db.commit()
    return {"status": "ok"}


@router.put(f"{PREFIX}/group-access")
@router.put(f"{PREFIX}/group-access/", include_in_schema=False)
def set_group_access(ws: str, body: dict, db: Session = Depends(get_db),
                     current_user: Account = Depends(get_current_user)):
    """设置用户组访问权限（暂不实现完整组权限）"""
    return {"status": "ok"}


@router.put(f"{PREFIX}/disable-user")
@router.put(f"{PREFIX}/disable-user/", include_in_schema=False)
def disable_user(ws: str, body: dict, db: Session = Depends(get_db),
                 current_user: Account = Depends(get_current_user)):
    user_mgmt_service.disable_user(db, ws, body.get("login", ""))
    return {"status": "ok"}


@router.get(f"{PREFIX}/workspace-workflows/{{workflowId}}/aborted")
def workflow_aborted(ws: str, workflowId: str, db: Session = Depends(get_db),
                     current_user: Account = Depends(get_current_user)):
    return []

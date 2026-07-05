from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.auth import Account
from app.services.user_mgmt_service import user_mgmt_service

router = APIRouter(prefix="/docdoku-plm-server-rest/api")
PREFIX = "/workspaces/{ws}"


def _user_to_dict(u):
    return {"login": u["login"], "workspaceId": u["workspaceId"],
            "name": u.get("name", ""), "email": u.get("email", ""),
            "language": u.get("language", "")}


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


def _tag_subscription_to_dict(r, field_prefix="subscriber_login"):
    """将 tagusersubscription / tagusergroupsubscription 行转为字典"""
    keys = ["tag_workspace_id", "tag_label", "oniterationchange", "onstatechange"]
    result = {}
    if field_prefix == "subscriber_login":
        result["subscriber"] = {"login": r[2]}
    else:
        result["subscriber"] = {"id": r[2]}
    for i, k in enumerate(keys):
        if i < len(r):
            val = r[i] if i < 2 else bool(r[i]) if r[i] is not None else False
            result[k] = val
    return result


# ============ 用户统计 ============

@router.get(f"{PREFIX}/users-stats")
def users_stats(ws: str, db: Session = Depends(get_db),
                current_user: Account = Depends(get_current_user)):
    users = db.execute(text(
        "SELECT COUNT(*) FROM userdata WHERE workspace_id=:w"
    ), {"w": ws}).scalar() or 0
    active_users = db.execute(text(
        "SELECT COUNT(*) FROM userdata u JOIN account a ON u.login = a.login "
        "WHERE u.workspace_id = :w AND a.enabled = true"
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

@router.get(f"{PREFIX}/users")
def list_users(ws: str, db: Session = Depends(get_db),
               current_user: Account = Depends(get_current_user)):
    return [_user_to_dict(u) for u in user_mgmt_service.list_users(db, ws)]


@router.get(f"{PREFIX}/users/me")
def who_am_i(ws: str, db: Session = Depends(get_db),
             current_user: Account = Depends(get_current_user)):
    return user_mgmt_service.who_am_i(db, ws, current_user.login)


@router.get(f"{PREFIX}/users/admin")
def get_admin(ws: str, db: Session = Depends(get_db),
              current_user: Account = Depends(get_current_user)):
    """返回工作区管理员用户信息（Payara: GET /workspaces/{ws}/users/admin）"""
    r = db.execute(text(
        "SELECT a.login, a.name, a.email, a.language "
        "FROM account a JOIN workspace w ON a.login = w.admin_login "
        "WHERE w.id = :ws"
    ), {"ws": ws}).fetchone()
    if not r:
        raise HTTPException(status_code=404, detail="工作区或管理员不存在")
    return {"login": r[0], "name": r[1] or "", "email": r[2] or "",
            "language": r[3] or "", "workspaceId": ws}


@router.get(f"{PREFIX}/users/{{login}}")
def get_user(ws: str, login: str, db: Session = Depends(get_db),
             current_user: Account = Depends(get_current_user)):
    acc = db.query(Account).filter(Account.login == login).first()
    if not acc:
        raise HTTPException(status_code=404, detail="用户不存在")
    return {
        "login": acc.login,
        "name": acc.name or "",
        "email": acc.email or "",
        "language": acc.language or "en",
        "workspaceId": ws,
    }


# ============ 用户组 CRUD ============

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


@router.get(f"{PREFIX}/groups/{{group_id}}/users")
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
        raise HTTPException(status_code=400, detail="组 id 不能为空")
    existing = db.execute(text(
        "SELECT id FROM usergroup WHERE id = :gid AND workspace_id = :ws"
    ), {"gid": group_id, "ws": ws}).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="工作组不存在")
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
        raise HTTPException(status_code=400, detail="组 id 不能为空")
    existing = db.execute(text(
        "SELECT id FROM usergroup WHERE id = :gid AND workspace_id = :ws"
    ), {"gid": group_id, "ws": ws}).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="工作组不存在")
    db.execute(text(
        "DELETE FROM workspaceusergroupmembership "
        "WHERE workspace_id = :ws AND member_id = :gid"
    ), {"ws": ws, "gid": group_id})
    db.commit()
    return Response(status_code=204)


# ============ 成员关系 ============

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
        raise HTTPException(status_code=400, detail="login 不能为空")
    acc = db.query(Account).filter(Account.login == login).first()
    if not acc:
        raise HTTPException(status_code=404, detail="用户不存在")
    user_mgmt_service.add_user(db, ws, login, body.get("group"))
    return Response(status_code=204)


@router.put(f"{PREFIX}/remove-from-workspace")
@router.put(f"{PREFIX}/remove-from-workspace/", include_in_schema=False)
def remove_user(ws: str, body: dict, db: Session = Depends(get_db),
                current_user: Account = Depends(get_current_user)):
    login = body.get("login", "")
    if not login:
        raise HTTPException(status_code=400, detail="login 不能为空")
    user_mgmt_service.remove_user_from_workspace(db, ws, login)
    # Payara 返回更新后的 WorkspaceDTO
    r = db.execute(text(
        "SELECT id, description, enabled, folderlocked, admin_login "
        "FROM workspace WHERE id = :id"
    ), {"id": ws}).fetchone()
    if not r:
        raise HTTPException(status_code=404, detail="工作区不存在")
    return _workspace_to_dict(r)


@router.put(f"{PREFIX}/remove-from-group/{{gid}}")
@router.put(f"{PREFIX}/remove-from-group/{{gid}}/", include_in_schema=False)
def remove_from_group(ws: str, gid: str, body: dict,
                       db: Session = Depends(get_db),
                       current_user: Account = Depends(get_current_user)):
    """从工作组移除用户"""
    login = body.get("login", "")
    if not login:
        raise HTTPException(status_code=400, detail="login 不能为空")
    group = db.execute(text(
        "SELECT id FROM usergroup WHERE id = :gid AND workspace_id = :ws"
    ), {"gid": gid, "ws": ws}).fetchone()
    if not group:
        raise HTTPException(status_code=404, detail="工作组不存在")
    db.execute(text(
        "DELETE FROM usergroupmapping WHERE login = :l AND groupname = :g"
    ), {"l": login, "g": gid})
    db.commit()
    return _group_to_dict(user_mgmt_service.list_groups(db, ws)[0])


@router.put(f"{PREFIX}/admin")
@router.put(f"{PREFIX}/admin/", include_in_schema=False)
def set_admin(ws: str, body: dict, db: Session = Depends(get_db),
              current_user: Account = Depends(get_current_user)):
    """设置工作区管理员"""
    login = body.get("login", "")
    if not login:
        raise HTTPException(status_code=400, detail="login 不能为空")
    acc = db.query(Account).filter(Account.login == login).first()
    if not acc:
        raise HTTPException(status_code=404, detail="用户不存在")
    ws_row = db.execute(text(
        "SELECT id FROM workspace WHERE id = :id"
    ), {"id": ws}).fetchone()
    if not ws_row:
        raise HTTPException(status_code=404, detail="工作区不存在")
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
    login = body.get("login", "")
    if not login:
        raise HTTPException(status_code=400, detail="login 不能为空")
    user_mgmt_service.enable_user(db, ws, login)
    return Response(status_code=204)


@router.put(f"{PREFIX}/disable-user")
@router.put(f"{PREFIX}/disable-user/", include_in_schema=False)
def disable_user(ws: str, body: dict, db: Session = Depends(get_db),
                 current_user: Account = Depends(get_current_user)):
    login = body.get("login", "")
    if not login:
        raise HTTPException(status_code=400, detail="login 不能为空")
    user_mgmt_service.disable_user(db, ws, login)
    return Response(status_code=204)


@router.put(f"{PREFIX}/user-access")
@router.put(f"{PREFIX}/user-access/", include_in_schema=False)
def set_user_access(ws: str, body: dict, db: Session = Depends(get_db),
                    current_user: Account = Depends(get_current_user)):
    """设置用户访问权限"""
    login = body.get("member", {}).get("login", "") or body.get("login", "")
    if not login:
        raise HTTPException(status_code=400, detail="login 不能为空")
    read_only = body.get("readOnly", False)
    db.execute(text("UPDATE account SET enabled = :en WHERE login = :l"),
               {"en": not read_only, "l": login})
    db.execute(text(
        "INSERT INTO workspaceusermembership "
        "(workspace_id, member_login, member_workspace_id, readonly) "
        "VALUES (:ws, :l, :ws, :ro) "
        "ON CONFLICT (workspace_id, member_login, member_workspace_id) "
        "DO UPDATE SET readonly = :ro2"
    ), {"ws": ws, "l": login, "ro": read_only, "ro2": read_only})
    db.commit()
    return {"status": "ok"}


@router.put(f"{PREFIX}/group-access")
@router.put(f"{PREFIX}/group-access/", include_in_schema=False)
def set_group_access(ws: str, body: dict, db: Session = Depends(get_db),
                     current_user: Account = Depends(get_current_user)):
    """设置工作组访问权限"""
    group_id = body.get("member", {}).get("id", "") or body.get("memberId", "")
    if not group_id:
        raise HTTPException(status_code=400, detail="组 id 不能为空")
    group = db.execute(text(
        "SELECT id FROM usergroup WHERE id = :gid AND workspace_id = :ws"
    ), {"gid": group_id, "ws": ws}).fetchone()
    if not group:
        raise HTTPException(status_code=404, detail="工作组不存在")
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


# ============ 用户 tag 订阅 ============

@router.get(f"{PREFIX}/users/{{login}}/tag-subscriptions")
def user_tag_subscriptions(ws: str, login: str, db: Session = Depends(get_db),
                           current_user: Account = Depends(get_current_user)):
    acc = db.query(Account).filter(Account.login == login).first()
    if not acc:
        raise HTTPException(status_code=404, detail="用户不存在")
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


@router.put(f"{PREFIX}/users/{{login}}/tag-subscriptions/{{tagName}}")
@router.put(f"{PREFIX}/users/{{login}}/tag-subscriptions/{{tagName}}/", include_in_schema=False)
def user_tag_subscription_put(ws: str, login: str, tagName: str,
                               body: dict = None,
                               db: Session = Depends(get_db),
                               current_user: Account = Depends(get_current_user)):
    acc = db.query(Account).filter(Account.login == login).first()
    if not acc:
        raise HTTPException(status_code=404, detail="用户不存在")
    on_iter = (body or {}).get("onIterationChange", False)
    on_state = (body or {}).get("onStateChange", False)
    # 确保 tag 存在
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
    db.execute(text(
        "DELETE FROM tagusersubscription "
        "WHERE tag_workspace_id = :ws AND tag_label = :tag "
        "AND subscriber_login = :l AND subscriber_workspace_id = :ws"
    ), {"ws": ws, "tag": tagName, "l": login})
    db.commit()


# ============ 工作组 tag 订阅 ============

@router.get(f"{PREFIX}/groups/{{groupId}}/tag-subscriptions")
def group_tag_subscriptions(ws: str, groupId: str, db: Session = Depends(get_db),
                            current_user: Account = Depends(get_current_user)):
    group = db.execute(text(
        "SELECT id FROM usergroup WHERE id = :gid AND workspace_id = :ws"
    ), {"gid": groupId, "ws": ws}).fetchone()
    if not group:
        raise HTTPException(status_code=404, detail="工作组不存在")
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
        raise HTTPException(status_code=404, detail="工作组不存在")
    on_iter = (body or {}).get("onIterationChange", False)
    on_state = (body or {}).get("onStateChange", False)
    # 确保 tag 存在
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
def workspace_user_group(ws: str, db: Session = Depends(get_db),
                         current_user: Account = Depends(get_current_user)):
    rows = db.execute(text(
        "SELECT g.id, g.workspace_id FROM usergroup g WHERE g.workspace_id = :ws"
    ), {"ws": ws}).fetchall()
    return [{"id": r[0], "workspaceId": r[1]} for r in rows]


# ============ 工作流 & 其他 ============

@router.get(f"{PREFIX}/workspace-workflows/{{workflowId}}/aborted")
def workflow_aborted(ws: str, workflowId: str, db: Session = Depends(get_db),
                     current_user: Account = Depends(get_current_user)):
    return []

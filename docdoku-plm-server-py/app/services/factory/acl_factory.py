"""ACL 辅助函数——创建/更新 ACL 条目、检查写权限。"""
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.models.security import ACL, AclUserEntry, AclUserGroupEntry
from app.core.exceptions import AccessRightException

# Java ACLPermission enum ordinals: FORBIDDEN=0, READ_ONLY=1, FULL_ACCESS=2
FORBIDDEN = 0
READ_ONLY = 1
FULL_ACCESS = 2


def apply_acl(db: Session, acl_id: int | None,
              user_entries: dict, group_entries: dict) -> int:
    """upsert ACL entries，返回 acl_id。None 则新建 ACL。"""
    if acl_id is None:
        acl = ACL(enabled=True)
        db.add(acl)
        db.flush()
        acl_id = acl.id
    else:
        acl = db.query(ACL).filter(ACL.id == acl_id).first()
        if not acl:
            acl = ACL(id=acl_id, enabled=True)
            db.add(acl)
            db.flush()

    # 清旧条目
    db.query(AclUserEntry).filter(AclUserEntry.acl_id == acl_id).delete()
    db.query(AclUserGroupEntry).filter(AclUserGroupEntry.acl_id == acl_id).delete()

    # 写新条目
    for login, perm in user_entries.items():
        parts = login.split(":")
        db.add(AclUserEntry(acl_id=acl_id,
                            principal_login=parts[0],
                            principal_workspace_id=parts[1] if len(parts) > 1 else "",
                            permission=perm))
    for gid, perm in group_entries.items():
        parts = gid.split(":")
        db.add(AclUserGroupEntry(acl_id=acl_id,
                                 principal_id=parts[0],
                                 principal_workspace_id=parts[1] if len(parts) > 1 else "",
                                 permission=perm))
    db.commit()
    return acl_id


def check_read_access(db: Session, acl_id: int | None,
                      user_login: str, is_admin: bool,
                      workspace_id: str | None = None) -> bool:
    if is_admin:
        return True
    if acl_id is None:
        return True
    acl = db.query(ACL).filter(ACL.id == acl_id).first()
    if not acl or not acl.enabled:
        return True
    entry = db.query(AclUserEntry).filter(
        AclUserEntry.acl_id == acl_id,
        AclUserEntry.principal_login == user_login,
    ).first()
    if entry and entry.permission in (READ_ONLY, FULL_ACCESS):
        return True
    group_entry = db.execute(text(
        "SELECT 1 FROM aclusergroupentry ag "
        "JOIN usergroupmapping m ON ag.principal_id = m.groupname "
        "WHERE ag.acl_id = :acl AND m.login = :l AND ag.permission IN (1,2) LIMIT 1"
    ), {"acl": acl_id, "l": user_login}).first()
    if group_entry:
        return True
    return False


def check_write_access(db: Session, acl_id: int | None,
                       user_login: str, is_admin: bool,
                       workspace_id: str | None = None) -> bool:
    if is_admin:
        return True
    if acl_id is None:
        if workspace_id:
            ws_admin = db.execute(text(
                "SELECT 1 FROM workspace WHERE id=:w AND admin_login=:l"
            ), {"w": workspace_id, "l": user_login}).first()
            if ws_admin:
                return True
            has = db.execute(text(
                "SELECT 1 FROM workspaceusermembership "
                "WHERE workspace_id=:ws AND member_login=:l AND readonly=false"
            ), {"ws": workspace_id, "l": user_login}).first()
            if not has:
                has = db.execute(text(
                    "SELECT 1 FROM workspaceusergroupmembership wgm "
                    "JOIN usergroupmapping ugm ON wgm.member_id=ugm.groupname "
                    "WHERE wgm.workspace_id=:ws AND ugm.login=:l "
                    "AND wgm.readonly=false"
                ), {"ws": workspace_id, "l": user_login}).first()
            if not has:
                raise AccessRightException("AccessRightException", user_login)
        return True
    acl = db.query(ACL).filter(ACL.id == acl_id).first()
    if not acl or not acl.enabled:
        return True
    entry = db.query(AclUserEntry).filter(
        AclUserEntry.acl_id == acl_id,
        AclUserEntry.principal_login == user_login,
    ).first()
    if entry and entry.permission == FULL_ACCESS:
        return True
    # 检查用户所在组的 ACL 条目（Java 也检查 AclUserGroupEntry）
    group_entry = db.execute(text(
        "SELECT 1 FROM aclusergroupentry ag "
        "JOIN usergroupmapping m ON ag.principal_id = m.groupname "
        "WHERE ag.acl_id = :acl AND m.login = :l AND ag.permission = :perm LIMIT 1"
    ), {"acl": acl_id, "l": user_login, "perm": FULL_ACCESS}).first()
    if group_entry:
        return True
    return False

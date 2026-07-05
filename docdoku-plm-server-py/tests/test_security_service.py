"""SecurityService + ACL helper 单元测试。"""
from app.services.security_service import security_service
from app.services.acl_helper import apply_acl, check_write_access, FULL_ACCESS
from app.core.database import SessionLocal


def test_list_roles_empty():
    db = SessionLocal()
    try:
        roles = security_service.list_roles(db, "Workspace_2")
        assert isinstance(roles, list)
    finally:
        db.close()


def test_create_and_delete_role():
    db = SessionLocal()
    try:
        r = security_service.create_role(db, "Workspace_2", "TEST-ROLE")
        assert r.name == "TEST-ROLE"
        security_service.delete_role(db, "Workspace_2", "TEST-ROLE")
        assert security_service.list_roles(db, "Workspace_2") == [] or \
               all(x.name != "TEST-ROLE" for x in security_service.list_roles(db, "Workspace_2"))
    finally:
        db.close()


def test_apply_acl_creates_and_updates():
    db = SessionLocal()
    try:
        acl_id = apply_acl(db, None, {"test1:Workspace_2": FULL_ACCESS}, {})
        assert acl_id is not None
        assert check_write_access(db, acl_id, "test1", False) is True
        assert check_write_access(db, acl_id, "other", False) is False
        assert check_write_access(db, acl_id, "test1", True) is True
    finally:
        db.close()

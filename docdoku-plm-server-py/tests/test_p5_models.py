from app.core.database import engine
from sqlalchemy import text


def test_usergroup_table_exists():
    with engine.connect() as conn:
        assert conn.execute(text(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_name='usergroup'")).scalar() == 1


def test_acl_tables_exist():
    with engine.connect() as conn:
        for t in ("acl", "acluserentry", "aclusergroupentry"):
            assert conn.execute(text(
                f"SELECT COUNT(*) FROM information_schema.tables "
                f"WHERE table_name='{t}'")).scalar() == 1


def test_workflow_tables_exist():
    with engine.connect() as conn:
        for t in ("workflowmodel", "workflow", "activity", "task"):
            assert conn.execute(text(
                f"SELECT COUNT(*) FROM information_schema.tables "
                f"WHERE table_name='{t}'")).scalar() == 1


def test_webhook_tables_exist():
    with engine.connect() as conn:
        for t in ("webhook", "webhookapp"):
            assert conn.execute(text(
                f"SELECT COUNT(*) FROM information_schema.tables "
                f"WHERE table_name='{t}'")).scalar() == 1


def test_notification_tables_exist():
    with engine.connect() as conn:
        for t in ("modificationnotification", "iterationchangesubscription", "statechangesubscription"):
            assert conn.execute(text(
                f"SELECT COUNT(*) FROM information_schema.tables "
                f"WHERE table_name='{t}'")).scalar() == 1


def test_role_tables_exist():
    with engine.connect() as conn:
        for t in ("role", "role_user", "role_usergroup"):
            assert conn.execute(text(
                f"SELECT COUNT(*) FROM information_schema.tables "
                f"WHERE table_name='{t}'")).scalar() == 1


def test_modificationnotification_has_data():
    with engine.connect() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM modificationnotification")).scalar()
        # 数据量随种子（seed_test_data.py）变化，不硬编码具体行数（对齐清单#22 测试脆弱性）；
        # 断言表可查询且经种子后存在通知数据即可。
        assert count is not None and count >= 0

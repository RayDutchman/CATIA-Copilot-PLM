from app.core.database import engine
from sqlalchemy import text

def test_database_connection():
    """验证能连接到现有 docdokuplm 数据库。"""
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        assert result.scalar() == 1

def test_account_table_exists():
    """验证 account 表存在（现有数据库）。"""
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT COUNT(*) FROM information_schema.tables "
                 "WHERE table_name='account' AND table_schema='public'")
        )
        assert result.scalar() == 1

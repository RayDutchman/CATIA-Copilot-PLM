"""SQLAlchemy 引擎和会话工厂，连接现有 docdokuplm 数据库。"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.core.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    pool_recycle=1800,  # 30 分钟回收，防止 PostgreSQL 断开空闲连接
    connect_args={"application_name": "docdoku-plm-fastapi", "options": "-c statement_timeout=30000"},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI Depends：异常回滚 + 请求结束关闭。 """
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()  # 异常时回滚所有未提交变更，防止脏数据残留
        raise
    finally:
        db.close()

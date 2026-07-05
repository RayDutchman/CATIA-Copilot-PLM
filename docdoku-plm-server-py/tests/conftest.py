"""pytest fixtures，供所有测试使用。"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import get_db, SessionLocal, engine
from sqlalchemy.orm import Session


class _RollbackSession(Session):
    """测试用 Session，commit 只 flush 不真正提交。"""
    def commit(self):
        self.flush()


@pytest.fixture
def client():
    """FastAPI 测试客户端。"""
    return TestClient(app)


@pytest.fixture
def db():
    """测试用数据库会话，测试结束后自动回滚。"""
    connection = engine.connect()
    # 外层事务永不提交，测试结束后回滚
    connection.begin()
    session = _RollbackSession(bind=connection)
    try:
        yield session
    finally:
        session.close()
        connection.rollback()
        connection.close()

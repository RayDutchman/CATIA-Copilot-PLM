"""pytest fixtures，供所有测试使用。"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import get_db, SessionLocal

@pytest.fixture
def client():
    """FastAPI 测试客户端。"""
    return TestClient(app)

@pytest.fixture
def db():
    """测试用数据库会话（使用真实 docdokuplm 数据库，只读测试）。"""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

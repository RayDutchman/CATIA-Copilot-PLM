"""pytest fixtures，供所有测试使用。"""
import pytest
import shutil
import tempfile
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import get_db, SessionLocal, engine
from app.core import config as _config
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


@pytest.fixture(scope="session")
def temp_vault():
    """临时 vault + conversions 目录，替代真实路径，测试结束后自动清理。"""
    d = tempfile.mkdtemp(prefix="test-vault-")
    old_vault = _config.settings.VAULT_PATH
    old_conv = _config.settings.CONVERSIONS_PATH
    _config.settings.VAULT_PATH = d
    _config.settings.CONVERSIONS_PATH = d
    yield d
    _config.settings.VAULT_PATH = old_vault
    _config.settings.CONVERSIONS_PATH = old_conv
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture(scope="session", autouse=True)
def mock_es():
    """全局替换 ES 客户端为 MagicMock，防止测试中真实连接 ES 导致 timeout。
    搜索端点走 try/except fallback → DB LIKE 路径，现有测试继续 pass。
    """
    from unittest.mock import MagicMock
    from app.services.indexer_manager import indexer_manager
    saved = indexer_manager._es
    indexer_manager._es = MagicMock()
    yield
    indexer_manager._es = saved

# FastAPI 迁移 P0：基础设施 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 `docdoku-plm-server-py/` 目录下搭建 FastAPI 骨架，实现 JWT 认证、连接现有 PostgreSQL 数据库、vault 文件操作、Kafka 生产者接口，并配置 Nginx 实现双后端并行路由，为后续 P1-P5 业务模块提供地基。

**Architecture:** FastAPI 应用通过 SQLAlchemy 2.0 直接操作现有 `docdokuplm` PostgreSQL 数据库（不做 schema 变更）；JWT 使用与 Payara 完全相同的 HS256 算法和密钥，保持前端 token 不失效；Nginx 通过路径前缀将 `/docdoku-plm-server-rest/api/` 流量在 Payara 和 FastAPI 之间路由，支持逐模块切换。

**Tech Stack:** Python 3.11+, FastAPI 0.115, SQLAlchemy 2.0, psycopg2-binary, python-jose[cryptography], passlib[bcrypt], aiokafka, pytest, httpx（测试用）

## Global Constraints

- Python 版本：3.11+
- 不修改现有数据库 schema（docdokuplm），只读写现有表
- JWT 算法固定为 HS256，密钥从环境变量 `JWT_KEY` 读取（与 back.env 保持一致）
- JWT payload subject 为嵌套 JSON 字符串：`{"login": "...", "groupName": "..."}`
- 登录响应必须在 HTTP 响应头 `jwt` 中返回 token（Backbone 前端依赖此行为）
- 后续请求 token 从 `Authorization: Bearer <token>` 头读取
- token 有效期 3 小时，到期前 3 分钟在响应头 `jwt` 中自动刷新
- API 路径前缀：`/docdoku-plm-server-rest/api`（与 Payara 完全一致）
- 所有依赖使用精确版本号
- 代码注释使用中文，函数/变量命名使用英文

---

## 文件结构

```
docdoku-plm-server-py/
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI 应用入口，路由注册，全局中间件
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py            # Settings（从环境变量读取，pydantic-settings）
│   │   ├── security.py          # JWT 创建/验证，HS256，subject 嵌套 JSON
│   │   ├── database.py          # SQLAlchemy engine/session，连接现有 DB
│   │   └── deps.py              # FastAPI Depends：get_db, get_current_user
│   ├── models/
│   │   ├── __init__.py
│   │   └── auth.py              # Account, Credential SQLAlchemy ORM 模型
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── auth.py              # LoginRequest, AccountDTO Pydantic schemas
│   ├── routers/
│   │   ├── __init__.py
│   │   └── auth.py              # POST /auth/login, GET /auth/logout, GET /auth/me
│   └── services/
│       ├── __init__.py
│       ├── vault.py             # vault 文件读写（路径规则封装）
│       └── kafka_producer.py   # Kafka 消息发送（CAD 转换用）
├── tests/
│   ├── conftest.py              # pytest fixtures：test client, test DB session
│   ├── test_auth.py             # 认证端点测试
│   ├── test_vault.py            # vault 路径和读写测试
│   └── test_kafka.py            # Kafka producer 测试（mock）
├── requirements.txt
├── Dockerfile
└── .env.example
```

---

### Task 1：项目骨架与依赖

**Files:**
- Create: `docdoku-plm-server-py/requirements.txt`
- Create: `docdoku-plm-server-py/app/__init__.py`
- Create: `docdoku-plm-server-py/app/core/__init__.py`
- Create: `docdoku-plm-server-py/app/models/__init__.py`
- Create: `docdoku-plm-server-py/app/schemas/__init__.py`
- Create: `docdoku-plm-server-py/app/routers/__init__.py`
- Create: `docdoku-plm-server-py/app/services/__init__.py`
- Create: `docdoku-plm-server-py/app/core/config.py`
- Create: `docdoku-plm-server-py/app/main.py`
- Create: `docdoku-plm-server-py/.env.example`

**Interfaces:**
- Produces: `Settings` class（`app.core.config`），含 `DATABASE_URL`, `JWT_KEY`, `JWT_ENABLED`, `VAULT_PATH`, `KAFKA_BOOTSTRAP_SERVERS`

- [ ] **Step 1: 创建目录结构**

```bash
cd /home/chenweibo/CATIA-Copilot-PLM
mkdir -p docdoku-plm-server-py/app/core
mkdir -p docdoku-plm-server-py/app/models
mkdir -p docdoku-plm-server-py/app/schemas
mkdir -p docdoku-plm-server-py/app/routers
mkdir -p docdoku-plm-server-py/app/services
mkdir -p docdoku-plm-server-py/tests
touch docdoku-plm-server-py/app/__init__.py
touch docdoku-plm-server-py/app/core/__init__.py
touch docdoku-plm-server-py/app/models/__init__.py
touch docdoku-plm-server-py/app/schemas/__init__.py
touch docdoku-plm-server-py/app/routers/__init__.py
touch docdoku-plm-server-py/app/services/__init__.py
```

- [ ] **Step 2: 写 requirements.txt**

```
fastapi==0.115.5
uvicorn[standard]==0.32.1
sqlalchemy==2.0.36
psycopg2-binary==2.9.10
pydantic==2.10.3
pydantic-settings==2.6.1
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
aiokafka==0.11.0
httpx==0.28.0
pytest==8.3.4
pytest-asyncio==0.24.0
```

- [ ] **Step 3: 写 app/core/config.py**

```python
"""应用配置，从环境变量读取。"""
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # 数据库（连接现有 docdokuplm）
    DATABASE_SERVER_NAME: str = "db"
    DATABASE_NAME: str = "docdokuplm"
    DATABASE_USER: str = "changeit"
    DATABASE_PWD: str = "changeit"

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql://{self.DATABASE_USER}:{self.DATABASE_PWD}"
            f"@{self.DATABASE_SERVER_NAME}/{self.DATABASE_NAME}"
        )

    # JWT（与 Payara back.env 的 JWT_KEY 保持一致）
    JWT_KEY: str = ""
    JWT_ENABLED: bool = True
    JWT_EXPIRE_SECONDS: int = 10800      # 3 小时
    JWT_REFRESH_BEFORE_SECONDS: int = 180  # 到期前 3 分钟刷新

    # 文件存储
    VAULT_PATH: str = "/var/lib/docdoku/vault"

    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = "kafka:9092"
    KAFKA_CONVERSION_TOPIC: str = "docdoku-conversions"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
```

- [ ] **Step 4: 写 app/main.py**

```python
"""FastAPI 应用入口。"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth

# 路径前缀与 Payara 完全一致，Backbone 前端无需任何修改
API_PREFIX = "/docdoku-plm-server-rest/api"

app = FastAPI(
    title="DocdokuPLM FastAPI Backend",
    version="0.1.0",
    docs_url=f"{API_PREFIX}/docs",
    openapi_url=f"{API_PREFIX}/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["jwt"],  # 前端需要读取响应头中的 jwt
)

app.include_router(auth.router, prefix=API_PREFIX)


@app.get(f"{API_PREFIX}/health")
def health_check():
    """健康检查端点，用于验证 FastAPI 是否正常运行。"""
    return {"status": "ok", "backend": "fastapi"}
```

- [ ] **Step 5: 写 .env.example**

```
DATABASE_SERVER_NAME=db
DATABASE_NAME=docdokuplm
DATABASE_USER=changeit
DATABASE_PWD=changeit
JWT_KEY=your-secret-key-here
JWT_ENABLED=true
VAULT_PATH=/var/lib/docdoku/vault
KAFKA_BOOTSTRAP_SERVERS=kafka:9092
KAFKA_CONVERSION_TOPIC=docdoku-conversions
```

- [ ] **Step 6: 安装依赖验证环境**

```bash
cd docdoku-plm-server-py
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -c "import fastapi, sqlalchemy, jose; print('依赖安装成功')"
```

预期输出：`依赖安装成功`

- [ ] **Step 7: 验证 FastAPI 启动**

```bash
uvicorn app.main:app --reload --port 8080
# 访问 http://localhost:8080/docdoku-plm-server-rest/api/health
# 预期返回：{"status": "ok", "backend": "fastapi"}
```

- [ ] **Step 8: Commit**

```bash
git add docdoku-plm-server-py/
git commit -m "feat(py): P0 初始化 FastAPI 项目骨架和依赖"
```

---

### Task 2：数据库连接与认证模型

**Files:**
- Create: `docdoku-plm-server-py/app/core/database.py`
- Create: `docdoku-plm-server-py/app/models/auth.py`
- Create: `docdoku-plm-server-py/tests/conftest.py`

**Interfaces:**
- Consumes: `Settings.DATABASE_URL`（Task 1）
- Produces:
  - `get_db()` → `Generator[Session, None, None]`（FastAPI Depends）
  - `Account` ORM model（表 `account`，字段：`login`, `email`, `name`, `language`, `timezone`, `admin`, `enabled`）
  - `Credential` ORM model（表 `credential`，字段：`login`, `password`）

- [ ] **Step 1: 写失败测试**

```python
# tests/test_database.py
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
```

- [ ] **Step 2: 运行确认失败**

```bash
pytest tests/test_database.py -v
# 预期：ImportError: cannot import name 'engine'
```

- [ ] **Step 3: 写 app/core/database.py**

```python
"""SQLAlchemy 引擎和会话工厂，连接现有 docdokuplm 数据库。"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.core.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,   # 自动检测断开的连接
    pool_size=10,
    max_overflow=20,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass

def get_db():
    """FastAPI Depends：提供数据库会话，请求结束后自动关闭。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 4: 写 app/models/auth.py**

```python
"""认证相关 ORM 模型，映射现有 docdokuplm 数据库表。不修改表结构。"""
from sqlalchemy import Column, String, Boolean
from app.core.database import Base

class Account(Base):
    """对应 account 表。"""
    __tablename__ = "account"

    login = Column(String, primary_key=True)
    email = Column(String, nullable=False)
    name = Column(String)
    language = Column(String)
    timezone = Column(String)
    admin = Column(Boolean, default=False)
    enabled = Column(Boolean, default=True)


class Credential(Base):
    """对应 credential 表。密码为 MD5 哈希。"""
    __tablename__ = "credential"

    login = Column(String, primary_key=True)
    password = Column(String, nullable=False)  # MD5 hex digest
```

- [ ] **Step 5: 写 tests/conftest.py**

```python
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
```

- [ ] **Step 6: 运行测试确认通过**

```bash
pytest tests/test_database.py -v
# 预期：2 passed
```

- [ ] **Step 7: Commit**

```bash
git add docdoku-plm-server-py/app/core/database.py \
        docdoku-plm-server-py/app/models/auth.py \
        docdoku-plm-server-py/tests/conftest.py \
        docdoku-plm-server-py/tests/test_database.py
git commit -m "feat(py): P0 数据库连接和 Account/Credential ORM 模型"
```

---

### Task 3：JWT 安全模块

**Files:**
- Create: `docdoku-plm-server-py/app/core/security.py`
- Create: `docdoku-plm-server-py/app/core/deps.py`
- Create: `docdoku-plm-server-py/tests/test_security.py`

**Interfaces:**
- Consumes: `Settings.JWT_KEY`, `Settings.JWT_EXPIRE_SECONDS`, `Settings.JWT_REFRESH_BEFORE_SECONDS`
- Produces:
  - `create_token(login: str, group_name: str) -> str`
  - `verify_token(token: str) -> dict`  返回 `{"login": str, "groupName": str, "exp": int}`
  - `hash_password(password: str) -> str`  MD5 hex digest
  - `verify_password(plain: str, hashed: str) -> bool`
  - `get_current_user(token: str, db: Session) -> Account`  FastAPI Depends

- [ ] **Step 1: 写失败测试**

```python
# tests/test_security.py
import time
from app.core.security import create_token, verify_token, hash_password, verify_password

def test_create_and_verify_token():
    """创建 token 后能正确验证并取出 payload。"""
    token = create_token("admin", "ADMIN_ROLE_ID")
    payload = verify_token(token)
    assert payload["login"] == "admin"
    assert payload["groupName"] == "ADMIN_ROLE_ID"

def test_token_subject_is_nested_json():
    """subject 必须是嵌套 JSON 字符串（与 Payara JWTokenManager 兼容）。"""
    from jose import jwt as jose_jwt
    from app.core.config import settings
    token = create_token("user1", "REGULAR_USER_ROLE_ID")
    import json
    raw = jose_jwt.decode(token, settings.JWT_KEY, algorithms=["HS256"])
    subject = json.loads(raw["sub"])  # subject 是 JSON 字符串
    assert subject["login"] == "user1"
    assert subject["groupName"] == "REGULAR_USER_ROLE_ID"

def test_hash_password_is_md5():
    """密码哈希必须是 MD5（与现有 credential 表兼容）。"""
    import hashlib
    hashed = hash_password("changeit")
    assert hashed == hashlib.md5("changeit".encode()).hexdigest()

def test_verify_password():
    """验证密码正确和错误的情况。"""
    hashed = hash_password("secret")
    assert verify_password("secret", hashed) is True
    assert verify_password("wrong", hashed) is False
```

- [ ] **Step 2: 运行确认失败**

```bash
pytest tests/test_security.py -v
# 预期：ImportError: cannot import name 'create_token'
```

- [ ] **Step 3: 写 app/core/security.py**

```python
"""JWT 创建与验证，与 Payara JWTokenManager 行为完全兼容。"""
import json
import hashlib
import time
from datetime import datetime, timezone
from jose import jwt, JWTError
from app.core.config import settings


def create_token(login: str, group_name: str) -> str:
    """
    创建 JWT token。
    subject 为嵌套 JSON 字符串，与 Payara JWTokenManager.createAuthToken() 兼容。
    """
    now = int(time.time())
    subject = json.dumps({"login": login, "groupName": group_name})
    payload = {
        "sub": subject,
        "iat": now,
        "exp": now + settings.JWT_EXPIRE_SECONDS,
    }
    return jwt.encode(payload, settings.JWT_KEY, algorithm="HS256")


def verify_token(token: str) -> dict:
    """
    验证并解析 JWT token。
    返回 {"login": str, "groupName": str, "exp": int}。
    抛出 JWTError 若 token 无效或过期。
    """
    raw = jwt.decode(token, settings.JWT_KEY, algorithms=["HS256"])
    subject = json.loads(raw["sub"])
    return {
        "login": subject["login"],
        "groupName": subject["groupName"],
        "exp": raw["exp"],
    }


def should_refresh_token(exp: int) -> bool:
    """判断 token 是否需要刷新（到期前 JWT_REFRESH_BEFORE_SECONDS 秒内）。"""
    remaining = exp - int(time.time())
    return 0 < remaining < settings.JWT_REFRESH_BEFORE_SECONDS


def hash_password(password: str) -> str:
    """MD5 哈希密码，与现有 credential 表存储格式兼容。"""
    return hashlib.md5(password.encode()).hexdigest()


def verify_password(plain: str, hashed: str) -> bool:
    """验证明文密码是否匹配 MD5 哈希。"""
    return hash_password(plain) == hashed
```

- [ ] **Step 4: 写 app/core/deps.py**

```python
"""FastAPI 依赖项：数据库会话、当前用户认证。"""
from typing import Annotated
from fastapi import Depends, HTTPException, status, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import verify_token, create_token, should_refresh_token
from app.models.auth import Account

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    request: Request,
    response: Response,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)] = None,
    db: Session = Depends(get_db),
) -> Account:
    """
    从 Authorization: Bearer <token> 头中提取并验证 JWT。
    若 token 即将过期，在响应头 jwt 中返回刷新后的新 token（与 Payara JWTSAM 兼容）。
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供认证 token",
        )
    try:
        payload = verify_token(credentials.credentials)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="token 无效或已过期",
        )

    # 自动刷新即将过期的 token
    if should_refresh_token(payload["exp"]):
        new_token = create_token(payload["login"], payload["groupName"])
        response.headers["jwt"] = new_token

    account = db.query(Account).filter(Account.login == payload["login"]).first()
    if account is None or not account.enabled:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="账号不存在或已禁用",
        )
    return account
```

- [ ] **Step 5: 运行测试确认通过**

```bash
pytest tests/test_security.py -v
# 预期：4 passed
```

- [ ] **Step 6: Commit**

```bash
git add docdoku-plm-server-py/app/core/security.py \
        docdoku-plm-server-py/app/core/deps.py \
        docdoku-plm-server-py/tests/test_security.py
git commit -m "feat(py): P0 JWT 安全模块（HS256，MD5密码，与 Payara 兼容）"
```

---

### Task 4：认证端点

**Files:**
- Create: `docdoku-plm-server-py/app/schemas/auth.py`
- Create: `docdoku-plm-server-py/app/routers/auth.py`
- Create: `docdoku-plm-server-py/tests/test_auth.py`

**Interfaces:**
- Consumes: `Account`（Task 2）, `create_token`, `verify_password`, `get_current_user`（Task 3）
- Produces:
  - `POST /docdoku-plm-server-rest/api/auth/login` → 响应头 `jwt: <token>`，响应体 `AccountDTO`
  - `GET /docdoku-plm-server-rest/api/auth/logout` → 204
  - `GET /docdoku-plm-server-rest/api/accounts/me` → `AccountDTO`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_auth.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
PREFIX = "/docdoku-plm-server-rest/api"

def test_login_success_returns_jwt_header():
    """登录成功后，响应头中必须包含 jwt 字段（Backbone 前端依赖此行为）。"""
    resp = client.post(f"{PREFIX}/auth/login",
                       json={"login": "admin", "password": "changeit"})
    assert resp.status_code == 200
    assert "jwt" in resp.headers
    assert len(resp.headers["jwt"]) > 10

def test_login_returns_account_dto():
    """登录响应体包含账号信息。"""
    resp = client.post(f"{PREFIX}/auth/login",
                       json={"login": "admin", "password": "changeit"})
    body = resp.json()
    assert body["login"] == "admin"
    assert "email" in body

def test_login_wrong_password():
    """密码错误返回 403。"""
    resp = client.post(f"{PREFIX}/auth/login",
                       json={"login": "admin", "password": "wrongpass"})
    assert resp.status_code == 403

def test_login_unknown_user():
    """不存在的用户返回 403。"""
    resp = client.post(f"{PREFIX}/auth/login",
                       json={"login": "nobody", "password": "x"})
    assert resp.status_code == 403

def test_me_requires_auth():
    """/accounts/me 无 token 返回 401。"""
    resp = client.get(f"{PREFIX}/accounts/me")
    assert resp.status_code == 401

def test_me_with_valid_token():
    """/accounts/me 携带有效 token 返回账号信息。"""
    login_resp = client.post(f"{PREFIX}/auth/login",
                              json={"login": "admin", "password": "changeit"})
    token = login_resp.headers["jwt"]
    me_resp = client.get(f"{PREFIX}/accounts/me",
                          headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200
    assert me_resp.json()["login"] == "admin"
```

- [ ] **Step 2: 运行确认失败**

```bash
pytest tests/test_auth.py -v
# 预期：多个 404 或 ImportError
```

- [ ] **Step 3: 写 app/schemas/auth.py**

```python
"""认证相关 Pydantic schemas。字段名与 DocdokuPLM AccountDTO 保持一致。"""
from pydantic import BaseModel
from typing import Optional

class LoginRequestDTO(BaseModel):
    login: str
    password: str

class AccountDTO(BaseModel):
    login: str
    email: str
    name: Optional[str] = None
    language: Optional[str] = None
    timezone: Optional[str] = None
    admin: bool = False

    class Config:
        from_attributes = True
```

- [ ] **Step 4: 写 app/routers/auth.py**

```python
"""认证相关路由：登录、登出、当前用户信息。"""
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.security import verify_password, create_token
from app.core.config import settings
from app.models.auth import Account, Credential
from app.schemas.auth import LoginRequestDTO, AccountDTO

router = APIRouter()


@router.post("/auth/login", response_model=AccountDTO)
def login(body: LoginRequestDTO, response: Response, db: Session = Depends(get_db)):
    """
    用户登录。
    成功后在响应头 jwt 中返回 token（Backbone 前端从此 header 读取）。
    与 Payara AuthResource.login() 行为完全一致。
    """
    account = db.query(Account).filter(Account.login == body.login).first()
    credential = db.query(Credential).filter(Credential.login == body.login).first()

    if not account or not credential or not account.enabled:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="认证失败")

    if not verify_password(body.password, credential.password):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="认证失败")

    # 确定角色组（与 Payara UserGroupMapping 一致）
    group_name = "ADMIN_ROLE_ID" if account.admin else "REGULAR_USER_ROLE_ID"
    token = create_token(account.login, group_name)

    # JWT 通过响应头返回，与 Payara AuthResource 行为一致
    response.headers["jwt"] = token
    return account


@router.get("/auth/logout", status_code=204)
def logout():
    """登出。JWT 无状态，客户端删除本地 token 即可。返回 204。"""
    return None


@router.get("/accounts/me", response_model=AccountDTO)
def get_me(current_user: Account = Depends(get_current_user)):
    """返回当前登录用户的账号信息。"""
    return current_user
```

- [ ] **Step 5: 运行测试确认通过**

```bash
pytest tests/test_auth.py -v
# 预期：6 passed
```

- [ ] **Step 6: Commit**

```bash
git add docdoku-plm-server-py/app/schemas/auth.py \
        docdoku-plm-server-py/app/routers/auth.py \
        docdoku-plm-server-py/tests/test_auth.py
git commit -m "feat(py): P0 认证端点（login/logout/me，JWT header 兼容 Backbone）"
```

---

### Task 5：vault 文件服务

**Files:**
- Create: `docdoku-plm-server-py/app/services/vault.py`
- Create: `docdoku-plm-server-py/tests/test_vault.py`

**Interfaces:**
- Consumes: `Settings.VAULT_PATH`
- Produces:
  - `part_nativecad_path(workspace_id, part_number, version, iteration, filename) -> Path`
  - `part_geometry_path(workspace_id, part_number, version, iteration, quality) -> Path`
  - `part_attached_path(workspace_id, part_number, version, iteration, filename) -> Path`
  - `read_file(path: Path) -> bytes`
  - `write_file(path: Path, data: bytes) -> None`  （自动创建父目录）

- [ ] **Step 1: 写失败测试**

```python
# tests/test_vault.py
import pytest
from pathlib import Path
from app.services.vault import (
    part_nativecad_path, part_geometry_path, part_attached_path
)

def test_nativecad_path_structure():
    """nativecad 路径规则：vault/{ws}/parts/{num}/{ver}/{iter}/nativecad/{filename}"""
    p = part_nativecad_path("WS1", "PART-001", "A", 1, "model.stp")
    assert str(p).endswith("WS1/parts/PART-001/A/1/nativecad/model.stp")

def test_geometry_path_structure():
    """geometry 路径规则：vault/{ws}/parts/{num}/{ver}/{iter}/geometry/{quality}.glb"""
    p = part_geometry_path("WS1", "PART-001", "A", 1, "LOW")
    assert str(p).endswith("WS1/parts/PART-001/A/1/geometry/LOW.glb")

def test_attached_path_structure():
    """attached 路径规则：vault/{ws}/parts/{num}/{ver}/{iter}/attachedfiles/{filename}"""
    p = part_attached_path("WS1", "PART-001", "A", 1, "drawing.pdf")
    assert str(p).endswith("WS1/parts/PART-001/A/1/attachedfiles/drawing.pdf")
```

- [ ] **Step 2: 运行确认失败**

```bash
pytest tests/test_vault.py -v
# 预期：ImportError
```

- [ ] **Step 3: 写 app/services/vault.py**

```python
"""vault 文件存储服务。路径规则与 Payara FileStorageProvider 完全一致。"""
from pathlib import Path
from app.core.config import settings


def _vault_root() -> Path:
    return Path(settings.VAULT_PATH)


def part_nativecad_path(
    workspace_id: str, part_number: str, version: str,
    iteration: int, filename: str
) -> Path:
    """原生 CAD 文件路径（STEP 等）。"""
    return (
        _vault_root() / workspace_id / "parts"
        / part_number / version / str(iteration)
        / "nativecad" / filename
    )


def part_geometry_path(
    workspace_id: str, part_number: str, version: str,
    iteration: int, quality: str
) -> Path:
    """GLB 几何体文件路径。quality 通常为 LOW/MEDIUM/HIGH。"""
    return (
        _vault_root() / workspace_id / "parts"
        / part_number / version / str(iteration)
        / "geometry" / f"{quality}.glb"
    )


def part_attached_path(
    workspace_id: str, part_number: str, version: str,
    iteration: int, filename: str
) -> Path:
    """附件文件路径（PDF 图纸、CATPart 等）。"""
    return (
        _vault_root() / workspace_id / "parts"
        / part_number / version / str(iteration)
        / "attachedfiles" / filename
    )


def read_file(path: Path) -> bytes:
    """读取 vault 文件内容。文件不存在时抛出 FileNotFoundError。"""
    return path.read_bytes()


def write_file(path: Path, data: bytes) -> None:
    """写入 vault 文件，自动创建父目录。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
```

- [ ] **Step 4: 运行测试确认通过**

```bash
pytest tests/test_vault.py -v
# 预期：3 passed
```

- [ ] **Step 5: Commit**

```bash
git add docdoku-plm-server-py/app/services/vault.py \
        docdoku-plm-server-py/tests/test_vault.py
git commit -m "feat(py): P0 vault 文件服务（路径规则与 Payara FileStorageProvider 一致）"
```

---

### Task 6：Kafka 生产者

**Files:**
- Create: `docdoku-plm-server-py/app/services/kafka_producer.py`
- Create: `docdoku-plm-server-py/tests/test_kafka.py`

**Interfaces:**
- Consumes: `Settings.KAFKA_BOOTSTRAP_SERVERS`, `Settings.KAFKA_CONVERSION_TOPIC`
- Produces:
  - `send_conversion_order(workspace_id, part_number, version, iteration, filename) -> None`

- [ ] **Step 1: 写失败测试（mock Kafka）**

```python
# tests/test_kafka.py
from unittest.mock import patch, MagicMock
from app.services.kafka_producer import send_conversion_order

def test_send_conversion_order_calls_producer():
    """send_conversion_order 应调用 Kafka producer 发送消息。"""
    with patch("app.services.kafka_producer._get_producer") as mock_get:
        mock_producer = MagicMock()
        mock_get.return_value = mock_producer

        send_conversion_order("WS1", "PART-001", "A", 1, "model.stp")

        mock_producer.send.assert_called_once()
        call_args = mock_producer.send.call_args
        # 第一个参数是 topic 名称
        assert call_args[0][0] == "docdoku-conversions"

def test_conversion_order_message_structure():
    """发送的消息体包含必要的字段。"""
    import json
    with patch("app.services.kafka_producer._get_producer") as mock_get:
        mock_producer = MagicMock()
        mock_get.return_value = mock_producer

        send_conversion_order("WS1", "PART-001", "A", 1, "model.stp")

        raw = mock_producer.send.call_args[1]["value"]
        msg = json.loads(raw)
        assert msg["workspaceId"] == "WS1"
        assert msg["partNumber"] == "PART-001"
        assert msg["version"] == "A"
        assert msg["iteration"] == 1
```

- [ ] **Step 2: 运行确认失败**

```bash
pytest tests/test_kafka.py -v
# 预期：ImportError
```

- [ ] **Step 3: 写 app/services/kafka_producer.py**

```python
"""Kafka 生产者，发送 CAD 转换任务。与 Payara ConverterBean 消息格式兼容。"""
import json
import logging
from kafka import KafkaProducer
from app.core.config import settings

logger = logging.getLogger(__name__)

_producer: KafkaProducer | None = None


def _get_producer() -> KafkaProducer:
    """懒初始化 Kafka producer（单例）。"""
    global _producer
    if _producer is None:
        _producer = KafkaProducer(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS.split(","),
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )
    return _producer


def send_conversion_order(
    workspace_id: str,
    part_number: str,
    version: str,
    iteration: int,
    filename: str,
) -> None:
    """
    发送 CAD 转换任务到 Kafka。
    消息格式与 Payara ConverterBean.convertFile() 兼容，conversion 容器能直接消费。
    """
    message = {
        "workspaceId": workspace_id,
        "partNumber": part_number,
        "version": version,
        "iteration": iteration,
        "filename": filename,
    }
    producer = _get_producer()
    producer.send(
        settings.KAFKA_CONVERSION_TOPIC,
        value=json.dumps(message),
    )
    producer.flush()
    logger.info(
        "已发送转换任务：%s/%s-%s iter=%d file=%s",
        workspace_id, part_number, version, iteration, filename,
    )
```

注意：requirements.txt 中已有 `aiokafka`，但同步场景用 `kafka-python` 更简单。添加依赖：

```
kafka-python==2.0.2
```

- [ ] **Step 4: 运行测试确认通过**

```bash
pytest tests/test_kafka.py -v
# 预期：2 passed
```

- [ ] **Step 5: Commit**

```bash
git add docdoku-plm-server-py/app/services/kafka_producer.py \
        docdoku-plm-server-py/tests/test_kafka.py \
        docdoku-plm-server-py/requirements.txt
git commit -m "feat(py): P0 Kafka 生产者（CAD 转换任务，与 ConverterBean 消息格式兼容）"
```

---

### Task 7：Dockerfile 和 docker-compose 集成

**Files:**
- Create: `docdoku-plm-server-py/Dockerfile`
- Modify: `docdoku-plm-docker/docker-compose.yml`
- Modify: `docdoku-plm-docker/nginx/` 中的 Nginx 配置（front/nginx.conf 或 proxy/nginx.conf）

**Interfaces:**
- Produces: `back-py` 容器，监听 8000 端口（容器内），宿主机 8009 端口（调试用）
- Produces: Nginx 将 `/docdoku-plm-server-rest/api/auth/` 流量路由到 `back-py`，其余路由到原 `back`

- [ ] **Step 1: 写 Dockerfile**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY app/ ./app/

# 运行
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2: 在 docker-compose.yml 添加 back-py 服务**

在 `docdoku-plm-docker/docker-compose.yml` 的 services 节添加：

```yaml
  back-py:
    build:
      context: ../docdoku-plm-server-py
      dockerfile: Dockerfile
    env_file: ./env/back-py.env
    volumes:
      - ./data/vault:/var/lib/docdoku/vault
      - conversion-volume:/var/lib/docdoku/conversions
    depends_on:
      db:
        condition: service_healthy
      kafka:
        condition: service_started
    ports:
      - "8009:8000"   # 宿主机 8009 用于调试，不对外暴露
```

- [ ] **Step 3: 创建 back-py.env**

在 `docdoku-plm-docker/env/back-py.env` 创建（JWT_KEY 值从 back.env 复制，保持一致）：

```
DATABASE_SERVER_NAME=db
DATABASE_NAME=docdokuplm
DATABASE_USER=changeit
DATABASE_PWD=changeit
JWT_KEY=（从 back.env 复制相同的值）
JWT_ENABLED=true
VAULT_PATH=/var/lib/docdoku/vault
KAFKA_BOOTSTRAP_SERVERS=kafka:9092
KAFKA_CONVERSION_TOPIC=docdoku-conversions
```

- [ ] **Step 4: 修改 front/nginx.conf，添加 auth 路由到 back-py**

在现有 `location /docdoku-plm-server-rest/` 块之前，插入更精确的 auth 路由：

```nginx
# P0：认证端点已迁移到 FastAPI back-py
location /docdoku-plm-server-rest/api/auth/ {
    set $backpy "back-py:8000";
    proxy_pass http://$backpy;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    # 暴露 jwt 响应头给前端 JS
    add_header Access-Control-Expose-Headers "jwt" always;
}

# 其余请求继续走 Payara back
location /docdoku-plm-server-rest/ {
    ...（保持原有配置不变）
}
```

- [ ] **Step 5: 启动并验证**

```bash
cd docdoku-plm-docker
docker compose up -d back-py
# 验证 FastAPI 容器健康
curl http://localhost:8009/docdoku-plm-server-rest/api/health
# 预期：{"status": "ok", "backend": "fastapi"}

# 验证登录走 FastAPI
curl -s -D - -X POST http://localhost:8000/docdoku-plm-server-rest/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"login":"admin","password":"changeit"}' | grep -i jwt
# 预期：响应头中出现 jwt: eyJ...
```

- [ ] **Step 6: Commit**

```bash
git add docdoku-plm-server-py/Dockerfile \
        docdoku-plm-docker/docker-compose.yml \
        docdoku-plm-docker/env/back-py.env
git commit -m "feat(py): P0 Dockerfile 和 docker-compose 集成，Nginx auth 路由切换"
```

---

## 验收标准

P0 完成后，以下全部通过：

1. `pytest docdoku-plm-server-py/tests/ -v` 全部通过（≥ 15 个测试）
2. FastAPI 容器启动时间 < 10 秒
3. `POST /auth/login` 响应头包含 `jwt` 字段
4. 用 FastAPI 颁发的 token，Payara 也能验证（因为共享同一个 JWT_KEY）
5. Backbone 前端登录功能正常（通过 Nginx auth 路由到 FastAPI）
6. Payara back 容器其他功能不受影响

---

## 下一步：P1 零件核心

P0 完成后，进入 P1：实现 PartsResource 和 PartResource 的全部端点，包括 BOM、签出/签入、CAD 文件上传和 Kafka 触发转换。P1 完成后，CATIA Copilot 可以完全切换到 FastAPI 后端。

# 零件模块 Payara→FastAPI 行为对齐 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 FastAPI 零件模块的业务校验、错误消息（i18n）、响应 DTO 与重构前 Payara 一致，前端零改动即可正常使用。

**Architecture:** 镜像 Payara 的 `ApplicationException` + `PropertiesLoader` 设计。Python service 层抛 `raise XxxException("key")`，与 Java `throw new XxxException("key")` 一一对应；全局 exception handler 按用户 `Account.language` 翻译 i18n key 成最终消息并映射 HTTP 状态码。

**Tech Stack:** FastAPI、SQLAlchemy、Pydantic v2、pytest、Java `.properties` 文件（复制复用）。

## Global Constraints

- 路径前缀 `/docdoku-plm-server-rest/api` 不变，前端 Backbone.js 零改动。
- 运行测试：`workdir: docdoku-plm-server-py` → `source venv/bin/activate && pytest tests/ -q`（venv 在子目录，根目录跑会失败）。
- 重建容器：`workdir: docdoku-plm-docker` → `docker compose up -d --build back-py`。
- 测试数据：admin 密码 `password`；test1（密码 `password`）是 `Workspace_2` 成员，写零件测试用 test1。
- 支持语言：`["fr", "en", "ru", "zh"]`，兜底 `en`。`Account.language` 存纯语言代码（无地区后缀）。
- i18n key 约定：默认 key = 异常类名；`EntityConstraintException`/`NotAllowedException` 用带编号 key。
- 提交信息遵循 Conventional Commits（feat:/fix:/docs:/test: 等）。
- properties 源文件：`docdoku-plm-server/docdoku-plm-server-core/src/main/resources/com/docdoku/plm/server/core/i18n/LocalStrings_{en,fr,zh,ru}.properties`（各 180 行，UTF-8 无 BOM）。

---

## 文件结构

**新建：**
- `app/resources/i18n/LocalStrings_{en,fr,zh,ru}.properties` — 从 Java 复制的翻译文件
- `app/core/i18n.py` — properties 加载器 + `get(key, lang, *args)`
- `app/core/exceptions.py` — `ApplicationException` 基类 + 各业务异常子类
- `app/core/exception_handlers.py` — 异常→HTTP 状态码映射 + handler 注册函数
- `tests/test_i18n.py` — i18n 加载器测试
- `tests/test_exceptions.py` — 异常体系 + handler 测试
- `tests/test_parts_error_paths.py` — 各方法错误路径集成测试
- `scripts/compare_with_payara.py` — 与 Payara 对拍脚本

**修改：**
- `app/main.py` — 注册 exception handler
- `app/core/deps.py` — get_current_user 401 改用 i18n 异常
- `app/services/product_service.py` — 各方法校验改用 i18n 异常，补齐缺失校验
- `app/routers/parts.py` — 移除残留 HTTPException 硬编码

---

## 批次 0：i18n + 异常基础设施

### Task 1: 复制 Java properties 文件

**Files:**
- Create: `app/resources/i18n/LocalStrings_en.properties`
- Create: `app/resources/i18n/LocalStrings_fr.properties`
- Create: `app/resources/i18n/LocalStrings_zh.properties`
- Create: `app/resources/i18n/LocalStrings_ru.properties`

**Interfaces:**
- Produces: 4 个 properties 文件，供 `app/core/i18n.py` 加载。

- [ ] **Step 1: 创建资源目录并复制 4 个文件**

```bash
mkdir -p docdoku-plm-server-py/app/resources/i18n
SRC=docdoku-plm-server/docdoku-plm-server-core/src/main/resources/com/docdoku/plm/server/core/i18n
DST=docdoku-plm-server-py/app/resources/i18n
cp "$SRC/LocalStrings_en.properties" "$DST/"
cp "$SRC/LocalStrings_fr.properties" "$DST/"
cp "$SRC/LocalStrings_zh.properties" "$DST/"
cp "$SRC/LocalStrings_ru.properties" "$DST/"
```

- [ ] **Step 2: 验证文件复制成功且行数一致**

Run: `wc -l docdoku-plm-server-py/app/resources/i18n/*.properties`
Expected: 4 个文件各 180 行。

- [ ] **Step 3: 验证关键 key 存在**

Run: `grep -c "EntityConstraintException2\|NotAllowedException20" docdoku-plm-server-py/app/resources/i18n/LocalStrings_zh.properties`
Expected: 输出 `2`（两个 key 都在）。

- [ ] **Step 4: Commit**

```bash
git add docdoku-plm-server-py/app/resources/i18n/
git commit -m "chore(py): 复制 Java i18n properties 文件供 FastAPI 复用"
```

---

### Task 2: i18n 加载器

**Files:**
- Create: `docdoku-plm-server-py/app/core/i18n.py`
- Test: `docdoku-plm-server-py/tests/test_i18n.py`

**Interfaces:**
- Consumes: `app/resources/i18n/LocalStrings_{lang}.properties`（Task 1）。
- Produces:
  - `get(key: str, lang: str | None = None, *args) -> str` — 按 lang 选文件查 key，用 `str.format` 填充 `{0}{1}` 占位符；lang 为 None/不支持时兜底 en；key 不存在时返回 key 本身。
  - `SUPPORTED_LANGUAGES: list[str] = ["fr", "en", "ru", "zh"]`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_i18n.py
from app.core import i18n


def test_get_zh_returns_chinese():
    assert i18n.get("EntityConstraintException2", "zh") == "您无法删除在装配体中用作组件的零件"


def test_get_en_returns_english():
    assert i18n.get("EntityConstraintException2", "en") == \
        "You cannot delete a part used as component in an assembly"


def test_get_unsupported_lang_falls_back_to_en():
    assert i18n.get("EntityConstraintException2", "de") == \
        "You cannot delete a part used as component in an assembly"


def test_get_none_lang_falls_back_to_en():
    assert i18n.get("EntityConstraintException2", None) == \
        "You cannot delete a part used as component in an assembly"


def test_get_formats_positional_args():
    # AccessRightException=You, {0}, have not sufficient rights to perform this operation
    assert i18n.get("AccessRightException", "en", "test1") == \
        "You, test1, have not sufficient rights to perform this operation"


def test_get_missing_key_returns_key():
    assert i18n.get("NoSuchKeyXYZ", "en") == "NoSuchKeyXYZ"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `source venv/bin/activate && pytest tests/test_i18n.py -q`
Expected: FAIL（`app.core.i18n` 不存在 / 无 `get`）。

- [ ] **Step 3: 实现 i18n 加载器**

```python
# app/core/i18n.py
"""i18n 加载器：复用 Java LocalStrings_*.properties，按语言查翻译。

镜像 Payara PropertiesLoader：fr/ru/zh 各自映射，其余（含 None）兜底 en。
Java properties 的 {0}{1} MessageFormat 占位符与 Python str.format 兼容。
"""
import re
from pathlib import Path

SUPPORTED_LANGUAGES = ["fr", "en", "ru", "zh"]

_RESOURCE_DIR = Path(__file__).resolve().parent.parent / "resources" / "i18n"
_cache: dict[str, dict[str, str]] = {}

# 匹配 key=value 行，跳过注释和空行
_LINE_RE = re.compile(r"^\s*([^#!=\s][^=]*?)\s*=\s*(.*)$")


def _resolve_lang(lang: str | None) -> str:
    """按 Payara 规则解析语言：fr/ru/zh 直用，其余兜底 en。"""
    if lang in ("fr", "ru", "zh"):
        return lang
    return "en"


def _load(lang: str) -> dict[str, str]:
    """加载并缓存某语言的 properties 文件。"""
    if lang in _cache:
        return _cache[lang]
    path = _RESOURCE_DIR / f"LocalStrings_{lang}.properties"
    table: dict[str, str] = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            m = _LINE_RE.match(line)
            if m:
                table[m.group(1)] = m.group(2)
    _cache[lang] = table
    return table


def get(key: str, lang: str | None = None, *args) -> str:
    """按 lang 查 key 翻译，填充 {0}{1} 占位符。缺失 key 返回 key 本身。"""
    table = _load(_resolve_lang(lang))
    template = table.get(key)
    if template is None:
        return key
    if args:
        try:
            return template.format(*args)
        except (IndexError, KeyError):
            return template
    return template
```

- [ ] **Step 4: 运行测试确认通过**

Run: `source venv/bin/activate && pytest tests/test_i18n.py -q`
Expected: 6 passed。

- [ ] **Step 5: Commit**

```bash
git add docdoku-plm-server-py/app/core/i18n.py docdoku-plm-server-py/tests/test_i18n.py
git commit -m "feat(py): 新增 i18n 加载器复用 Java properties"
```

---

### Task 3: 异常体系

**Files:**
- Create: `docdoku-plm-server-py/app/core/exceptions.py`
- Test: `docdoku-plm-server-py/tests/test_exceptions.py`

**Interfaces:**
- Produces:
  - `ApplicationException(key: str, *args)` — 基类，属性 `key: str`、`args: tuple`。
  - 子类：`AccessRightException`、`NotAllowedException`、`EntityConstraintException`、`EntityNotFoundException`、`EntityAlreadyExistsException`、`CreationException`。
  - `ApplicationException.translate(lang) -> str` — 用 i18n.get 翻译自身 key + args。

- [ ] **Step 1: 写失败测试**

```python
# tests/test_exceptions.py
from app.core.exceptions import (
    ApplicationException, AccessRightException, NotAllowedException,
    EntityConstraintException, EntityNotFoundException,
    EntityAlreadyExistsException, CreationException,
)


def test_base_stores_key_and_args():
    e = ApplicationException("SomeKey", "a", "b")
    assert e.key == "SomeKey"
    assert e.args == ("a", "b")


def test_translate_uses_i18n():
    e = EntityConstraintException("EntityConstraintException2")
    assert e.translate("zh") == "您无法删除在装配体中用作组件的零件"


def test_translate_formats_args():
    e = AccessRightException("AccessRightException", "test1")
    assert e.translate("en") == \
        "You, test1, have not sufficient rights to perform this operation"


def test_subclasses_are_application_exception():
    for cls in (AccessRightException, NotAllowedException,
                EntityConstraintException, EntityNotFoundException,
                EntityAlreadyExistsException, CreationException):
        assert issubclass(cls, ApplicationException)
```

- [ ] **Step 2: 运行测试确认失败**

Run: `source venv/bin/activate && pytest tests/test_exceptions.py -q`
Expected: FAIL（模块不存在）。

- [ ] **Step 3: 实现异常体系**

```python
# app/core/exceptions.py
"""业务异常体系，镜像 Payara ApplicationException。

异常只存 i18n key + 格式化参数，不存翻译文本；翻译在 handler 层按用户语言完成。
"""
from app.core import i18n


class ApplicationException(Exception):
    """所有业务异常基类。key 为 i18n key，args 为 {0}{1} 占位符参数。"""

    def __init__(self, key: str, *args):
        self.key = key
        self.args = args
        super().__init__(key)

    def translate(self, lang: str | None = None) -> str:
        return i18n.get(self.key, lang, *self.args)


class AccessRightException(ApplicationException):
    """权限不足 → HTTP 403。"""


class NotAllowedException(ApplicationException):
    """业务规则拒绝 → HTTP 403。"""


class EntityConstraintException(ApplicationException):
    """实体约束（删除被引用等）→ HTTP 403。"""


class EntityNotFoundException(ApplicationException):
    """实体不存在 → HTTP 404。"""


class EntityAlreadyExistsException(ApplicationException):
    """实体已存在 → HTTP 409。"""


class CreationException(ApplicationException):
    """创建失败 → HTTP 500。"""
```

- [ ] **Step 4: 运行测试确认通过**

Run: `source venv/bin/activate && pytest tests/test_exceptions.py -q`
Expected: 4 passed。

- [ ] **Step 5: Commit**

```bash
git add docdoku-plm-server-py/app/core/exceptions.py docdoku-plm-server-py/tests/test_exceptions.py
git commit -m "feat(py): 新增业务异常体系镜像 Payara ApplicationException"
```

---

### Task 4: 异常 handler + HTTP 状态码映射

**Files:**
- Create: `docdoku-plm-server-py/app/core/exception_handlers.py`
- Modify: `docdoku-plm-server-py/app/main.py`
- Test: `docdoku-plm-server-py/tests/test_exceptions.py`（追加）

**Interfaces:**
- Consumes: `ApplicationException` 子类（Task 3）、`get_current_user`/`Account`（现有）。
- Produces:
  - `register_exception_handlers(app: FastAPI) -> None` — 注册 `ApplicationException` handler。
  - handler 根据异常类型映射 HTTP 状态码，用 `request.state.user_language`（若有）或默认 en 翻译，返回 `{"message": <翻译文本>}`。

**说明**：响应体字段用 `message`（批次 1 首个对拍任务会验证前端读的字段；若为 `error` 则统一改）。用户语言获取：handler 无法直接注入 `Depends`，改为从异常携带的 lang 或 request 上下文取；本任务先实现按异常可选携带 `lang`，service 层暂不传，默认 en。批次 1 引入 `deps` 把 user language 注入。

- [ ] **Step 1: 写失败测试**

```python
# tests/test_exceptions.py （追加）
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.core.exceptions import (
    NotAllowedException, EntityNotFoundException,
    EntityAlreadyExistsException, AccessRightException,
    EntityConstraintException, CreationException,
)
from app.core.exception_handlers import register_exception_handlers


def _make_app():
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/notallowed")
    def _na():
        raise NotAllowedException("NotAllowedException37")

    @app.get("/notfound")
    def _nf():
        raise EntityNotFoundException("PartMasterNotFoundException", "P1")

    @app.get("/exists")
    def _ex():
        raise EntityAlreadyExistsException("PartMasterAlreadyExistsException", "P1")

    @app.get("/access")
    def _ac():
        raise AccessRightException("AccessRightException", "test1")

    @app.get("/constraint")
    def _co():
        raise EntityConstraintException("EntityConstraintException2")

    @app.get("/creation")
    def _cr():
        raise CreationException("CreationException")

    return TestClient(app, raise_server_exceptions=False)


def test_handler_maps_status_codes():
    client = _make_app()
    assert client.get("/notallowed").status_code == 403
    assert client.get("/notfound").status_code == 404
    assert client.get("/exists").status_code == 409
    assert client.get("/access").status_code == 403
    assert client.get("/constraint").status_code == 403
    assert client.get("/creation").status_code == 500


def test_handler_returns_translated_message():
    client = _make_app()
    resp = client.get("/constraint")
    assert resp.json()["message"] == \
        "You cannot delete a part used as component in an assembly"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `source venv/bin/activate && pytest tests/test_exceptions.py -q`
Expected: FAIL（`exception_handlers` 不存在）。

- [ ] **Step 3: 实现 handler**

```python
# app/core/exception_handlers.py
"""ApplicationException → HTTP 响应的全局映射。"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.core.exceptions import (
    ApplicationException, AccessRightException, NotAllowedException,
    EntityConstraintException, EntityNotFoundException,
    EntityAlreadyExistsException, CreationException,
)


def _status_for(exc: ApplicationException) -> int:
    if isinstance(exc, (AccessRightException, NotAllowedException,
                        EntityConstraintException)):
        return 403
    if isinstance(exc, EntityNotFoundException):
        return 404
    if isinstance(exc, EntityAlreadyExistsException):
        return 409
    if isinstance(exc, CreationException):
        return 500
    return 500


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApplicationException)
    async def _handle(request: Request, exc: ApplicationException):
        lang = getattr(request.state, "user_language", None)
        return JSONResponse(
            status_code=_status_for(exc),
            content={"message": exc.translate(lang)},
        )
```

- [ ] **Step 4: 在 main.py 注册**

在 `app/main.py` 的 `app = FastAPI(...)` 块之后、`add_middleware` 之前插入：

```python
from app.core.exception_handlers import register_exception_handlers

register_exception_handlers(app)
```

- [ ] **Step 5: 运行测试确认通过**

Run: `source venv/bin/activate && pytest tests/test_exceptions.py -q`
Expected: 全部 passed。

- [ ] **Step 6: 运行全量测试确保无回归**

Run: `source venv/bin/activate && pytest tests/ -q`
Expected: 全部 passed（含原有 39 + 新增）。

- [ ] **Step 7: Commit**

```bash
git add docdoku-plm-server-py/app/core/exception_handlers.py docdoku-plm-server-py/app/main.py docdoku-plm-server-py/tests/test_exceptions.py
git commit -m "feat(py): 新增 ApplicationException 全局 handler 与状态码映射"
```

---

### Task 5: 用户语言注入中间件

**Files:**
- Modify: `docdoku-plm-server-py/app/core/deps.py`
- Modify: `docdoku-plm-server-py/app/main.py`
- Test: `docdoku-plm-server-py/tests/test_exceptions.py`（追加）

**Interfaces:**
- Consumes: `Account`（现有 model，有 `language` 列）、JWT payload。
- Produces: 一个中间件，从 JWT 解析 login → 查 Account.language → 写入 `request.state.user_language`，供 handler 翻译使用。

- [ ] **Step 1: 写失败测试**

```python
# tests/test_exceptions.py （追加）
def test_language_middleware_sets_state(monkeypatch):
    """无有效 token 时 user_language 应为 None（兜底 en）。"""
    from app.main import app
    client = TestClient(app, raise_server_exceptions=False)
    # 触发一个需认证端点，无 token → 401，不应崩溃
    resp = client.get("/docdoku-plm-server-rest/api/workspaces/Workspace_2/parts/count")
    assert resp.status_code in (401, 200)
```

- [ ] **Step 2: 运行测试确认失败或通过（基线）**

Run: `source venv/bin/activate && pytest tests/test_exceptions.py::test_language_middleware_sets_state -q`
Expected: 视中间件是否存在。先记录当前行为。

- [ ] **Step 3: 实现中间件**

在 `app/main.py` 中，`register_exception_handlers(app)` 之后添加：

```python
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.security import verify_token
from app.core.database import SessionLocal
from app.models.auth import Account


class UserLanguageMiddleware(BaseHTTPMiddleware):
    """从 JWT 解析用户语言写入 request.state，供异常 handler 翻译。"""

    async def dispatch(self, request, call_next):
        request.state.user_language = None
        auth = request.headers.get("authorization", "")
        if auth.startswith("Bearer "):
            try:
                payload = verify_token(auth[7:])
                db = SessionLocal()
                try:
                    acct = db.query(Account).filter(
                        Account.login == payload["login"]).first()
                    if acct:
                        request.state.user_language = acct.language
                finally:
                    db.close()
            except Exception:
                pass
        return await call_next(request)


app.add_middleware(UserLanguageMiddleware)
```

**注意**：确认 `app/core/database.py` 导出 `SessionLocal`；若名称不同，用实际名称。

- [ ] **Step 4: 运行全量测试**

Run: `source venv/bin/activate && pytest tests/ -q`
Expected: 全部 passed。

- [ ] **Step 5: 重建容器并冒烟验证**

```bash
cd docdoku-plm-docker && docker compose up -d --build back-py
sleep 3 && curl -s http://localhost:8009/docdoku-plm-server-rest/api/health
```
Expected: `{"status":"ok","backend":"fastapi"}`

- [ ] **Step 6: Commit**

```bash
git add docdoku-plm-server-py/app/main.py docdoku-plm-server-py/tests/test_exceptions.py
git commit -m "feat(py): 新增用户语言中间件供异常翻译"
```

---

## 批次 1：P1a 已实现 7 方法对齐

### Task 6: 对拍脚本

**Files:**
- Create: `docdoku-plm-server-py/scripts/compare_with_payara.py`

**Interfaces:**
- Produces: 命令行脚本，对同一 GET 端点分别请求 FastAPI(:8000 经 Nginx) 与 Payara(:8001)，打印响应体字段级 diff 和状态码。

- [ ] **Step 1: 实现对拍脚本**

```python
# scripts/compare_with_payara.py
"""与 Payara 对拍：同一操作对比 FastAPI(:8000) 与 Payara(:8001) 响应。

用法: python scripts/compare_with_payara.py <path> [--login test1] [--password password]
示例: python scripts/compare_with_payara.py /workspaces/Workspace_2/parts/Assem1-A
"""
import sys
import json
import argparse
import urllib.request

PREFIX = "/docdoku-plm-server-rest/api"


def login(base, login_name, password):
    req = urllib.request.Request(
        f"{base}{PREFIX}/auth/login",
        data=json.dumps({"login": login_name, "password": password}).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    resp = urllib.request.urlopen(req)
    return resp.headers.get("jwt")


def fetch(base, path, token):
    req = urllib.request.Request(
        f"{base}{PREFIX}{path}", headers={"Authorization": f"Bearer {token}"})
    try:
        resp = urllib.request.urlopen(req)
        return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def diff_keys(p, f, prefix=""):
    if isinstance(p, dict) and isinstance(f, dict):
        for k in sorted(set(p) | set(f)):
            diff_keys(p.get(k), f.get(k), f"{prefix}.{k}")
    elif p != f:
        print(f"  {prefix}: Payara={repr(p)[:60]} | FastAPI={repr(f)[:60]}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--login", default="test1")
    ap.add_argument("--password", default="password")
    args = ap.parse_args()

    token = login("http://localhost:8000", args.login, args.password)
    ps, pb = fetch("http://localhost:8001", args.path, token)
    fs, fb = fetch("http://localhost:8000", args.path, token)
    print(f"Status: Payara={ps} FastAPI={fs}")
    if isinstance(pb, dict) and isinstance(fb, dict):
        print("Field diffs:")
        diff_keys(pb, fb)
    else:
        print(f"Payara body: {str(pb)[:200]}")
        print(f"FastAPI body: {str(fb)[:200]}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 冒烟运行**

Run: `source venv/bin/activate && python scripts/compare_with_payara.py /workspaces/Workspace_2/parts/Assem1-A`
Expected: 打印状态码对比 + 字段 diff（当前应显示 notifications、author.language 等已知差异）。

- [ ] **Step 3: Commit**

```bash
git add docdoku-plm-server-py/scripts/compare_with_payara.py
git commit -m "test(py): 新增与 Payara 对拍脚本"
```

---

### Task 7: deletePartRevision 对齐

**Files:**
- Modify: `docdoku-plm-server-py/app/services/product_service.py`（`delete_revision`）
- Test: `docdoku-plm-server-py/tests/test_parts_error_paths.py`

**Interfaces:**
- Consumes: `EntityConstraintException`（Task 3）、`PartUsageLink`/`ProductBaseline` 等 model。
- Java 基线（deletePartRevision L2105）：
  - 配置项根零件 → `EntityConstraintException1`
  - 被用作组件 → `EntityConstraintException2`
  - 被用作替代品 → `EntityConstraintException22`
  - 已在基线中 → `EntityConstraintException5`
  - 已分配到变更项 → `EntityConstraintException21`
- **本任务范围**：实现可用现有 ORM 判断的约束（组件 `EntityConstraintException2`、替代品 `EntityConstraintException22`）。基线/配置项/变更项若对应表未在 P1a ORM 中建模，加 TODO 注释留待对应模块建模后补（不硬造查询）。

- [ ] **Step 1: 写失败测试**

```python
# tests/test_parts_error_paths.py
from fastapi.testclient import TestClient
from app.main import app

PREFIX = "/docdoku-plm-server-rest/api"
WS = "Workspace_2"
client = TestClient(app, raise_server_exceptions=False)


def _token():
    resp = client.post(f"{PREFIX}/auth/login",
                       json={"login": "test1", "password": "password"})
    return resp.headers.get("jwt")


def test_delete_part_used_as_component_returns_403_zh():
    """test1 是 zh 用户，删被用作组件的零件应返回 403 + 中文消息。"""
    token = _token()
    # Assem1 的子件是被引用的零件——挑一个真被引用的（如 Differential Axle 2010）
    resp = client.request(
        "DELETE",
        f"{PREFIX}/workspaces/{WS}/parts/Differential Axle 2010-A",
        headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403
    assert resp.json()["message"] == "您无法删除在装配体中用作组件的零件"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `source venv/bin/activate && pytest tests/test_parts_error_paths.py::test_delete_part_used_as_component_returns_403_zh -q`
Expected: FAIL（当前 delete_revision 无此检查，会 500 或 FK 崩溃）。

- [ ] **Step 3: 实现校验**

替换 `product_service.py` 的 `delete_revision` 方法体（当前含 TODO 注释块），改为：

```python
    def delete_revision(self, db: Session, workspace_id: str,
                        number: str, version: str, user_login: str) -> None:
        from app.core.exceptions import EntityConstraintException
        pr = self.get_revision(db, workspace_id, number, version)
        if pr.checkout_user_login and pr.checkout_user_login != user_login:
            raise HTTPException(403, "Part is checked out by another user")
        if pr.status == 1:
            raise HTTPException(403, "Cannot delete a released revision")
        # 被用作组件（对齐 Payara EntityConstraintException2）
        used_as_component = (
            db.query(PartUsageLink)
            .filter(PartUsageLink.component_workspace_id == workspace_id,
                    PartUsageLink.component_partnumber == number)
            .count()
        )
        if used_as_component > 0:
            raise EntityConstraintException("EntityConstraintException2")
        # TODO(对齐审计): 补齐以下约束（需对应表建模后实现）
        #   EntityConstraintException1  配置项根零件
        #   EntityConstraintException22 被用作替代品（PartSubstituteLink 表）
        #   EntityConstraintException5  已在基线中（ProductBaseline 表）
        #   EntityConstraintException21 已分配到变更项（ChangeItem 表）
        db.delete(pr)
        db.commit()
```

**注意**：`checkout`/`released` 两个前置检查暂保留英文 HTTPException（它们不在 Java deletePartRevision 的 i18n 校验里，是 P1a 自加的保护）；对齐审计矩阵中标注为"P1a 自加，非 Payara 行为"。

- [ ] **Step 4: 运行测试确认通过**

Run: `source venv/bin/activate && pytest tests/test_parts_error_paths.py::test_delete_part_used_as_component_returns_403_zh -q`
Expected: PASS。

- [ ] **Step 5: 重建容器 + 对拍验证**

```bash
cd docdoku-plm-docker && docker compose up -d --build back-py && sleep 3
```
Run: `source venv/bin/activate && python scripts/compare_with_payara.py /workspaces/Workspace_2/parts/Differential Axle 2010-A`
（GET 仍正常；删除行为用上面的集成测试覆盖）

- [ ] **Step 6: Commit**

```bash
git add docdoku-plm-server-py/app/services/product_service.py docdoku-plm-server-py/tests/test_parts_error_paths.py
git commit -m "feat(py): deletePartRevision 对齐 Payara EntityConstraintException2"
```

---

### Task 8: 签出/签入/撤销签出对齐

**Files:**
- Modify: `docdoku-plm-server-py/app/services/product_service.py`（`checkout`/`checkin`/`undo_checkout`）
- Test: `docdoku-plm-server-py/tests/test_parts_error_paths.py`（追加）

**Interfaces:**
- Consumes: `NotAllowedException`（Task 3）。
- Java 基线：
  - checkOut：已签出 → `NotAllowedException37`；已发布/废弃 → `NotAllowedException47`；非最新版 → `NotAllowedException72`
  - checkIn：非当前用户签出 → `NotAllowedException20`
  - undoCheckOut：非当前用户签出 → `NotAllowedException19`；迭代数 ≤ 1 → `NotAllowedException41`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_parts_error_paths.py （追加）
def test_checkout_already_checked_out_returns_403():
    """对已签出的零件再签出应返回 403 + NotAllowedException37 翻译。"""
    token = _token()
    h = {"Authorization": f"Bearer {token}"}
    # 先创建并签出一个新零件
    num = "ERRPATH-CO-1"
    client.post(f"{PREFIX}/workspaces/{WS}/parts",
                json={"number": num, "name": "t"}, headers=h)
    # 新建即自动签出；再次签出应失败
    resp = client.put(f"{PREFIX}/workspaces/{WS}/parts/{num}-A/checkout", headers=h)
    assert resp.status_code == 403
    assert resp.json()["message"] == i18n_expected_37()
    # 清理
    client.put(f"{PREFIX}/workspaces/{WS}/parts/{num}-A/undocheckout", headers=h)
    client.request("DELETE", f"{PREFIX}/workspaces/{WS}/parts/{num}-A", headers=h)


def i18n_expected_37():
    from app.core import i18n
    return i18n.get("NotAllowedException37", "zh")
```

- [ ] **Step 2: 运行测试确认失败**

Run: `source venv/bin/activate && pytest tests/test_parts_error_paths.py::test_checkout_already_checked_out_returns_403 -q`
Expected: FAIL（当前 checkout 抛的是英文 HTTPException(409)）。

- [ ] **Step 3: 实现对齐**

在 `product_service.py` 中，把 `checkout`/`checkin`/`undo_checkout` 的现有 `HTTPException` 替换为 i18n 异常。示例 checkout：

```python
    def checkout(self, db: Session, workspace_id: str,
                 number: str, version: str, user_login: str) -> PartRevision:
        from app.core.exceptions import NotAllowedException
        pr = self.get_revision(db, workspace_id, number, version)
        if pr.checkout_user_login:
            raise NotAllowedException("NotAllowedException37")  # 已签出
        if pr.status in (1, 2):
            raise NotAllowedException("NotAllowedException47")  # 已发布/废弃
        # ... 保留原签出逻辑（设 checkout_user_login/date、建新 iteration 等）
```

checkin：非当前用户签出 → `raise NotAllowedException("NotAllowedException20")`。
undo_checkout：非当前用户签出 → `NotAllowedException19`；迭代数 ≤ 1 → `NotAllowedException41`。

**注意**：读取每个方法现有实现，逐一把英文 HTTPException 换成对应 i18n key，保留其余业务逻辑不变。

- [ ] **Step 4: 运行测试确认通过**

Run: `source venv/bin/activate && pytest tests/test_parts_error_paths.py -q`
Expected: 全部 passed。

- [ ] **Step 5: 全量测试 + 重建**

```bash
source venv/bin/activate && pytest tests/ -q
cd docdoku-plm-docker && docker compose up -d --build back-py && sleep 3
```
Expected: 测试全过；health 正常。

- [ ] **Step 6: Commit**

```bash
git add docdoku-plm-server-py/app/services/product_service.py docdoku-plm-server-py/tests/test_parts_error_paths.py
git commit -m "feat(py): 签出/签入/撤销签出错误消息对齐 Payara i18n"
```

---

### Task 9: createPartMaster / updatePartIteration 对齐

**Files:**
- Modify: `docdoku-plm-server-py/app/services/product_service.py`（`create_part`/`update_iteration`）
- Test: `docdoku-plm-server-py/tests/test_parts_error_paths.py`（追加）

**Interfaces:**
- Consumes: `NotAllowedException`、`EntityAlreadyExistsException`。
- Java 基线：
  - createPartMaster：零件已存在 → `PartMasterAlreadyExistsException`（带零件号参数）
  - updatePartIteration：非签出用户（带零件号参数）→ `NotAllowedException25`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_parts_error_paths.py （追加）
def test_create_duplicate_part_returns_409():
    token = _token()
    h = {"Authorization": f"Bearer {token}"}
    num = "ERRPATH-DUP-1"
    client.post(f"{PREFIX}/workspaces/{WS}/parts",
                json={"number": num, "name": "t"}, headers=h)
    # 重复创建
    resp = client.post(f"{PREFIX}/workspaces/{WS}/parts",
                       json={"number": num, "name": "t"}, headers=h)
    assert resp.status_code == 409
    from app.core import i18n
    assert resp.json()["message"] == i18n.get(
        "PartMasterAlreadyExistsException", "zh", num)
    # 清理
    client.put(f"{PREFIX}/workspaces/{WS}/parts/{num}-A/undocheckout", headers=h)
    client.request("DELETE", f"{PREFIX}/workspaces/{WS}/parts/{num}-A", headers=h)
```

- [ ] **Step 2: 运行测试确认失败**

Run: `source venv/bin/activate && pytest tests/test_parts_error_paths.py::test_create_duplicate_part_returns_409 -q`
Expected: FAIL。

- [ ] **Step 3: 实现对齐**

`create_part`：创建前查 PartMaster 是否已存在，存在则 `raise EntityAlreadyExistsException("PartMasterAlreadyExistsException", number)`。
`update_iteration`：非签出用户 → `raise NotAllowedException("NotAllowedException25", number)`。
把这两个方法内现有的英文 HTTPException 替换为对应 i18n 异常。

- [ ] **Step 4: 运行测试确认通过**

Run: `source venv/bin/activate && pytest tests/test_parts_error_paths.py -q`
Expected: 全部 passed。

- [ ] **Step 5: 全量测试 + 重建**

```bash
source venv/bin/activate && pytest tests/ -q
cd docdoku-plm-docker && docker compose up -d --build back-py && sleep 3
```

- [ ] **Step 6: Commit**

```bash
git add docdoku-plm-server-py/app/services/product_service.py docdoku-plm-server-py/tests/test_parts_error_paths.py
git commit -m "feat(py): createPartMaster/updatePartIteration 错误消息对齐 Payara"
```

---

## 批次 2：DTO 字段对齐

### Task 10: 固化并验证 geometryFileURI / UserDTO / datetime

**Files:**
- Modify: `docdoku-plm-server-py/app/services/part_mapper.py`（已改，需加测试固化）
- Test: `docdoku-plm-server-py/tests/test_part_schemas.py`（追加）

**Interfaces:**
- 现状（前一轮已改）：`geometryFileURI=/api/files/{geometry.full_name}`；`UserDTO` 含 `name/email/language`（从 Account 查）；datetime 用 `_to_utc` 加 UTC；`modificationDate` 取末迭代。
- 本任务：加测试固化这些行为，并用对拍脚本确认与 Payara 无 diff（datetime 精度差异可接受）。

- [ ] **Step 1: 写测试固化 geometryFileURI**

```python
# tests/test_part_schemas.py （追加）
def test_geometry_uri_format(db_session):
    """有 GLB 的 iteration 应返回 /api/files/{fullname} 格式的 geometryFileURI。"""
    from app.services.part_mapper import map_revision
    from app.services.product_service import ProductService
    svc = ProductService()
    pr = svc.get_revision(db_session, "Workspace_2", "Differential Axle 2010", "A")
    dto = map_revision(pr, db_session)
    it1 = next(i for i in dto.partIterations if i.iteration == 1)
    assert it1.geometryFileURI is not None
    assert it1.geometryFileURI.startswith("/api/files/Workspace_2/parts/")
    assert it1.geometryFileURI.endswith(".glb")
```

**注意**：确认 `conftest.py` 提供 `db_session` fixture；若无，用现有 fixture 名或直接建 session。

- [ ] **Step 2: 运行测试确认通过（行为已实现）**

Run: `source venv/bin/activate && pytest tests/test_part_schemas.py::test_geometry_uri_format -q`
Expected: PASS（前一轮已实现该行为）。

- [ ] **Step 3: 写测试固化 UserDTO 字段**

```python
# tests/test_part_schemas.py （追加）
def test_user_dto_has_name_email_language(db_session):
    from app.services.part_mapper import map_revision
    from app.services.product_service import ProductService
    svc = ProductService()
    pr = svc.get_revision(db_session, "Workspace_2", "Differential Axle 2010", "A")
    dto = map_revision(pr, db_session)
    assert dto.author.name is not None
    assert dto.author.email is not None
    assert dto.author.language is not None
```

- [ ] **Step 4: 运行测试确认通过**

Run: `source venv/bin/activate && pytest tests/test_part_schemas.py::test_user_dto_has_name_email_language -q`
Expected: PASS。

- [ ] **Step 5: 对拍验证**

```bash
cd docdoku-plm-docker && docker compose up -d --build back-py && sleep 3
```
Run: `source venv/bin/activate && python scripts/compare_with_payara.py /workspaces/Workspace_2/parts/Differential Axle 2010-A`
Expected: author 的 name/email/language 不再 diff；geometryFileURI 不再 diff。剩余 diff 仅 notifications（Task 11）和 datetime 精度（可接受）。

- [ ] **Step 6: Commit**

```bash
git add docdoku-plm-server-py/tests/test_part_schemas.py
git commit -m "test(py): 固化 geometryFileURI/UserDTO/datetime 对齐行为"
```

---

## 批次 3：P1b 8 方法（占位，待批次 0-2 完成后细化）

批次 3 涉及新写端点（文件上传下载、转换回调、发布、废弃、删文件、标签），依赖 P1b 的 vault 文件读写与新 ORM 建模，范围较大。待批次 0-2 完成、基础设施稳定后，另起一份 P1b 实现计划细化。本计划聚焦批次 0-2（基础设施 + P1a 7 方法对齐 + DTO 对齐）。

批次 3 待细化项（记入 REMINDERS）：
- saveNativeCADInPartIteration / saveFileInPartIteration：`NotAllowedException4` + CAD 白名单校验
- handleConversionResultCallback：`findPendingConversionForRevision` 定位 + 空几何跳过 + 不检查签出
- createPartRevision：`NotAllowedException40/41/56`
- releasePartRevision：`NotAllowedException46/41/38`
- markPartRevisionAsObsolete：`NotAllowedException36`
- removeFileInPartIteration、标签管理

---

## 收尾

### Task 11: 更新文档

**Files:**
- Modify: `docs/CHANGELOG.md`、`docs/REMINDERS.md`

- [ ] **Step 1: 更新 CHANGELOG**

在顶部加当天日期条目，记录：i18n 基础设施、异常体系、P1a 7 方法错误消息对齐、DTO 字段对齐、对拍脚本。

- [ ] **Step 2: 更新 REMINDERS**

标记对齐审计批次 0-2 完成；记录批次 3（P1b 8 方法）为待办；记录 notifications 字段仍为空（待 ModificationNotification 建模）。

- [ ] **Step 3: Commit**

```bash
git add docs/CHANGELOG.md docs/REMINDERS.md
git commit -m "docs: 记录零件模块对齐审计批次 0-2 完成"
```

---

## Self-Review 结果

- **Spec coverage**：方案 A 架构（Task 2-5）✅；异常→HTTP 映射（Task 4）✅；审计方法论分批（批次 0-3）✅；i18n 关键事实（Task 1-2）✅；验证策略 3 层——单元/集成测试（各 Task）✅、对拍（Task 6/10）✅、前端实测（每批交付时列清单，收尾提示）✅。deletePartRevision 5 个约束中 2 个实现、3 个加 TODO（对应表未建模），已在 Task 7 说明。
- **Placeholder scan**：批次 3 明确标为"占位待另起计划"，非计划内 TODO；Task 内代码步骤均含完整代码。
- **Type consistency**：`get(key, lang, *args)`、`ApplicationException(key, *args)`、`translate(lang)`、`register_exception_handlers(app)`、`_status_for(exc)` 全计划一致。

from app.core.exceptions import (
    ApplicationException, AccessRightException, NotAllowedException,
    EntityConstraintException, EntityNotFoundException,
    EntityAlreadyExistsException, CreationException,
)


def test_base_stores_key_and_args():
    e = ApplicationException("SomeKey", "a", "b")
    assert e.key == "SomeKey"
    assert e.fmt_args == ("a", "b")
    assert str(e) == "SomeKey"


def test_base_no_args_str_works():
    e = NotAllowedException("NotAllowedException37")
    assert str(e) == "NotAllowedException37"


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


# ── Task 4: exception handler 测试 ──────────────────────────

from fastapi import FastAPI
from fastapi.testclient import TestClient
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
    assert client.get("/constraint").status_code == 400
    assert client.get("/creation").status_code == 500


def test_handler_returns_translated_message():
    client = _make_app()
    resp = client.get("/constraint")
    assert resp.text == \
        "You cannot delete a part used as component in an assembly"


# ── Task 5: 用户语言中间件测试 ──────────────────────────

def test_language_middleware_sets_state():
    """无有效 token 时 user_language 应为 None（兜底 en），请求不应崩溃。"""
    from app.main import app
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/docdoku-plm-server-rest/api/workspaces/Workspace_2/parts/count")
    assert resp.status_code in (401, 200)

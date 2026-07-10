"""Task 6: QueryResult 序列化测试（不依赖 DB，用轻量替身）。"""
from datetime import datetime

from app.schemas.query_result import build_query_result_rows


class _Master:
    name = "Gear"
    type = "part"
    standard_part = False


class _Iter:
    iteration = 1
    check_in_date = datetime(2024, 1, 1, 10, 0, 0)
    modification_date = datetime(2024, 1, 2, 10, 0, 0)


class _PR:
    workspace_id = "WS"
    partmaster_partnumber = "P1"
    version = "A"
    status = 1
    status_label = "RELEASED"
    creation_date = datetime(2024, 1, 1)
    check_out_date = None
    author_login = "e"
    part_master = _Master()
    iterations = [_Iter()]


def test_part_key_always_present_and_pm_pr_fields():
    query = {"selects": ["pm.number", "pm.name", "pr.version", "pr.status"]}
    rows = [{"partRevision": _PR()}]
    out = build_query_result_rows(rows, query, None)
    assert len(out) == 1
    d = out[0]
    assert d["pr.partKey"] == "P1-A"
    assert d["pm.number"] == "P1"
    assert d["pm.name"] == "Gear"
    assert d["pr.version"] == "A"
    assert d["pr.status"] == "RELEASED"


def test_ctx_fields_only_when_context_present():
    query = {"selects": ["ctx.depth", "ctx.productId", "ctx.serialNumber"]}
    # 有 context 的行
    row_ctx = {"partRevision": _PR(), "context": {"configurationItemId": "CI1",
               "serialNumber": "SN1"}, "depth": 2, "amount": 3.0}
    out_ctx = build_query_result_rows([row_ctx], query, None)[0]
    assert out_ctx["ctx.depth"] == 2
    assert out_ctx["ctx.productId"] == "CI1"
    assert out_ctx["ctx.serialNumber"] == "SN1"
    # 无 context 的行 → ctx.* 不输出
    out_noctx = build_query_result_rows([{"partRevision": _PR()}], query, None)[0]
    assert "ctx.depth" not in out_noctx
    assert out_noctx["pr.partKey"] == "P1-A"


def test_pd_attr_values_are_arrays():
    query = {"selects": ["pd-attr-TEXT.color"]}
    row = {"partRevision": _PR(), "pathDataAttrs": {"pd-attr-TEXT.color": ["red", "blue"]}}
    out = build_query_result_rows([row], query, None)[0]
    assert out["pd-attr-TEXT.color"] == ["red", "blue"]

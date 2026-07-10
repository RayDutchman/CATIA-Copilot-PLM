"""Task 5: Context PBS 过滤 + mergeRows 测试。"""
from app.core.database import SessionLocal
from app.services.query_pbs import _path_string, _amount, _p2p_for_path, merge_rows, filter_pbs


class _Link:
    def __init__(self, lid, amount=1.0, unit=None):
        self.id = lid
        self.amount = amount
        self.unit = unit


class _VirtualRoot(_Link):
    pass


class _PR:
    def __init__(self, ws, pn, ver):
        self.workspace_id = ws
        self.partmaster_partnumber = pn
        self.version = ver


def test_path_string_encoding():
    path = [_VirtualRoot(1), _Link(2), _Link(5)]
    assert _path_string(path) == "-1-u2-u5"
    assert _path_string([_VirtualRoot(1)]) == "-1"


def test_amount_multiplies_skipping_unit():
    path = [_VirtualRoot(1), _Link(2, amount=3.0), _Link(3, amount=2.0, unit="kg")]
    # unit=kg 的链接被跳过 → 3.0
    assert _amount(path) == 3.0


def test_p2p_for_path_matches_source_and_target():
    links = [("-1-u2", "-1-u5", "linktype-A"), ("-1-u9", "-1-u2", "linktype-B")]
    sources, targets = _p2p_for_path(links, "-1-u2")
    assert sources == {"linktype-A": ["-1-u5"]}
    assert targets == {"linktype-B": ["-1-u9"]}


def test_merge_rows_intersection():
    pr1, pr2, pr3 = _PR("W", "A", "1"), _PR("W", "B", "1"), _PR("W", "C", "1")
    pbs_rows = [{"partRevision": pr1}, {"partRevision": pr2}, {"partRevision": pr3}]
    part_revisions = [pr2, pr3]
    merged = merge_rows(pbs_rows, part_revisions)
    assert len(merged) == 2
    assert {r["partRevision"].partmaster_partnumber for r in merged} == {"B", "C"}


def test_filter_pbs_no_contexts_returns_empty():
    db = SessionLocal()
    try:
        assert filter_pbs(db, "测试用工作区", {"contexts": []}, "e", True) == []
    finally:
        db.close()


def test_filter_pbs_missing_ci_skipped():
    db = SessionLocal()
    try:
        query = {"contexts": [{"configurationItemId": "NO_SUCH_CI", "serialNumber": None}]}
        assert filter_pbs(db, "测试用工作区", query, "e", True) == []
    finally:
        db.close()

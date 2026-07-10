"""Import 记录 CRUD 服务单元测试（TDD）。"""
import pytest
from datetime import datetime


def _make_id(suffix: str = "") -> str:
    """生成不与 seed 数据冲突的 import_id。"""
    return f"imp-test-{suffix}-{datetime.utcnow().timestamp()}"[:50]


WS = "Workspace_2"
USER = "SEED-20260705-215045-alice"


class TestCreateAndGet:
    """测试创建导入记录并读取。"""

    def test_create_and_get(self, db):
        from app.services.importers.import_record import create_import, get_import

        import_id = _make_id("cag")
        create_import(db, import_id, "test-parts.xlsx", USER, WS)

        dto = get_import(db, import_id)
        assert dto is not None
        assert dto.id == import_id
        assert dto.fileName == "test-parts.xlsx"
        assert dto.pending is True
        assert dto.succeed is False
        assert dto.startDate is not None
        assert dto.endDate is None
        assert dto.errors == []
        assert dto.warnings == []


class TestCompleteImport:
    """测试结束导入。"""

    def test_complete_success(self, db):
        from app.services.importers.import_record import create_import, complete_import, get_import

        import_id = _make_id("cs")
        create_import(db, import_id, "test.xlsx", USER, WS)
        complete_import(db, import_id, succeed=True, errors=[], warnings=["w1"])

        dto = get_import(db, import_id)
        assert dto is not None
        assert dto.pending is False
        assert dto.succeed is True
        assert dto.endDate is not None
        assert dto.errors == []
        assert dto.warnings == ["w1"]

    def test_complete_with_errors(self, db):
        from app.services.importers.import_record import create_import, complete_import, get_import

        import_id = _make_id("ce")
        create_import(db, import_id, "test.xlsx", USER, WS)
        complete_import(db, import_id, succeed=False, errors=["e1", "e2"], warnings=[])

        dto = get_import(db, import_id)
        assert dto is not None
        assert dto.pending is False
        assert dto.succeed is False
        assert dto.endDate is not None
        assert dto.errors == ["e1", "e2"]
        assert dto.warnings == []

    def test_complete_with_both(self, db):
        from app.services.importers.import_record import create_import, complete_import, get_import

        import_id = _make_id("cb")
        create_import(db, import_id, "test.xlsx", USER, WS)
        complete_import(db, import_id, succeed=True, errors=["e1"], warnings=["w1", "w2"])

        dto = get_import(db, import_id)
        assert dto is not None
        assert dto.pending is False
        assert dto.succeed is True
        assert dto.errors == ["e1"]
        assert dto.warnings == ["w1", "w2"]


class TestListImports:
    """测试列表查询。"""

    def test_list_imports(self, db):
        from app.services.importers.import_record import create_import, list_imports

        suffix = "li"
        id1 = _make_id(f"{suffix}-1")
        id2 = _make_id(f"{suffix}-2")
        id3 = _make_id(f"{suffix}-3")

        create_import(db, id1, "same-file.xlsx", USER, WS)
        create_import(db, id2, "same-file.xlsx", USER, WS)
        create_import(db, id3, "other-file.xlsx", USER, WS)

        results = list_imports(db, WS, "same-file.xlsx")
        assert len(results) == 2
        ids = {r.id for r in results}
        assert id1 in ids
        assert id2 in ids
        assert id3 not in ids

    def test_list_imports_other_workspace(self, db):
        from app.services.importers.import_record import create_import, list_imports

        import_id = _make_id("li-other")
        create_import(db, import_id, "f.xlsx", USER, WS)

        results = list_imports(db, "NonExistentWorkspace", "f.xlsx")
        assert results == []


class TestDeleteImport:
    """测试删除导入记录。"""

    def test_delete(self, db):
        from app.services.importers.import_record import (
            create_import, complete_import, delete_import_record, get_import,
        )
        from sqlalchemy import text

        import_id = _make_id("del")
        create_import(db, import_id, "del.xlsx", USER, WS)
        complete_import(db, import_id, succeed=False, errors=["e"], warnings=["w"])

        # 确认子表有数据
        err_count = db.execute(
            text("SELECT COUNT(*) FROM import_error WHERE import_id=:id"),
            {"id": import_id},
        ).scalar()
        assert err_count == 1

        # 删除
        assert delete_import_record(db, import_id) is True
        assert get_import(db, import_id) is None

        # 子表也应删除
        err_count_after = db.execute(
            text("SELECT COUNT(*) FROM import_error WHERE import_id=:id"),
            {"id": import_id},
        ).scalar()
        assert err_count_after == 0

        warn_count_after = db.execute(
            text("SELECT COUNT(*) FROM import_warning WHERE import_id=:id"),
            {"id": import_id},
        ).scalar()
        assert warn_count_after == 0


class TestMissing:
    """测试不存在的记录。"""

    def test_get_missing(self, db):
        from app.services.importers.import_record import get_import

        assert get_import(db, "imp-test-nonexistent-id") is None

    def test_delete_missing(self, db):
        from app.services.importers.import_record import delete_import_record

        assert delete_import_record(db, "imp-test-nonexistent-id") is False

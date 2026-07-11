"""ImporterService 编排层单测（TDD）。

测试覆盖：
- 解析错误不写库
- 零件不存在返回错误
- dry_run 不产生副作用
- _write_iteration_attributes 写入带 dtype
- BOM/PathData stub 返回 NotSupported
- error-path 验证无 DB 写入

注意：避免真实 checkout/checkin（会 commit 污染 DB）。
"""
import pytest
from pathlib import Path
from sqlalchemy import text

WS = "GD50"
USER = "SEED-20260705-215045-alice"


# ═══════════════════════════════════════════════════════════════════════════════
# 导入 stub — 测试在实现前先失败（TDD red）
# ═══════════════════════════════════════════════════════════════════════════════

from app.services.importer import ImporterService

_importer = ImporterService()


class TestImportIntoParts:
    """import_into_parts 主流程测试。"""

    def test_parse_error_no_write(self, db, tmp_path):
        """解析阶段报错 → succeed False，不写库。"""
        from tests.fixtures.make_import_xlsx import make_invalid_date_parts_xlsx

        xlsx_bytes = make_invalid_date_parts_xlsx()
        file_path = str(tmp_path / "invalid_date.xlsx")
        Path(file_path).write_bytes(xlsx_bytes)

        before_count = db.execute(text(
            "SELECT count(*) FROM instanceattribute"
        )).scalar()

        result = _importer.import_into_parts(
            db, WS, file_path, "invalid_date.xlsx",
            user_login=USER, is_admin=True,
        )

        assert result["succeed"] is False
        assert len(result["errors"]) > 0

        # 确认无 DB 写入
        after_count = db.execute(text(
            "SELECT count(*) FROM instanceattribute"
        )).scalar()
        assert after_count == before_count

    def test_part_not_found(self, db, tmp_path):
        """Excel 中零件号在 DB 中不存在 → succeed False，含 PartMasterNotFound，不写库。"""
        from tests.fixtures.make_import_xlsx import make_valid_parts_xlsx

        xlsx_bytes = make_valid_parts_xlsx()
        file_path = str(tmp_path / "parts.xlsx")
        Path(file_path).write_bytes(xlsx_bytes)

        before_count = db.execute(text(
            "SELECT count(*) FROM instanceattribute"
        )).scalar()

        result = _importer.import_into_parts(
            db, WS, file_path, "parts.xlsx",
            user_login=USER, is_admin=True,
            auto_checkout=True, auto_checkin=True,
        )

        assert result["succeed"] is False
        assert len(result["errors"]) > 0
        assert any("PartMasterNotFound" in e for e in result["errors"])

        # 确认无 DB 写入
        after_count = db.execute(text(
            "SELECT count(*) FROM instanceattribute"
        )).scalar()
        assert after_count == before_count


class TestDryRun:
    """dry_run_import_into_parts 测试。"""

    def test_dry_run_no_write(self, db, tmp_path):
        """dry_run 不产生副作用，partRevsToCheckout 空。"""
        from tests.fixtures.make_import_xlsx import make_valid_parts_xlsx

        xlsx_bytes = make_valid_parts_xlsx()
        file_path = str(tmp_path / "dry.xlsx")
        Path(file_path).write_bytes(xlsx_bytes)

        result = _importer.dry_run_import_into_parts(
            db, WS, file_path, "dry.xlsx",
            user_login=USER, is_admin=True,
            auto_checkout=True, auto_checkin=True,
        )

        assert "partRevsToCheckout" in result
        assert "partsToCreate" in result
        assert result["partRevsToCheckout"] == []
        assert result["partsToCreate"] == []


class TestWriteIterationAttributes:
    """_write_iteration_attributes 直接测试（无 checkout/commit，fixture 回滚）。"""

    def test_sets_dtype_and_values(self, db):
        """写入后 instanceattribute 行带有正确的 dtype 和值。"""
        from app.services.importer import _write_iteration_attributes
        from app.services.importers.attributes_importer_utils import (
            MergedAttribute, TOKEN_TO_DTYPE, TOKEN_TO_VALUECOL,
        )

        # 动态查找 seed 中 GD50 的一个零件迭代（避免硬编码）
        row = db.execute(text(
            "SELECT partmaster_partnumber, partrevision_version, iteration "
            "FROM partiteration WHERE workspace_id=:ws LIMIT 1"
        ), {"ws": WS}).fetchone()

        if row is None:
            pytest.skip("GD50 中无 seed 迭代，跳过写入测试")

        pn = row.partmaster_partnumber
        ver = row.partrevision_version
        it = row.iteration

        merged = [
            MergedAttribute(name="TestText", type="TEXT", value="hello"),
            MergedAttribute(name="TestNum", type="NUMBER", value=3.5),
        ]

        _write_iteration_attributes(db, WS, pn, ver, it, merged)

        # 查写入结果
        rows = db.execute(text(
            "SELECT ia.dtype, ia.textvalue, ia.numbervalue "
            "FROM instanceattribute ia "
            "JOIN partiteration_attribute pia ON ia.id = pia.instanceattribute_id "
            "WHERE pia.workspace_id=:ws AND pia.partmaster_partnumber=:pn "
            "  AND pia.partrevision_version=:ver AND pia.iteration=:it "
            "ORDER BY pia.attribute_order"
        ), {"ws": WS, "pn": pn, "ver": ver, "it": it}).fetchall()

        assert len(rows) == 2

        # 第一条：TEXT
        assert rows[0].dtype == "InstanceTextAttribute"
        assert rows[0].textvalue == "hello"

        # 第二条：NUMBER
        assert rows[1].dtype == "InstanceNumberAttribute"
        assert rows[1].numbervalue == 3.5


class TestBomStub:
    """BOM 导入 stub 测试。"""

    def test_import_bom_stub(self, db, tmp_path):
        """import_bom 返回 succeed False + NotSupported。"""
        file_path = str(tmp_path / "bom.xlsx")
        Path(file_path).write_bytes(b"dummy")

        result = _importer.import_bom(
            db, WS, file_path, "bom.xlsx",
            user_login=USER,
        )

        assert result["succeed"] is False
        assert any("NotSupported" in e for e in result["errors"])

    def test_dry_run_import_bom_stub(self, db, tmp_path):
        """dry_run_import_bom 返回 succeed False + NotSupported。"""
        file_path = str(tmp_path / "bom.xlsx")
        Path(file_path).write_bytes(b"dummy")

        result = _importer.dry_run_import_bom(
            db, WS, file_path, "bom.xlsx",
            user_login=USER,
        )

        assert result["succeed"] is False
        assert "errors" in result
        assert any("NotSupported" in e for e in result["errors"])


class TestPathDataStub:
    """PathData 导入 stub 测试。"""

    def test_import_path_data_stub(self, db, tmp_path):
        """import_into_path_data 返回 succeed False + NotSupported。"""
        file_path = str(tmp_path / "path.xlsx")
        Path(file_path).write_bytes(b"dummy")

        result = _importer.import_into_path_data(
            db, WS, file_path, "path.xlsx",
            user_login=USER,
        )

        assert result["succeed"] is False
        assert any("NotSupported" in e for e in result["errors"])

#
# 注意：test_revision_note_written 被跳过——
# revision_note 写入需要真实 checkout（checkout 会新建迭代并 commit 到 DB，
# 污染后续测试），fixture 级回滚不足以隔离，故不在此处测试。
# revision_note 更新逻辑已在 importer.py:203-208 实现。
#
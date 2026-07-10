"""属性合并工具单元测试（对齐 AttributesImporterUtils.java merge 语义）。"""

import datetime
import pytest
from sqlalchemy import text

from app.services.importers.attributes_importer_utils import (
    TOKEN_TO_DTYPE,
    TOKEN_TO_VALUECOL,
    DTYPE_TO_TOKEN,
    MergedAttribute,
    convert_value,
    resolve_lov_index,
    merge_attributes,
    would_change,
)
from app.services.importers.excel_parser import ParsedAttribute


class TestConvertValue:
    """convert_value 类型转换测试。"""

    def test_text(self):
        assert convert_value("TEXT", "hello") == "hello"
        assert convert_value("TEXT", "") is None
        assert convert_value("TEXT", None) is None

    def test_long_text(self):
        assert convert_value("LONG_TEXT", "long content") == "long content"
        assert convert_value("LONG_TEXT", "") is None
        assert convert_value("LONG_TEXT", None) is None

    def test_url(self):
        assert convert_value("URL", "https://example.com") == "https://example.com"
        assert convert_value("URL", "") is None
        assert convert_value("URL", None) is None

    def test_number(self):
        assert convert_value("NUMBER", "3.14") == pytest.approx(3.14)
        assert convert_value("NUMBER", "42") == pytest.approx(42.0)
        assert convert_value("NUMBER", "") is None
        assert convert_value("NUMBER", None) is None

    def test_date(self):
        result = convert_value("DATE", "2025-01-15 00:00:00")
        assert result == datetime.datetime(2025, 1, 15, 0, 0, 0)
        assert convert_value("DATE", "") is None
        assert convert_value("DATE", None) is None

    def test_boolean(self):
        assert convert_value("BOOLEAN", "true") is True
        assert convert_value("BOOLEAN", "false") is False
        assert convert_value("BOOLEAN", "") is None
        assert convert_value("BOOLEAN", None) is None

    def test_invalid_number_raises(self):
        with pytest.raises(ValueError):
            convert_value("NUMBER", "not-a-number")

    def test_invalid_date_raises(self):
        with pytest.raises(ValueError):
            convert_value("DATE", "not-a-date")

    def test_lov_returns_none(self):
        assert convert_value("LOV", "Red") is None
        assert convert_value("LOV", None) is None


class TestMergeCreateNew:
    """合并 — 新建模式。"""

    def test_all_new_empty_existing(self):
        parsed = [
            ParsedAttribute(name="Mat", type="TEXT", value="Steel"),
            ParsedAttribute(name="Weight", type="NUMBER", value="2.5"),
        ]
        errors: list[str] = []
        result = merge_attributes(None, "WS1", [], parsed, "P001", errors)
        assert errors == []
        assert len(result) == 2
        assert result[0].name == "Mat"
        assert result[0].type == "TEXT"
        assert result[0].value == "Steel"
        assert result[1].name == "Weight"
        assert result[1].type == "NUMBER"
        assert result[1].value == pytest.approx(2.5)

    def test_new_appended_to_existing(self):
        existing = [
            MergedAttribute(name="A", type="TEXT", value="a"),
        ]
        parsed = [
            ParsedAttribute(name="B", type="TEXT", value="b"),
        ]
        errors: list[str] = []
        result = merge_attributes(None, "WS1", existing, parsed, "P002", errors)
        assert errors == []
        assert len(result) == 2
        assert result[0].name == "A"
        assert result[1].name == "B"

    def test_new_conversion_error(self):
        """新建模式值转换失败 → 记 error，跳过该属性。"""
        parsed = [
            ParsedAttribute(name="Weight", type="NUMBER", value="not-a-number"),
        ]
        errors: list[str] = []
        result = merge_attributes(None, "WS1", [], parsed, "P003", errors)
        assert len(errors) == 1
        assert "P003" in errors[0]
        assert "Weight" in errors[0]
        assert len(result) == 0


class TestMergeUpdate:
    """合并 — 更新模式。"""

    def test_update_value(self):
        existing = [
            MergedAttribute(name="Mat", type="TEXT", value="OldValue"),
        ]
        parsed = [
            ParsedAttribute(name="Mat", type="TEXT", value="NewValue", attribute_id=1),
        ]
        errors: list[str] = []
        result = merge_attributes(None, "WS1", existing, parsed, "P004", errors)
        assert errors == []
        assert len(result) == 1
        assert result[0].value == "NewValue"

    def test_update_not_found(self):
        existing = [
            MergedAttribute(name="A", type="TEXT", value="a"),
        ]
        parsed = [
            ParsedAttribute(name="B", type="TEXT", value="b", attribute_id=99),
        ]
        errors: list[str] = []
        result = merge_attributes(None, "WS1", existing, parsed, "P005", errors)
        assert len(result) == 1
        assert len(errors) == 1
        assert "AttributeNotFound" in errors[0]
        assert "P005" in errors[0]
        assert "B" in errors[0]

    def test_duplicate_create(self):
        """新建模式但 existing 已有同 name+type → errors 含 DuplicateEntry。"""
        existing = [
            MergedAttribute(name="Mat", type="TEXT", value="Steel"),
        ]
        parsed = [
            ParsedAttribute(name="Mat", type="TEXT", value="SteelAgain"),
        ]
        errors: list[str] = []
        result = merge_attributes(None, "WS1", existing, parsed, "P006", errors)
        assert len(result) == 1
        assert len(errors) == 1
        assert "DuplicateEntry" in errors[0]

    def test_preserves_unmentioned(self):
        existing = [
            MergedAttribute(name="A", type="TEXT", value="a"),
            MergedAttribute(name="B", type="TEXT", value="b"),
        ]
        parsed = [
            ParsedAttribute(name="A", type="TEXT", value="a_new", attribute_id=1),
        ]
        errors: list[str] = []
        result = merge_attributes(None, "WS1", existing, parsed, "P007", errors)
        assert errors == []
        assert len(result) == 2
        a_match = [x for x in result if x.name == "A"]
        assert len(a_match) == 1
        assert a_match[0].value == "a_new"
        b_match = [x for x in result if x.name == "B"]
        assert len(b_match) == 1
        assert b_match[0].value == "b"

    def test_update_conversion_error(self):
        """更新模式值转换失败 → 记 error，保留原值。"""
        existing = [
            MergedAttribute(name="Weight", type="NUMBER", value=1.0),
        ]
        parsed = [
            ParsedAttribute(name="Weight", type="NUMBER", value="bad", attribute_id=1),
        ]
        errors: list[str] = []
        result = merge_attributes(None, "WS1", existing, parsed, "P008", errors)
        assert len(errors) == 1
        assert len(result) == 1
        assert result[0].value == 1.0  # 保留原值，未更新


class TestWouldChange:
    """would_change dry-run 测试。"""

    def test_true_new(self):
        """新建模式且 existing 无匹配 → True。"""
        existing: list[MergedAttribute] = []
        parsed = [ParsedAttribute(name="A", type="TEXT", value="a")]
        assert would_change(None, "WS1", existing, parsed) is True

    def test_true_update(self):
        """更新模式且在 existing 找到匹配 → True。"""
        existing = [MergedAttribute(name="A", type="TEXT", value="old")]
        parsed = [ParsedAttribute(name="A", type="TEXT", value="new", attribute_id=1)]
        assert would_change(None, "WS1", existing, parsed) is True

    def test_false_empty_parsed(self):
        existing = [MergedAttribute(name="A", type="TEXT", value="a")]
        assert would_change(None, "WS1", existing, []) is False

    def test_false_update_not_found(self):
        """更新模式但找不到匹配 → False。"""
        existing = [MergedAttribute(name="A", type="TEXT", value="a")]
        parsed = [ParsedAttribute(name="B", type="TEXT", value="b", attribute_id=99)]
        assert would_change(None, "WS1", existing, parsed) is False


class TestResolveLovIndex:
    """resolve_lov_index 测试（需 db fixture）。"""

    WS = "Workspace_2"  # 使用已有的 workspace，满足 lov FK
    LOV_NAME = "Colors_T2"

    @pytest.fixture(autouse=True)
    def seed_lov(self, db):
        db.execute(text(
            "INSERT INTO lov (name, workspace_id) VALUES (:n, :w) "
            "ON CONFLICT (name, workspace_id) DO NOTHING"
        ), {"n": self.LOV_NAME, "w": self.WS})
        for order, name in enumerate(["Red", "Green", "Blue"]):
            db.execute(text(
                "INSERT INTO lov_namevalue "
                "(name, value, lov_name, lov_workspace_id, namevalue_order) "
                "VALUES (:n, :v, :ln, :lw, :o)"
            ), {"n": name, "v": name, "ln": self.LOV_NAME,
                "lw": self.WS, "o": order})
        db.flush()

    def test_found(self, db):
        assert resolve_lov_index(db, self.WS, self.LOV_NAME, "Green") == 1

    def test_not_found(self, db):
        assert resolve_lov_index(db, self.WS, self.LOV_NAME, "Purple") is None

    def test_first(self, db):
        assert resolve_lov_index(db, self.WS, self.LOV_NAME, "Red") == 0


class TestMergeLov:
    """LOV 合并测试（需 db fixture）。"""

    WS = "Workspace_2"
    LOV_NAME = "Colors_T2"

    @pytest.fixture(autouse=True)
    def seed_lov(self, db):
        db.execute(text(
            "INSERT INTO lov (name, workspace_id) VALUES (:n, :w) "
            "ON CONFLICT (name, workspace_id) DO NOTHING"
        ), {"n": self.LOV_NAME, "w": self.WS})
        for order, name in enumerate(["Red", "Green", "Blue"]):
            db.execute(text(
                "INSERT INTO lov_namevalue "
                "(name, value, lov_name, lov_workspace_id, namevalue_order) "
                "VALUES (:n, :v, :ln, :lw, :o)"
            ), {"n": name, "v": name, "ln": self.LOV_NAME,
                "lw": self.WS, "o": order})
        db.flush()

    def test_resolved(self, db):
        parsed = [
            ParsedAttribute(name="Color", type="LOV", value="Blue",
                           lov_name=self.LOV_NAME),
        ]
        errors: list[str] = []
        result = merge_attributes(db, self.WS, [], parsed, "P009", errors)
        assert errors == []
        assert len(result) == 1
        assert result[0].name == "Color"
        assert result[0].type == "LOV"
        assert result[0].value == 2

    def test_not_found(self, db):
        parsed = [
            ParsedAttribute(name="Color", type="LOV", value="Nope",
                           lov_name=self.LOV_NAME),
        ]
        errors: list[str] = []
        result = merge_attributes(db, self.WS, [], parsed, "P010", errors)
        assert len(errors) == 1
        assert "LovValueNotFound" in errors[0]
        assert "P010" in errors[0]
        assert not errors[0].startswith("ConversionError")
        assert len(result) == 0

    def test_lov_missing_name(self, db):
        parsed = [
            ParsedAttribute(name="Color", type="LOV", value="Red",
                           lov_name=None),
        ]
        errors: list[str] = []
        result = merge_attributes(db, self.WS, [], parsed, "P011", errors)
        assert len(errors) == 1
        assert "LovValueNotFound" in errors[0]
        assert "P011" in errors[0]
        assert "has no LOV name" in errors[0]
        assert len(result) == 0


class TestMaps:
    """模块级映射完整性测试。"""

    def test_token_to_dtype_complete(self):
        for t in ["TEXT", "NUMBER", "DATE", "BOOLEAN", "URL", "LONG_TEXT", "LOV"]:
            assert t in TOKEN_TO_DTYPE, f"Missing token: {t}"

    def test_token_to_valuecol_complete(self):
        for t in TOKEN_TO_DTYPE:
            assert t in TOKEN_TO_VALUECOL, f"Missing token in VALUECOL: {t}"

    def test_dtype_to_token_reverse(self):
        assert DTYPE_TO_TOKEN["InstanceTextAttribute"] == "TEXT"
        assert DTYPE_TO_TOKEN["InstanceNumberAttribute"] == "NUMBER"
        assert DTYPE_TO_TOKEN["InstanceDateAttribute"] == "DATE"
        assert DTYPE_TO_TOKEN["InstanceBooleanAttribute"] == "BOOLEAN"
        assert DTYPE_TO_TOKEN["InstanceURLAttribute"] == "URL"
        assert DTYPE_TO_TOKEN["InstanceLongTextAttribute"] == "LONG_TEXT"
        assert DTYPE_TO_TOKEN["InstanceListOfValuesAttribute"] == "LOV"

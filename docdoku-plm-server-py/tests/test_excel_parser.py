"""Excel 属性解析器单元测试（对齐 ExcelParser.java）。

测试策略：
1. 用 openpyxl 合成 .xlsx 夹具
2. 调用 parse_excel 解析
3. 断言结果结构、属性值、错误信息
"""

import pytest
from tests.fixtures.make_import_xlsx import (
    make_valid_parts_xlsx,
    make_invalid_date_parts_xlsx,
    make_missing_pmnumber_comment_xlsx,
    make_empty_xlsx,
    make_text_too_long_xlsx,
    make_invalid_boolean_xlsx,
    make_duplicate_attr_xlsx,
    make_multi_value_xlsx,
    make_multi_value_more_values_than_ids_xlsx,
    make_empty_first_col_stop_xlsx,
)


class TestParseValidParts:
    """测试合法 parts 文件解析。"""

    def test_parse_valid_parts(self):
        """合法文件 → errors 为空，parts 数量正确，属性 name/type/value/attribute_id 正确。"""
        from app.services.importers.excel_parser import parse_excel

        data = make_valid_parts_xlsx()
        result = parse_excel(data, import_type="parts")

        assert result.import_type == "parts"
        assert result.errors == [], f"Unexpected errors: {result.errors}"
        assert len(result.parts) == 3

        part1 = result.parts[0]
        assert part1.number == "PART-001"
        assert len(part1.attributes) == 7

        # 属性1: LOV Color
        attr = part1.attributes[0]
        assert attr.name == "Color"
        assert attr.type == "LOV"
        assert attr.value == "Red"
        assert attr.attribute_id == 101
        assert attr.lov_name == "Colors_LOV"

        # 属性2: Number Weight (带 ID)
        attr = part1.attributes[1]
        assert attr.name == "Weight"
        assert attr.type == "NUMBER"
        assert attr.value == "2.5"
        assert attr.attribute_id == 102

        # 属性3: Text Description
        attr = part1.attributes[2]
        assert attr.name == "Description"
        assert attr.type == "TEXT"
        assert attr.value == "Some text"
        assert attr.attribute_id == 103

        # 属性4: Boolean Active
        attr = part1.attributes[3]
        assert attr.name == "Active"
        assert attr.type == "BOOLEAN"
        assert attr.value == "true"
        assert attr.attribute_id == 104

        # 属性5: Date ReleaseDate
        attr = part1.attributes[4]
        assert attr.name == "ReleaseDate"
        assert attr.type == "DATE"
        assert attr.value == "2025-01-15 00:00:00"
        assert attr.attribute_id == 105

        # 属性6: URL DocURL
        attr = part1.attributes[5]
        assert attr.name == "DocURL"
        assert attr.type == "URL"
        assert attr.value == "https://example.com/doc"
        assert attr.attribute_id == 106

        # 属性7: Long_Text Notes
        attr = part1.attributes[6]
        assert attr.name == "Notes"
        assert attr.type == "LONG_TEXT"
        assert attr.value == "Long description text"
        assert attr.attribute_id == 107

        # part2: 新建（无 comment） → attribute_id 全部为 None
        part2 = result.parts[1]
        assert part2.number == "PART-002"
        for attr in part2.attributes:
            assert attr.attribute_id is None, f"Expected None for new attr {attr.name}, got {attr.attribute_id}"

        # part3: 混合
        part3 = result.parts[2]
        assert part3.number == "PART-003"
        # LOV 新建 → id=None
        assert part3.attributes[0].attribute_id is None
        # Number 更新 → id=202
        assert part3.attributes[1].attribute_id == 202
        # Text 新建 → id=None
        assert part3.attributes[2].attribute_id is None
        # Boolean 更新 → id=204
        assert part3.attributes[3].attribute_id == 204
        # Date 新建 → id=None
        assert part3.attributes[4].attribute_id is None
        # URL 更新 → id=206
        assert part3.attributes[5].attribute_id == 206
        # Long_Text 新建 → id=None
        assert part3.attributes[6].attribute_id is None

    def test_lov_header(self):
        """LOV 表头 'Color <ListOfValues> <Colors_LOV>' → type==LOV, lov_name=='Colors_LOV'。"""
        from app.services.importers.excel_parser import parse_excel

        data = make_valid_parts_xlsx()
        result = parse_excel(data, import_type="parts")

        attr = result.parts[0].attributes[0]
        assert attr.name == "Color"
        assert attr.type == "LOV"
        assert attr.lov_name == "Colors_LOV"

    def test_multi_value_cell(self):
        """多值单元格 'a|b' + comment '12|34' → 拆成 2 个 ParsedAttribute，id 分别 12/34。"""
        from app.services.importers.excel_parser import parse_excel

        data = make_multi_value_xlsx()
        result = parse_excel(data, import_type="parts")

        assert result.errors == [], f"Unexpected errors: {result.errors}"
        part = result.parts[0]
        tags_attrs = [a for a in part.attributes if a.name == "Tags"]
        assert len(tags_attrs) == 2
        assert tags_attrs[0].value == "a"
        assert tags_attrs[0].attribute_id == 12
        assert tags_attrs[1].value == "b"
        assert tags_attrs[1].attribute_id == 34

    def test_multi_value_more_values_than_ids(self):
        """值比 ID 多 → errors 含 MISSING_ATTRIBUTE_ID。"""
        from app.services.importers.excel_parser import parse_excel

        data = make_multi_value_more_values_than_ids_xlsx()
        result = parse_excel(data, import_type="parts")

        assert any("MISSING_ATTRIBUTE_ID" in e for e in result.errors), \
            f"Expected MISSING_ATTRIBUTE_ID in errors: {result.errors}"

    def test_invalid_date(self):
        """DATE 列非法值 → errors 含 INVALID_DATE_VALUE。"""
        from app.services.importers.excel_parser import parse_excel

        data = make_invalid_date_parts_xlsx()
        result = parse_excel(data, import_type="parts")

        assert any("INVALID_DATE_VALUE" in e for e in result.errors), \
            f"Expected INVALID_DATE_VALUE in errors: {result.errors}"

    def test_invalid_boolean(self):
        """BOOLEAN 列填 'yes' → errors 含 INVALID_BOOLEAN_VALUE。"""
        from app.services.importers.excel_parser import parse_excel

        data = make_invalid_boolean_xlsx()
        result = parse_excel(data, import_type="parts")

        assert any("INVALID_BOOLEAN_VALUE" in e for e in result.errors), \
            f"Expected INVALID_BOOLEAN_VALUE in errors: {result.errors}"

    def test_text_too_long(self):
        """TEXT 值 >255 → errors 含 INVALID_TEXT_VALUE。"""
        from app.services.importers.excel_parser import parse_excel

        data = make_text_too_long_xlsx()
        result = parse_excel(data, import_type="parts")

        assert any("INVALID_TEXT_VALUE" in e for e in result.errors), \
            f"Expected INVALID_TEXT_VALUE in errors: {result.errors}"

    def test_missing_pmnumber_comment(self):
        """A1 无 pm.number comment → errors 含 INVALID_HEADER。"""
        from app.services.importers.excel_parser import parse_excel

        data = make_missing_pmnumber_comment_xlsx()
        result = parse_excel(data, import_type="parts")

        assert any("INVALID_HEADER" in e for e in result.errors), \
            f"Expected INVALID_HEADER in errors: {result.errors}"

    def test_duplicate_attribute(self):
        """两列同名同类型 → errors 含 DUPLICATE_ATTRIBUTE。"""
        from app.services.importers.excel_parser import parse_excel

        data = make_duplicate_attr_xlsx()
        result = parse_excel(data, import_type="parts")

        assert any("DUPLICATE_ATTRIBUTE" in e for e in result.errors), \
            f"Expected DUPLICATE_ATTRIBUTE in errors: {result.errors}"

    def test_empty_file(self):
        """空 workbook → errors 含 EMPTY_FILE。"""
        from app.services.importers.excel_parser import parse_excel

        data = make_empty_xlsx()
        result = parse_excel(data)

        assert any("EMPTY_FILE" in e for e in result.errors), \
            f"Expected EMPTY_FILE in errors: {result.errors}"

    def test_stop_at_empty_first_column(self):
        """数据中间某行第一列空 → 之后行不再解析。"""
        from app.services.importers.excel_parser import parse_excel

        data = make_empty_first_col_stop_xlsx()
        result = parse_excel(data, import_type="parts")

        assert len(result.parts) == 1  # 只解析了第一行
        assert result.parts[0].number == "PART-001"

    def test_new_vs_update(self):
        """无 comment 的数据单元格 → attribute_id is None（新建）。"""
        from app.services.importers.excel_parser import parse_excel

        data = make_valid_parts_xlsx()
        result = parse_excel(data, import_type="parts")

        part2 = result.parts[1]
        for attr in part2.attributes:
            assert attr.attribute_id is None

    def test_empty_boolean_not_allowed(self):
        """BOOLEAN 列空值应报错（不允许空值类型）。"""
        from app.services.importers.excel_parser import parse_excel

        columns = [
            {"header": "PartNumber", "comment": "pm.number"},
            {"header": "Active <Boolean>", "comment": None},
        ]
        from tests.fixtures.make_import_xlsx import make_xlsx
        data = make_xlsx(columns, [
            {"values": ["PART-001", None], "comments": [None, "101"]},
        ])
        result = parse_excel(data, import_type="parts")
        assert any("EMPTY_FIELD" in e for e in result.errors), \
            f"Expected EMPTY_FIELD for empty BOOLEAN: {result.errors}"

    def test_empty_number_not_allowed(self):
        """NUMBER 列空值应报错。"""
        from app.services.importers.excel_parser import parse_excel

        columns = [
            {"header": "PartNumber", "comment": "pm.number"},
            {"header": "Weight <Number>", "comment": None},
        ]
        from tests.fixtures.make_import_xlsx import make_xlsx
        data = make_xlsx(columns, [
            {"values": ["PART-001", None], "comments": [None, "101"]},
        ])
        result = parse_excel(data, import_type="parts")
        assert any("EMPTY_FIELD" in e for e in result.errors), \
            f"Expected EMPTY_FIELD for empty NUMBER: {result.errors}"

    def test_empty_lov_not_allowed(self):
        """LOV 列空值应报错。"""
        from app.services.importers.excel_parser import parse_excel

        columns = [
            {"header": "PartNumber", "comment": "pm.number"},
            {"header": "Color <ListOfValues> <Colors_LOV>", "comment": None},
        ]
        from tests.fixtures.make_import_xlsx import make_xlsx
        data = make_xlsx(columns, [
            {"values": ["PART-001", None], "comments": [None, "101"]},
        ])
        result = parse_excel(data, import_type="parts")
        assert any("EMPTY_FIELD" in e for e in result.errors), \
            f"Expected EMPTY_FIELD for empty LOV: {result.errors}"

    def test_text_empty_allowed(self):
        """TEXT 列空值应允许。"""
        from app.services.importers.excel_parser import parse_excel

        columns = [
            {"header": "PartNumber", "comment": "pm.number"},
            {"header": "Desc <Text>", "comment": None},
        ]
        from tests.fixtures.make_import_xlsx import make_xlsx
        data = make_xlsx(columns, [
            {"values": ["PART-001", None], "comments": [None, None]},
        ])
        result = parse_excel(data, import_type="parts")
        assert result.errors == [], f"Unexpected errors for empty TEXT: {result.errors}"

    def test_date_empty_allowed(self):
        """DATE 列空值应允许。"""
        from app.services.importers.excel_parser import parse_excel

        columns = [
            {"header": "PartNumber", "comment": "pm.number"},
            {"header": "Release <Date>", "comment": None},
        ]
        from tests.fixtures.make_import_xlsx import make_xlsx
        data = make_xlsx(columns, [
            {"values": ["PART-001", None], "comments": [None, None]},
        ])
        result = parse_excel(data, import_type="parts")
        assert result.errors == [], f"Unexpected errors for empty DATE: {result.errors}"


class TestParsePathdata:
    """测试 pathdata 导入文件解析。"""

    def test_pathdata_header_validation(self):
        """pathdata: 前三列 comment 依次为 ctx.productId, ctx.serialNumber, pm.number。"""
        from app.services.importers.excel_parser import parse_excel
        from tests.fixtures.make_import_xlsx import make_pathdata_xlsx

        data = make_pathdata_xlsx()
        result = parse_excel(data, import_type="pathdata")

        assert result.import_type == "pathdata"
        assert result.errors == [], f"Unexpected errors: {result.errors}"
        assert len(result.parts) == 2
        part1 = result.parts[0]
        assert part1.number == "PART-001"
        assert part1.product_id == "PROD-001"
        assert part1.serial_number == "SN-001"

    def test_pathdata_header_invalid_product_id(self):
        """pathdata: A1 comment 不是 ctx.productId → INVALID_HEADER。"""
        from app.services.importers.excel_parser import parse_excel
        from tests.fixtures.make_import_xlsx import make_xlsx

        columns = [
            {"header": "BadCol", "comment": "not.productId"},
            {"header": "SN", "comment": "ctx.serialNumber"},
            {"header": "PN", "comment": "pm.number"},
            {"header": "Attr <Text>", "comment": None},
        ]
        data = make_xlsx(columns, [
            {"values": ["a", "b", "c", "d"], "comments": [None, None, None, None]},
        ])
        result = parse_excel(data, import_type="pathdata")
        assert any("INVALID_HEADER" in e for e in result.errors), \
            f"Expected INVALID_HEADER: {result.errors}"

    def test_pathdata_too_few_columns(self):
        """pathdata: 列数 ≤ 3 → INVALID_COLUMNS_NUMBER。"""
        from app.services.importers.excel_parser import parse_excel
        from tests.fixtures.make_import_xlsx import make_xlsx

        columns = [
            {"header": "Prod", "comment": "ctx.productId"},
            {"header": "SN", "comment": "ctx.serialNumber"},
            {"header": "PN", "comment": "pm.number"},
        ]  # 只有 3 列
        data = make_xlsx(columns, [
            {"values": ["a", "b", "c"], "comments": [None, None, None]},
        ])
        result = parse_excel(data, import_type="pathdata")
        assert any("INVALID_COLUMNS_NUMBER" in e for e in result.errors), \
            f"Expected INVALID_COLUMNS_NUMBER: {result.errors}"


class TestHeaderTypeParsing:
    """测试表头类型解析的各种情况。"""

    def test_header_with_comment_type(self):
        """表头无正则匹配但有 comment → 用 comment 文本作为类型。"""
        from app.services.importers.excel_parser import parse_excel
        from tests.fixtures.make_import_xlsx import make_xlsx

        columns = [
            {"header": "PartNumber", "comment": "pm.number"},
            {"header": "My Field", "comment": "TEXT"},
        ]
        data = make_xlsx(columns, [
            {"values": ["PART-001", "hello"], "comments": [None, None]},
        ])
        result = parse_excel(data, import_type="parts")
        assert result.errors == [], f"Unexpected errors: {result.errors}"
        attr = result.parts[0].attributes[0]
        assert attr.name == "My Field"
        assert attr.type == "TEXT"

    def test_header_no_comment_no_pattern(self):
        """表头无正则匹配也无 comment → MISSING_COMMENT。"""
        from app.services.importers.excel_parser import parse_excel
        from tests.fixtures.make_import_xlsx import make_xlsx

        columns = [
            {"header": "PartNumber", "comment": "pm.number"},
            {"header": "BareHeader", "comment": None},
        ]
        data = make_xlsx(columns, [
            {"values": ["PART-001", "val"], "comments": [None, None]},
        ])
        result = parse_excel(data, import_type="parts")
        assert any("MISSING_COMMENT" in e for e in result.errors), \
            f"Expected MISSING_COMMENT: {result.errors}"

    def test_header_invalid_type(self):
        """表头类型在合法集合之外 → ATTRIBUTE_TYPE_NOT_FOUND。"""
        from app.services.importers.excel_parser import parse_excel
        from tests.fixtures.make_import_xlsx import make_xlsx

        columns = [
            {"header": "PartNumber", "comment": "pm.number"},
            {"header": "Bad <UnknownType>", "comment": None},
        ]
        data = make_xlsx(columns, [
            {"values": ["PART-001", "val"], "comments": [None, None]},
        ])
        result = parse_excel(data, import_type="parts")
        assert any("ATTRIBUTE_TYPE_NOT_FOUND" in e for e in result.errors), \
            f"Expected ATTRIBUTE_TYPE_NOT_FOUND: {result.errors}"

    def test_invalid_attribute_id_format(self):
        """comment 中的 attribute id 不是纯数字 → INVALID_ATTRIBUTE_ID。"""
        from app.services.importers.excel_parser import parse_excel
        from tests.fixtures.make_import_xlsx import make_xlsx

        columns = [
            {"header": "PartNumber", "comment": "pm.number"},
            {"header": "Attr <Text>", "comment": None},
        ]
        data = make_xlsx(columns, [
            {"values": ["PART-001", "val"], "comments": [None, "abc"]},
        ])
        result = parse_excel(data, import_type="parts")
        assert any("INVALID_ATTRIBUTE_ID" in e for e in result.errors), \
            f"Expected INVALID_ATTRIBUTE_ID: {result.errors}"


class TestEdgeCases:
    """边界情况测试。"""

    def test_invalid_file_bytes(self):
        """非法字节流（非 xlsx）→ EMPTY_FILE 错误，不抛异常。"""
        from app.services.importers.excel_parser import parse_excel

        result = parse_excel(b"not an xlsx file", import_type="parts")
        assert any("EMPTY_FILE" in e for e in result.errors), \
            f"Expected EMPTY_FILE for invalid bytes: {result.errors}"

    def test_only_header_row(self):
        """只有表头没有数据行 → parts 为空。"""
        from app.services.importers.excel_parser import parse_excel
        from tests.fixtures.make_import_xlsx import make_xlsx

        columns = [
            {"header": "PartNumber", "comment": "pm.number"},
            {"header": "Attr <Text>", "comment": None},
        ]
        data = make_xlsx(columns, [])
        result = parse_excel(data, import_type="parts")
        assert result.errors == []
        assert result.parts == []

    def test_invalid_number_value(self):
        """NUMBER 列非法值 → INVALID_NUMBER_VALUE。"""
        from app.services.importers.excel_parser import parse_excel
        from tests.fixtures.make_import_xlsx import make_xlsx

        columns = [
            {"header": "PartNumber", "comment": "pm.number"},
            {"header": "Weight <Number>", "comment": None},
        ]
        data = make_xlsx(columns, [
            {"values": ["PART-001", "not-a-number"], "comments": [None, "101"]},
        ])
        result = parse_excel(data, import_type="parts")
        assert any("INVALID_NUMBER_VALUE" in e for e in result.errors), \
            f"Expected INVALID_NUMBER_VALUE: {result.errors}"

    def test_invalid_url_value(self):
        """URL 列非法值 → INVALID_URL_VALUE。"""
        from app.services.importers.excel_parser import parse_excel
        from tests.fixtures.make_import_xlsx import make_xlsx

        columns = [
            {"header": "PartNumber", "comment": "pm.number"},
            {"header": "Link <URL>", "comment": None},
        ]
        data = make_xlsx(columns, [
            {"values": ["PART-001", "not-a-url"], "comments": [None, "101"]},
        ])
        result = parse_excel(data, import_type="parts")
        assert any("INVALID_URL_VALUE" in e for e in result.errors), \
            f"Expected INVALID_URL_VALUE: {result.errors}"

    def test_empty_field_other_cols_have_value(self):
        """第一列空但其他列有值 → EMPTY_FIELD（parts 导入）。"""
        from app.services.importers.excel_parser import parse_excel
        from tests.fixtures.make_import_xlsx import make_xlsx

        columns = [
            {"header": "PartNumber", "comment": "pm.number"},
            {"header": "Attr <Text>", "comment": None},
        ]
        data = make_xlsx(columns, [
            {"values": [None, "val"], "comments": [None, None]},
        ])
        result = parse_excel(data, import_type="parts")
        assert any("EMPTY_FIELD" in e for e in result.errors), \
            f"Expected EMPTY_FIELD: {result.errors}"

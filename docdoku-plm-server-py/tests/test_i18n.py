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

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

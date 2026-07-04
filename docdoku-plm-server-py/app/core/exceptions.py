from app.core import i18n


class ApplicationException(Exception):

    def __init__(self, key: str, *args):
        self.key = key
        self.fmt_args = args
        super().__init__(key)

    def translate(self, lang: str | None = None) -> str:
        return i18n.get(self.key, lang, *self.fmt_args)


class AccessRightException(ApplicationException):
    pass


class NotAllowedException(ApplicationException):
    pass


class EntityConstraintException(ApplicationException):
    pass


class EntityNotFoundException(ApplicationException):
    pass


class EntityAlreadyExistsException(ApplicationException):
    pass


class CreationException(ApplicationException):
    pass

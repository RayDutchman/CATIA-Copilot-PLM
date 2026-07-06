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


class UserNotFoundException(EntityNotFoundException):
    pass


class PartMasterNotFoundException(EntityNotFoundException):
    pass


class PartRevisionNotFoundException(EntityNotFoundException):
    pass


class PartIterationNotFoundException(EntityNotFoundException):
    pass


class ConfigurationItemNotFoundException(EntityNotFoundException):
    pass


class WorkspaceNotFoundException(EntityNotFoundException):
    pass


class SharedEntityNotFoundException(EntityNotFoundException):
    pass


# ============================================================
# NotFoundException → EntityNotFoundException
# ============================================================


class AccountNotFoundException(EntityNotFoundException):
    pass


class BaselineNotFoundException(EntityNotFoundException):
    pass


class ChangeIssueNotFoundException(EntityNotFoundException):
    pass


class ChangeOrderNotFoundException(EntityNotFoundException):
    pass


class ChangeRequestNotFoundException(EntityNotFoundException):
    pass


class DocumentIterationNotFoundException(EntityNotFoundException):
    pass


class DocumentMasterTemplateNotFoundException(EntityNotFoundException):
    pass


class DocumentRevisionNotFoundException(EntityNotFoundException):
    pass


class FileNotFoundException(EntityNotFoundException):
    pass


class FolderNotFoundException(EntityNotFoundException):
    pass


class GCMAccountNotFoundException(EntityNotFoundException):
    pass


class LayerNotFoundException(EntityNotFoundException):
    pass


class ListOfValuesNotFoundException(EntityNotFoundException):
    pass


class MarkerNotFoundException(EntityNotFoundException):
    pass


class MilestoneNotFoundException(EntityNotFoundException):
    pass


class OrganizationNotFoundException(EntityNotFoundException):
    pass


class PartMasterTemplateNotFoundException(EntityNotFoundException):
    pass


class PartUsageLinkNotFoundException(EntityNotFoundException):
    pass


class PasswordRecoveryRequestNotFoundException(EntityNotFoundException):
    pass


class PathDataMasterNotFoundException(EntityNotFoundException):
    pass


class PathToPathLinkNotFoundException(EntityNotFoundException):
    pass


class ProductConfigurationNotFoundException(EntityNotFoundException):
    pass


class ProductInstanceIterationNotFoundException(EntityNotFoundException):
    pass


class ProductInstanceMasterNotFoundException(EntityNotFoundException):
    pass


class RoleNotFoundException(EntityNotFoundException):
    pass


class TagNotFoundException(EntityNotFoundException):
    pass


class TaskNotFoundException(EntityNotFoundException):
    pass


class UserGroupNotFoundException(EntityNotFoundException):
    pass


class WebhookNotFoundException(EntityNotFoundException):
    pass


class WorkflowModelNotFoundException(EntityNotFoundException):
    pass


class WorkflowNotFoundException(EntityNotFoundException):
    pass


# ============================================================
# AlreadyExistsException → EntityAlreadyExistsException
# ============================================================


class AccountAlreadyExistsException(EntityAlreadyExistsException):
    pass


class ConfigurationItemAlreadyExistsException(EntityAlreadyExistsException):
    pass


class DocumentMasterAlreadyExistsException(EntityAlreadyExistsException):
    pass


class DocumentMasterTemplateAlreadyExistsException(EntityAlreadyExistsException):
    pass


class DocumentRevisionAlreadyExistsException(EntityAlreadyExistsException):
    pass


class FileAlreadyExistsException(EntityAlreadyExistsException):
    pass


class FolderAlreadyExistsException(EntityAlreadyExistsException):
    pass


class GCMAccountAlreadyExistsException(EntityAlreadyExistsException):
    pass


class MilestoneAlreadyExistsException(EntityAlreadyExistsException):
    pass


class OrganizationAlreadyExistsException(EntityAlreadyExistsException):
    pass


class PartMasterAlreadyExistsException(EntityAlreadyExistsException):
    pass


class PartMasterTemplateAlreadyExistsException(EntityAlreadyExistsException):
    pass


class PartRevisionAlreadyExistsException(EntityAlreadyExistsException):
    pass


class PathDataAlreadyExistsException(EntityAlreadyExistsException):
    pass


class PathToPathLinkAlreadyExistsException(EntityAlreadyExistsException):
    pass


class ProductInstanceAlreadyExistsException(EntityAlreadyExistsException):
    pass


class QueryAlreadyExistsException(EntityAlreadyExistsException):
    pass


class RoleAlreadyExistsException(EntityAlreadyExistsException):
    pass


class TagAlreadyExistsException(EntityAlreadyExistsException):
    pass


class UserAlreadyExistsException(EntityAlreadyExistsException):
    pass


class UserGroupAlreadyExistsException(EntityAlreadyExistsException):
    pass


class WorkflowModelAlreadyExistsException(EntityAlreadyExistsException):
    pass


class WorkspaceAlreadyExistsException(EntityAlreadyExistsException):
    pass


# ============================================================
# Other → ApplicationException
# ============================================================


class BaselineWarningException(ApplicationException):
    pass


class ConvertedResourceException(ApplicationException):
    pass


class IndexNamingException(ApplicationException):
    pass


class IndexerNotAvailableException(ApplicationException):
    pass


class IndexerRequestException(ApplicationException):
    pass


class IndexerServerException(ApplicationException):
    pass


class LOVNameEmptyException(ApplicationException):
    pass


class LOVPossibleValueException(ApplicationException):
    pass


class MaskCreationException(ApplicationException):
    pass


class MissingIndexException(ApplicationException):
    pass


class PartRevisionNotReleasedException(ApplicationException):
    pass


class PathToPathCyclicException(ApplicationException):
    pass


class UpdateException(ApplicationException):
    pass


class UserNotActiveException(ApplicationException):
    pass


class WorkflowNameEmptyException(ApplicationException):
    pass


class WorkspaceNotEnabledException(ApplicationException):
    """Payara WorkspaceNotEnabledException(pWorkspaceId)"""


class WrongInputException(ApplicationException):
    pass


class PlatformHealthException(ApplicationException):
    pass
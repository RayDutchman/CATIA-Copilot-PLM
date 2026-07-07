from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from app.core.exceptions import (
    ApplicationException, AccessRightException, NotAllowedException,
    EntityConstraintException, EntityNotFoundException,
    EntityAlreadyExistsException, CreationException,
    WorkspaceNotEnabledException, PlatformHealthException,
    AccountNotFoundException,
    BaselineNotFoundException,
    ChangeIssueNotFoundException,
    ChangeOrderNotFoundException,
    ChangeRequestNotFoundException,
    ConfigurationItemNotFoundException,
    DocumentIterationNotFoundException,
    DocumentMasterTemplateNotFoundException,
    DocumentRevisionNotFoundException,
    FileNotFoundException,
    FolderNotFoundException,
    GCMAccountNotFoundException,
    LayerNotFoundException,
    ListOfValuesNotFoundException,
    MarkerNotFoundException,
    MilestoneNotFoundException,
    OrganizationNotFoundException,
    PartIterationNotFoundException,
    PartMasterNotFoundException,
    PartMasterTemplateNotFoundException,
    PartRevisionNotFoundException,
    PartUsageLinkNotFoundException,
    PasswordRecoveryRequestNotFoundException,
    PathDataMasterNotFoundException,
    PathToPathLinkNotFoundException,
    ProductConfigurationNotFoundException,
    ProductInstanceIterationNotFoundException,
    ProductInstanceMasterNotFoundException,
    RoleNotFoundException,
    SharedEntityNotFoundException,
    TagNotFoundException,
    TaskNotFoundException,
    UserGroupNotFoundException,
    UserNotFoundException,
    WebhookNotFoundException,
    WorkflowModelNotFoundException,
    WorkflowNotFoundException,
    WorkspaceNotFoundException,
)

_404_EXCEPTIONS = (
    EntityNotFoundException,
    AccountNotFoundException,
    BaselineNotFoundException,
    ChangeIssueNotFoundException,
    ChangeOrderNotFoundException,
    ChangeRequestNotFoundException,
    ConfigurationItemNotFoundException,
    DocumentIterationNotFoundException,
    DocumentMasterTemplateNotFoundException,
    DocumentRevisionNotFoundException,
    FileNotFoundException,
    FolderNotFoundException,
    GCMAccountNotFoundException,
    LayerNotFoundException,
    ListOfValuesNotFoundException,
    MarkerNotFoundException,
    MilestoneNotFoundException,
    OrganizationNotFoundException,
    PartIterationNotFoundException,
    PartMasterNotFoundException,
    PartMasterTemplateNotFoundException,
    PartRevisionNotFoundException,
    PartUsageLinkNotFoundException,
    PasswordRecoveryRequestNotFoundException,
    PathDataMasterNotFoundException,
    PathToPathLinkNotFoundException,
    ProductConfigurationNotFoundException,
    ProductInstanceIterationNotFoundException,
    ProductInstanceMasterNotFoundException,
    RoleNotFoundException,
    SharedEntityNotFoundException,
    TagNotFoundException,
    TaskNotFoundException,
    UserGroupNotFoundException,
    UserNotFoundException,
    WebhookNotFoundException,
    WorkflowModelNotFoundException,
    WorkflowNotFoundException,
    WorkspaceNotFoundException,
)


def _status_for(exc: ApplicationException) -> int:
    if isinstance(exc, EntityConstraintException):
        return 403
    if isinstance(exc, (AccessRightException, NotAllowedException, WorkspaceNotEnabledException)):
        return 403
    if isinstance(exc, EntityNotFoundException):
        return 404
    if isinstance(exc, EntityAlreadyExistsException):
        return 409
    if isinstance(exc, CreationException):
        return 500
    if isinstance(exc, PlatformHealthException):
        return 503
    return 500


async def _not_found_handler(request: Request, exc: EntityNotFoundException) -> PlainTextResponse:
    lang = getattr(request.state, "user_language", None)
    return PlainTextResponse(content=exc.translate(lang), status_code=404)


def register_exception_handlers(app: FastAPI) -> None:
    for exc_cls in _404_EXCEPTIONS:
        app.add_exception_handler(exc_cls, _not_found_handler)

    @app.exception_handler(ApplicationException)
    async def _application_handler(request: Request, exc: ApplicationException):
        lang = getattr(request.state, "user_language", None)
        return PlainTextResponse(
            content=exc.translate(lang),
            status_code=_status_for(exc),
        )

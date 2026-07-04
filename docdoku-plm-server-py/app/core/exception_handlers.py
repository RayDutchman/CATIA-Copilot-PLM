from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.core.exceptions import (
    ApplicationException, AccessRightException, NotAllowedException,
    EntityConstraintException, EntityNotFoundException,
    EntityAlreadyExistsException, CreationException,
)


def _status_for(exc: ApplicationException) -> int:
    if isinstance(exc, (AccessRightException, NotAllowedException,
                        EntityConstraintException)):
        return 403
    if isinstance(exc, EntityNotFoundException):
        return 404
    if isinstance(exc, EntityAlreadyExistsException):
        return 409
    if isinstance(exc, CreationException):
        return 500
    return 500


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApplicationException)
    async def _handle(request: Request, exc: ApplicationException):
        lang = getattr(request.state, "user_language", None)
        return JSONResponse(
            status_code=_status_for(exc),
            content={"message": exc.translate(lang)},
        )

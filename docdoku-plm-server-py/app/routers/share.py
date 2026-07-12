"""共享文档/零件端点（公开访问，无需认证）。"""
from fastapi import APIRouter, HTTPException, Depends, Header, Response
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import JWTError
from app.core.database import get_db
from app.core.security import create_token, verify_token, create_entity_token
from app.core.deps import bearer_scheme
from app.core.exceptions import (
    AccessRightException, EntityNotFoundException, NotAllowedException,
    PartRevisionNotFoundException, SharedEntityNotFoundException,
    WorkspaceNotFoundException,
)
from app.schemas.misc import SharedDocumentDTO, SharedPartDTO
from app.models.util.date_utils import format_iso_date
from app.services.share_manager import share_service

router = APIRouter(prefix="/docdoku-plm-server-rest/api")

_STATUS_MAP = {0: "WIP", 1: "RELEASED", 2: "OBSOLETE"}


def _get_author_dto(db: Session, login: str | None, ws: str) -> dict:
    if not login:
        return {"login": "", "name": "", "email": None, "language": None, "workspaceId": ws}
    info = share_service.get_account_info(db, login)
    return {
        "login": info["login"],
        "name": info["name"],
        "email": info["email"],
        "language": info["language"],
        "workspaceId": ws,
    }


def _get_optional_login(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> str | None:
    """可选的用户认证：有有效 token 返回 login，否则返回 None。"""
    if credentials is None:
        return None
    try:
        payload = verify_token(credentials.credentials)
        return payload["login"]
    except (JWTError, Exception):
        return None


def _check_workspace_member(db: Session, login: str, ws: str):
    """对齐 Payara checkWorkspaceReadAccess：验证工作区启用且用户是成员。"""
    share_service.check_workspace_member(db, login, ws)


@router.get("/shared/{uuid}/documents", response_model=SharedDocumentDTO)
@router.get("/shared/{uuid}/documents/", include_in_schema=False)
def get_shared_documents(uuid: str,
                         response: Response,
                         password: str | None = Header(None),
                         db: Session = Depends(get_db)):
    status, entity = share_service.get_shared_entity(db, uuid, password)
    if status == "password-required":
        raise HTTPException(status_code=403, detail={"forbidden": "password-protected"},
                            headers={"Reason-Phrase": "password-protected"})
    if status == "expired":
        raise HTTPException(status_code=404, detail={"forbidden": "entity-expired"},
                            headers={"Reason-Phrase": "entity-expired"})
    if entity.dtype != "SharedDocument":
        raise SharedEntityNotFoundException("SharedEntityNotFoundException", uuid)

    doc = share_service.get_shared_document_row(db, entity)

    if not doc:
        raise SharedEntityNotFoundException("SharedEntityNotFoundException", uuid)

    response.headers["entity-token"] = create_entity_token(uuid)
    response.headers["shared-entity-token"] = create_entity_token(uuid)
    return {
        "id": doc.documentmaster_id,
        "workspaceId": doc.workspace_id,
        "version": doc.version,
        "type": doc.type,
        "title": doc.title,
        "description": doc.description,
        "status": _STATUS_MAP.get(doc.status, "WIP"),
        "author": _get_author_dto(db, doc.author_login, doc.workspace_id),
        "creationDate": format_iso_date(doc.creationdate),
    }


@router.get("/shared/{uuid}/parts", response_model=SharedPartDTO)
@router.get("/shared/{uuid}/parts/", include_in_schema=False)
def get_shared_parts(uuid: str,
                     response: Response,
                     password: str | None = Header(None),
                     db: Session = Depends(get_db)):
    status, entity = share_service.get_shared_entity(db, uuid, password)
    if status == "password-required":
        raise HTTPException(status_code=403, detail={"forbidden": "password-protected"},
                            headers={"Reason-Phrase": "password-protected"})
    if status == "expired":
        raise HTTPException(status_code=404, detail={"forbidden": "entity-expired"},
                            headers={"Reason-Phrase": "entity-expired"})
    if entity.dtype != "SharedPart":
        raise SharedEntityNotFoundException("SharedEntityNotFoundException", uuid)

    part = share_service.get_shared_part_row(db, entity)

    if not part:
        raise SharedEntityNotFoundException("SharedEntityNotFoundException", uuid)

    response.headers["entity-token"] = create_entity_token(uuid)
    response.headers["shared-entity-token"] = create_entity_token(uuid)
    return {
        "partNumber": part.partnumber,
        "version": part.version,
        "workspaceId": part.workspace_id,
        "name": part.name,
        "type": part.type,
        "description": part.description,
        "status": _STATUS_MAP.get(part.status, "WIP"),
        "author": _get_author_dto(db, part.author_login, part.workspace_id),
        "creationDate": format_iso_date(part.creationdate),
    }


@router.get("/shared/{ws}/documents/{doc_id}-{ver}", response_model=SharedDocumentDTO)
@router.get("/shared/{ws}/documents/{doc_id}-{ver}/", include_in_schema=False)
def get_public_shared_document(ws: str, doc_id: str, ver: str,
                               response: Response,
                               db: Session = Depends(get_db),
                               login: str | None = Depends(_get_optional_login)):
    """返回公开共享的文档详情。
    public_shared=True 时可公开访问；
    public_shared=False 时若已认证可正常访问，否则返回 403。
    """
    doc = share_service.get_document_revision(db, ws, doc_id, ver)

    if not doc:
        raise EntityNotFoundException("DocumentRevisionNotFoundException", doc_id, ver)

    if not doc.public_shared:
        if login is None:
            raise NotAllowedException("NotAllowedException5")
        _check_workspace_member(db, login, ws)

    response.headers["entity-token"] = create_entity_token(ws, login or "")
    return {
        "id": doc.documentmaster_id,
        "workspaceId": doc.workspace_id,
        "version": doc.version,
        "type": doc.document_master.type if doc.document_master else None,
        "title": doc.title,
        "description": doc.description,
        "status": _STATUS_MAP.get(doc.status, "WIP"),
        "author": _get_author_dto(db, doc.author_login, doc.workspace_id),
        "creationDate": format_iso_date(doc.creation_date),
    }


@router.get("/shared/{ws}/parts/{pn}-{ver}", response_model=SharedPartDTO)
@router.get("/shared/{ws}/parts/{pn}-{ver}/", include_in_schema=False)
def get_public_shared_part(ws: str, pn: str, ver: str,
                           response: Response,
                           db: Session = Depends(get_db),
                           login: str | None = Depends(_get_optional_login)):
    """返回公开共享的零件详情。
    public_shared=True 时可公开访问；
    public_shared=False 时若已认证可正常访问，否则返回 403。
    """
    part = share_service.get_part_revision(db, ws, pn, ver)

    if not part:
        raise PartRevisionNotFoundException("PartRevisionNotFoundException", pn, ver)

    if not part.public_shared:
        if login is None:
            raise NotAllowedException("NotAllowedException5")
        _check_workspace_member(db, login, ws)

    response.headers["entity-token"] = create_entity_token(ws, login or "")
    return {
        "partNumber": part.partmaster_partnumber,
        "version": part.version,
        "workspaceId": part.workspace_id,
        "name": part.part_master.name if part.part_master else None,
        "type": part.part_master.type if part.part_master else None,
        "description": part.description,
        "status": _STATUS_MAP.get(part.status, "WIP"),
        "author": _get_author_dto(db, part.author_login, part.workspace_id),
        "creationDate": format_iso_date(part.creation_date),
    }

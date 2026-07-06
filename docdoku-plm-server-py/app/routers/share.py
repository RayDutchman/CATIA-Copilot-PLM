"""共享文档/零件端点（公开访问，无需认证）。"""
import hashlib
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import get_db
from app.models.auth import Account
from app.models.document import DocumentRevision
from app.models.part import PartRevision

router = APIRouter(prefix="/docdoku-plm-server-rest/api")

_STATUS_MAP = {0: "WIP", 1: "RELEASED", 2: "OBSOLETE"}


def _fmt_date(d) -> str | None:
    if d is None:
        return None
    return d.strftime("%Y-%m-%dT%H:%M:%S.") + f"{d.microsecond // 1000:03d}Z"


def _get_author_dto(db: Session, login: str | None, ws: str) -> dict:
    if not login:
        return {"login": "", "name": "", "email": None, "language": None, "workspaceId": ws}
    acc = db.query(Account).filter(Account.login == login).first()
    return {
        "login": login,
        "name": acc.name if acc else login,
        "email": acc.email if acc else None,
        "language": acc.language if acc else None,
        "workspaceId": ws,
    }


def _get_shared_entity(uuid: str, password: str | None, db: Session):
    entity = db.execute(text(
        "SELECT uuid, dtype, entity_workspace_id, password, expire_date, "
        "partmaster_partnumber, partrevision_version, "
        "documentmaster_id, documentrevision_version "
        "FROM sharedentity WHERE uuid = :uuid"
    ), {"uuid": uuid}).fetchone()

    if not entity:
        raise HTTPException(status_code=404, detail="共享实体不存在或已过期")

    if password is not None and entity.password is not None and \
            hashlib.md5(password.encode()).hexdigest() != entity.password:
        raise HTTPException(status_code=403, detail="密码错误")

    if entity.expire_date is not None:
        now = datetime.now(timezone.utc)
        expire = entity.expire_date.replace(tzinfo=timezone.utc) if entity.expire_date.tzinfo is None else entity.expire_date
        if expire < now:
            raise HTTPException(status_code=404, detail="共享实体不存在或已过期")

    return entity


@router.get("/shared/{uuid}/documents")
@router.get("/shared/{uuid}/documents/", include_in_schema=False)
def get_shared_documents(uuid: str,
                         password: str | None = Query(None),
                         db: Session = Depends(get_db)):
    entity = _get_shared_entity(uuid, password, db)
    if entity.dtype != "SharedDocument":
        raise HTTPException(status_code=404, detail="共享实体不存在或已过期")

    doc = db.execute(text(
        "SELECT d.title, d.description, d.status, d.author_login, d.creationdate, "
        "dm.type, d.version, dm.id AS documentmaster_id, d.workspace_id "
        "FROM documentrevision d "
        "JOIN documentmaster dm ON dm.workspace_id = d.workspace_id "
        "AND dm.id = d.documentmaster_id "
        "WHERE d.workspace_id = :ws AND d.documentmaster_id = :dmid "
        "AND d.version = :ver"
    ), {
        "ws": entity.entity_workspace_id,
        "dmid": entity.documentmaster_id,
        "ver": entity.documentrevision_version,
    }).fetchone()

    if not doc:
        raise HTTPException(status_code=404, detail="共享实体不存在或已过期")

    return {
        "id": doc.documentmaster_id,
        "workspaceId": doc.workspace_id,
        "version": doc.version,
        "type": doc.type,
        "title": doc.title,
        "description": doc.description,
        "status": _STATUS_MAP.get(doc.status, "WIP"),
        "author": _get_author_dto(db, doc.author_login, doc.workspace_id),
        "creationDate": _fmt_date(doc.creationdate),
    }


@router.get("/shared/{uuid}/parts")
@router.get("/shared/{uuid}/parts/", include_in_schema=False)
def get_shared_parts(uuid: str,
                     password: str | None = Query(None),
                     db: Session = Depends(get_db)):
    entity = _get_shared_entity(uuid, password, db)
    if entity.dtype != "SharedPart":
        raise HTTPException(status_code=404, detail="共享实体不存在或已过期")

    part = db.execute(text(
        "SELECT pr.description, pr.status, pr.author_login, pr.creationdate, "
        "pm.type, pm.name, pm.partnumber, pr.version, pr.workspace_id "
        "FROM partrevision pr "
        "JOIN partmaster pm ON pm.workspace_id = pr.workspace_id "
        "AND pm.partnumber = pr.partmaster_partnumber "
        "WHERE pr.workspace_id = :ws AND pr.partmaster_partnumber = :pn "
        "AND pr.version = :ver"
    ), {
        "ws": entity.entity_workspace_id,
        "pn": entity.partmaster_partnumber,
        "ver": entity.partrevision_version,
    }).fetchone()

    if not part:
        raise HTTPException(status_code=404, detail="共享实体不存在或已过期")

    return {
        "partNumber": part.partnumber,
        "version": part.version,
        "workspaceId": part.workspace_id,
        "name": part.name,
        "type": part.type,
        "description": part.description,
        "status": _STATUS_MAP.get(part.status, "WIP"),
        "author": _get_author_dto(db, part.author_login, part.workspace_id),
        "creationDate": _fmt_date(part.creationdate),
    }


@router.get("/shared/{ws}/documents/{doc_id}-{ver}")
@router.get("/shared/{ws}/documents/{doc_id}-{ver}/", include_in_schema=False)
def get_public_shared_document(ws: str, doc_id: str, ver: str,
                                db: Session = Depends(get_db)):
    """返回公开共享的文档详情（public_shared=True 即可访问，无需 sharedentity）。"""
    doc = db.query(DocumentRevision).filter(
        DocumentRevision.workspace_id == ws,
        DocumentRevision.documentmaster_id == doc_id,
        DocumentRevision.version == ver,
        DocumentRevision.public_shared == True,
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="共享文档不存在或未公开")
    return {
        "id": doc.documentmaster_id,
        "workspaceId": doc.workspace_id,
        "version": doc.version,
        "type": doc.document_master.type if doc.document_master else None,
        "title": doc.title,
        "description": doc.description,
        "status": _STATUS_MAP.get(doc.status, "WIP"),
        "author": _get_author_dto(db, doc.author_login, doc.workspace_id),
        "creationDate": _fmt_date(doc.creation_date),
    }


@router.get("/shared/{ws}/parts/{pn}-{ver}")
@router.get("/shared/{ws}/parts/{pn}-{ver}/", include_in_schema=False)
def get_public_shared_part(ws: str, pn: str, ver: str,
                            db: Session = Depends(get_db)):
    """返回公开共享的零件详情（public_shared=True 即可访问，无需 sharedentity）。"""
    part = db.query(PartRevision).filter(
        PartRevision.workspace_id == ws,
        PartRevision.partmaster_partnumber == pn,
        PartRevision.version == ver,
        PartRevision.public_shared == True,
    ).first()
    if not part:
        raise HTTPException(status_code=404, detail="共享零件不存在或未公开")
    return {
        "partNumber": part.partmaster_partnumber,
        "version": part.version,
        "workspaceId": part.workspace_id,
        "name": part.part_master.name if part.part_master else None,
        "type": part.part_master.type if part.part_master else None,
        "description": part.description,
        "status": _STATUS_MAP.get(part.status, "WIP"),
        "author": _get_author_dto(db, part.author_login, part.workspace_id),
        "creationDate": _fmt_date(part.creation_date),
    }

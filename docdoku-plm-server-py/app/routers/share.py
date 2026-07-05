"""共享文档/零件端点（公开访问，无需认证）。"""
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import get_db

router = APIRouter(prefix="/docdoku-plm-server-rest/api")


def _get_shared_entity(uuid: str, password: str | None, db: Session):
    entity = db.execute(text(
        "SELECT uuid, dtype, entity_workspace_id, password, expire_date, "
        "partmaster_partnumber, partrevision_version, "
        "documentmaster_id, documentrevision_version "
        "FROM sharedentity WHERE uuid = :uuid"
    ), {"uuid": uuid}).fetchone()

    if not entity:
        raise HTTPException(status_code=404, detail="共享实体不存在或已过期")

    if password is not None and entity.password is not None and entity.password != password:
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
        "status": doc.status,
        "author": doc.author_login,
        "creationDate": int(doc.creationdate.timestamp() * 1000) if doc.creationdate else None,
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
        "status": part.status,
        "author": part.author_login,
        "creationDate": int(part.creationdate.timestamp() * 1000) if part.creationdate else None,
    }

"""标签端点（TagResource）。

GET/POST /workspaces/{ws}/tags
POST     /workspaces/{ws}/tags/multiple
DELETE   /workspaces/{ws}/tags/{tagId}
GET/POST /workspaces/{ws}/tags/{tagId}/documents
"""
from typing import List
from fastapi import APIRouter, Depends, Body
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.auth import Account
from app.models.part import Tag
from app.services.document_manager import DocumentService
from app.services.part_mapper import map_revision as map_part_revision

router = APIRouter(prefix="/docdoku-plm-server-rest/api")
doc_svc = DocumentService()


def _build_doc_dto(dr, db: Session, current_user_login=None) -> dict:
    """组装文档修订版 DTO，使用统一的 _doc_to_dict 确保字段完整。"""
    from app.routers.document import _doc_to_dict
    return _doc_to_dict(db, dr, current_user_login)


@router.get("/workspaces/{workspace_id}/tags")
@router.get("/workspaces/{workspace_id}/tags/", include_in_schema=False)
def get_tags(
    workspace_id: str,
    current_user: Account = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取工作空间中所有标签。"""
    tags = db.query(Tag).filter(Tag.workspace_id == workspace_id).all()
    return [{"id": t.label, "label": t.label, "workspaceId": workspace_id} for t in tags]


@router.post("/workspaces/{workspace_id}/tags", status_code=201)
@router.post("/workspaces/{workspace_id}/tags/", status_code=201, include_in_schema=False)
def create_tag(
    workspace_id: str,
    body: dict = Body(...),
    current_user: Account = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """创建单个标签。"""
    label = body.get("label", body.get("id", ""))
    existing = db.query(Tag).filter(
        Tag.workspace_id == workspace_id, Tag.label == label
    ).first()
    if existing is None:
        db.add(Tag(workspace_id=workspace_id, label=label))
        db.commit()
    return {"id": label, "label": label, "workspaceId": workspace_id}


@router.post("/workspaces/{workspace_id}/tags/multiple", status_code=201)
@router.post("/workspaces/{workspace_id}/tags/multiple/", status_code=201, include_in_schema=False)
def create_tags(
    workspace_id: str,
    body: list = Body(...),
    current_user: Account = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """批量创建标签。"""
    created = []
    for item in body:
        label = item.get("label", item.get("id", "")) if isinstance(item, dict) else str(item)
        existing = db.query(Tag).filter(
            Tag.workspace_id == workspace_id, Tag.label == label
        ).first()
        if existing is None:
            db.add(Tag(workspace_id=workspace_id, label=label))
            created.append(label)
    db.commit()
    return [{"id": lbl, "label": lbl, "workspaceId": workspace_id} for lbl in created]


@router.delete("/workspaces/{workspace_id}/tags/{tag_id}", status_code=204)
@router.delete("/workspaces/{workspace_id}/tags/{tag_id}/", status_code=204, include_in_schema=False)
def delete_tag(
    workspace_id: str,
    tag_id: str,
    current_user: Account = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除标签。"""
    tag = db.query(Tag).filter(
        Tag.workspace_id == workspace_id, Tag.label == tag_id
    ).first()
    if tag is not None:
        db.delete(tag)
        db.commit()
    return Response(status_code=204)


@router.get("/workspaces/{workspace_id}/tags/{tag_id}/documents")
@router.get("/workspaces/{workspace_id}/tags/{tag_id}/documents/", include_in_schema=False)
def get_documents_by_tag(
    workspace_id: str,
    tag_id: str,
    current_user: Account = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取带有指定标签的所有文档修订版。"""
    from app.models.document import DocumentRevision, document_revision_tags
    revisions = db.query(DocumentRevision).join(
        document_revision_tags,
        (DocumentRevision.workspace_id == document_revision_tags.c.documentmaster_workspace_id)
        & (DocumentRevision.documentmaster_id == document_revision_tags.c.documentmaster_id)
        & (DocumentRevision.version == document_revision_tags.c.documentrevision_version)
    ).filter(
        DocumentRevision.workspace_id == workspace_id,
        document_revision_tags.c.tag_label == tag_id,
    ).all()
    return [_build_doc_dto(dr, db, current_user.login) for dr in revisions]


@router.post("/workspaces/{workspace_id}/tags/{tag_id}/documents", status_code=201)
@router.post("/workspaces/{workspace_id}/tags/{tag_id}/documents/", status_code=201, include_in_schema=False)
def create_document_in_root_with_tag(
    workspace_id: str,
    tag_id: str,
    body: dict = Body(...),
    current_user: Account = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """在根文件夹创建文档并打上标签（对标 Java createDocumentMasterInRootFolderWithTag）。"""
    doc_id = body.get("reference", body.get("id", ""))
    title = body.get("title", "")
    template_id = body.get("templateId")
    workflow_model_id = body.get("workflowModelId")

    dr = doc_svc.create_document(
        db, workspace_id, doc_id, title, current_user.login,
        folder_path=workspace_id,
        template_id=template_id,
        workflow_model_id=workflow_model_id,
    )
    # 打标签
    _ensure_tag(db, workspace_id, tag_id)
    doc_svc.add_tag(db, workspace_id, dr.documentmaster_id, dr.version, tag_id)

    return _build_doc_dto(dr, db, current_user.login)


def _ensure_tag(db: Session, ws: str, label: str) -> None:
    existing = db.query(Tag).filter(
        Tag.workspace_id == ws, Tag.label == label
    ).first()
    if existing is None:
        db.add(Tag(workspace_id=ws, label=label))
        db.flush()

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
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.auth import Account
from app.services.document_manager import DocumentService

router = APIRouter(prefix="/docdoku-plm-server-rest/api")
doc_svc = DocumentService()


@router.get("/workspaces/{workspace_id}/tags")
@router.get("/workspaces/{workspace_id}/tags/", include_in_schema=False)
def get_tags(
    workspace_id: str,
    current_user: Account = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取工作空间中所有标签。"""
    return doc_svc.get_all_tags(db, workspace_id)


@router.post("/workspaces/{workspace_id}/tags", status_code=200)
@router.post("/workspaces/{workspace_id}/tags/", status_code=200, include_in_schema=False)
def create_tag(
    workspace_id: str,
    body: dict = Body(...),
    current_user: Account = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """创建单个标签。"""
    label = body.get("label", body.get("id", ""))
    return doc_svc.create_tag(db, workspace_id, label)


@router.post("/workspaces/{workspace_id}/tags/multiple", status_code=204)
@router.post("/workspaces/{workspace_id}/tags/multiple/", status_code=204, include_in_schema=False)
def create_tags(
    workspace_id: str,
    body: dict = Body(...),
    current_user: Account = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """批量创建标签（对齐 Java TagResource.createTags：TagListDTO{tags:[TagDTO]} → 204）。"""
    items = body.get("tags", []) if isinstance(body, dict) else (body or [])
    labels = []
    for item in items:
        label = item.get("label", item.get("id", "")) if isinstance(item, dict) else str(item)
        if label:
            labels.append(label)
    doc_svc.create_tags_batch(db, workspace_id, labels)
    return Response(status_code=204)


@router.delete("/workspaces/{workspace_id}/tags/{tag_id}", status_code=204)
@router.delete("/workspaces/{workspace_id}/tags/{tag_id}/", status_code=204, include_in_schema=False)
def delete_tag(
    workspace_id: str,
    tag_id: str,
    current_user: Account = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除标签（先清关联表再删 tag，避免 FK 约束错误）。"""
    doc_svc.delete_tag(db, workspace_id, tag_id)
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
    return doc_svc.get_documents_by_tag(db, workspace_id, tag_id, current_user.login)


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
    return doc_svc.create_document_in_root_with_tag(db, workspace_id, body, tag_id, current_user.login)

"""零件模板端点（PartTemplateResource）。"""
import re
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Body
from fastapi.responses import Response
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.auth import Account
from app.models.part import PartMaster, PartMasterTemplate
from app.services.acl_helper import apply_acl

router = APIRouter(prefix="/docdoku-plm-server-rest/api")


def _mask_to_sql_like(mask: str) -> str:
    """将 mask 转换为 SQL LIKE 模式，# → _（单数字），* → _（单字符），转义 _ 和 %。"""
    result = []
    for ch in mask:
        if ch == '#':
            result.append('_')
        elif ch == '*':
            result.append('_')
        elif ch == '_':
            result.append('\\_')
        elif ch == '%':
            result.append('\\%')
        else:
            result.append(ch)
    return ''.join(result)


def _parse_id_with_mask(id_str: str, mask: str) -> str | None:
    """检查 id_str 是否匹配 mask 模式，匹配则返回变量部分。"""
    if len(id_str) != len(mask):
        return None
    variable_chars = []
    for i, (mch, ich) in enumerate(zip(mask, id_str)):
        if mch == '#':
            if not ich.isdigit():
                return None
            variable_chars.append(ich)
        elif mch == '*':
            if not ich.isalnum():
                return None
            variable_chars.append(ich)
        elif mch != ich:
            return None
    return ''.join(variable_chars)


def _increment_masked_value(value: str, mask: str) -> str | None:
    """递增 mask 变量部分的值，返回完整的下一个 ID。"""
    mask_vars = [(i, ch) for i, ch in enumerate(mask) if ch in ('#', '*')]
    if not mask_vars:
        return None

    # 从最后一个可变字符开始进位
    result = list(value)
    for pos, mch in reversed(mask_vars):
        if result[pos] == '9' if mch == '#' else result[pos] == 'Z':
            result[pos] = '0' if mch == '#' else 'A'
            continue
        c = result[pos]
        if mch == '#':
            result[pos] = chr(ord(c) + 1)
        else:
            result[pos] = chr(ord(c) + 1)
            if result[pos] > 'Z' and result[pos] < 'a':
                result[pos] = 'a'
        break
    else:
        # 全部溢出，无法递增
        return None
    return ''.join(result)


def _first_id_from_mask(mask: str) -> str:
    """从 mask 生成第一个 ID。# 位初始为 0，* 位初始为 A。"""
    result = []
    for ch in mask:
        if ch == '#':
            result.append('0')
        elif ch == '*':
            result.append('A')
        else:
            result.append(ch)
    return ''.join(result)


def _generate_from_mask(db: Session, workspace_id: str, mask: str) -> str:
    """使用 mask 查询已有零件编号并递增。"""
    like_pattern = _mask_to_sql_like(mask)

    # 查匹配 mask 的已有编号
    rows = (
        db.query(PartMaster.number)
        .filter(PartMaster.workspace_id == workspace_id,
                PartMaster.number.like(like_pattern))
        .order_by(PartMaster.number.desc())
        .limit(50)
        .all()
    )

    last_valid = None
    for (number,) in rows:
        val = _parse_id_with_mask(number, mask)
        if val is not None:
            last_valid = number
            break

    if last_valid is not None:
        new_id = _increment_masked_value(last_valid, mask)
        if new_id is not None:
            return new_id
        # 溢出回退：用第一位字符递增
        return _first_id_from_mask(mask)

    return _first_id_from_mask(mask)


def _generate_from_template_id(db: Session, workspace_id: str, template_id: str) -> str:
    """无 mask 时用 template_id 前缀 + 递增序号。"""
    rows = (
        db.query(PartMaster.number)
        .filter(PartMaster.workspace_id == workspace_id,
                PartMaster.number.like(f"{template_id}%"))
        .all()
    )

    max_seq = 0
    seq_re = re.compile(rf'^{re.escape(template_id)}-(\d+)$')
    for (number,) in rows:
        m = seq_re.match(number)
        if m:
            max_seq = max(max_seq, int(m.group(1)))

    return f"{template_id}-{max_seq + 1:03d}"


@router.get("/workspaces/{workspace_id}/part-templates")
@router.get("/workspaces/{workspace_id}/part-templates/", include_in_schema=False)
def list_part_templates(workspace_id: str,
                        current_user: Account = Depends(get_current_user),
                        db: Session = Depends(get_db)):
    templates = (
        db.query(PartMasterTemplate)
        .filter(PartMasterTemplate.workspace_id == workspace_id)
        .all()
    )
    result = []
    for t in templates:
        result.append({
            "id": t.id,
            "workspaceId": t.workspace_id,
            "mask": t.mask,
            "idGenerated": t.id_generated,
            "partType": t.part_type,
            "attributesLocked": t.attributes_locked,
            "authorLogin": t.author_login,
            "authorWorkspaceId": t.author_workspace_id,
            "creationDate": t.creation_date.isoformat() if t.creation_date else None,
            "modificationDate": t.modification_date.isoformat() if t.modification_date else None,
            "aclId": t.acl_id,
            "workflowModelId": t.workflowmodel_id,
        })
    return result


@router.get("/workspaces/{workspace_id}/part-templates/{template_id}")
@router.get("/workspaces/{workspace_id}/part-templates/{template_id}/", include_in_schema=False)
def get_part_template(workspace_id: str, template_id: str,
                      current_user: Account = Depends(get_current_user),
                      db: Session = Depends(get_db)):
    t = (
        db.query(PartMasterTemplate)
        .filter(PartMasterTemplate.workspace_id == workspace_id,
                PartMasterTemplate.id == template_id)
        .first()
    )
    if t is None:
        raise HTTPException(404, f"Template {template_id} not found")
    return {
        "id": t.id,
        "workspaceId": t.workspace_id,
        "mask": t.mask,
        "idGenerated": t.id_generated,
        "partType": t.part_type,
        "attributesLocked": t.attributes_locked,
        "authorLogin": t.author_login,
        "authorWorkspaceId": t.author_workspace_id,
        "creationDate": t.creation_date.isoformat() if t.creation_date else None,
        "modificationDate": t.modification_date.isoformat() if t.modification_date else None,
        "aclId": t.acl_id,
        "workflowModelId": t.workflowmodel_id,
    }


@router.post("/workspaces/{workspace_id}/part-templates", status_code=201)
@router.post("/workspaces/{workspace_id}/part-templates/", status_code=201, include_in_schema=False)
def create_part_template(workspace_id: str,
                         body: dict = Body(...),
                         current_user: Account = Depends(get_current_user),
                         db: Session = Depends(get_db)):
    t = PartMasterTemplate(
        id=body.get("id", ""),
        workspace_id=workspace_id,
        mask=body.get("mask", ""),
        id_generated=body.get("idGenerated", False),
        part_type=body.get("partType", ""),
        attributes_locked=body.get("attributesLocked", False),
        author_login=current_user.login,
        author_workspace_id=workspace_id,
        creation_date=datetime.utcnow(),
        modification_date=datetime.utcnow(),
        acl_id=body.get("aclId"),
        workflowmodel_id=body.get("workflowModelId"),
    )
    db.add(t)
    db.commit()
    return {
        "id": t.id,
        "workspaceId": t.workspace_id,
        "mask": t.mask,
        "idGenerated": t.id_generated,
        "partType": t.part_type,
        "attributesLocked": t.attributes_locked,
        "authorLogin": t.author_login,
        "authorWorkspaceId": t.author_workspace_id,
        "creationDate": t.creation_date.isoformat() if t.creation_date else None,
        "modificationDate": t.modification_date.isoformat() if t.modification_date else None,
        "aclId": t.acl_id,
        "workflowModelId": t.workflowmodel_id,
    }


@router.put("/workspaces/{workspace_id}/part-templates/{template_id}")
@router.put("/workspaces/{workspace_id}/part-templates/{template_id}/", include_in_schema=False)
def update_part_template(workspace_id: str, template_id: str,
                         body: dict = Body(...),
                         current_user: Account = Depends(get_current_user),
                         db: Session = Depends(get_db)):
    t = (
        db.query(PartMasterTemplate)
        .filter(PartMasterTemplate.workspace_id == workspace_id,
                PartMasterTemplate.id == template_id)
        .first()
    )
    if t is None:
        raise HTTPException(404, f"Template {template_id} not found")
    if "mask" in body:
        t.mask = body["mask"]
    if "idGenerated" in body:
        t.id_generated = body["idGenerated"]
    if "partType" in body:
        t.part_type = body["partType"]
    if "attributesLocked" in body:
        t.attributes_locked = body["attributesLocked"]
    if "workflowModelId" in body:
        t.workflowmodel_id = body["workflowModelId"]
    t.modification_date = datetime.utcnow()
    db.commit()
    return {
        "id": t.id,
        "workspaceId": t.workspace_id,
        "mask": t.mask,
        "idGenerated": t.id_generated,
        "partType": t.part_type,
        "attributesLocked": t.attributes_locked,
        "authorLogin": t.author_login,
        "authorWorkspaceId": t.author_workspace_id,
        "creationDate": t.creation_date.isoformat() if t.creation_date else None,
        "modificationDate": t.modification_date.isoformat() if t.modification_date else None,
        "aclId": t.acl_id,
        "workflowModelId": t.workflowmodel_id,
    }


@router.delete("/workspaces/{workspace_id}/part-templates/{template_id}", status_code=204)
@router.delete("/workspaces/{workspace_id}/part-templates/{template_id}/", status_code=204, include_in_schema=False)
def delete_part_template(workspace_id: str, template_id: str,
                         current_user: Account = Depends(get_current_user),
                         db: Session = Depends(get_db)):
    t = (
        db.query(PartMasterTemplate)
        .filter(PartMasterTemplate.workspace_id == workspace_id,
                PartMasterTemplate.id == template_id)
        .first()
    )
    if t is None:
        raise HTTPException(404, f"Template {template_id} not found")
    db.delete(t)
    db.commit()
    return Response(status_code=204)


@router.get("/workspaces/{workspace_id}/part-templates/{template_id}/generate_id")
@router.get("/workspaces/{workspace_id}/part-templates/{template_id}/generate_id/", include_in_schema=False)
def generate_part_id(workspace_id: str, template_id: str,
                     current_user: Account = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    t = (
        db.query(PartMasterTemplate)
        .filter(PartMasterTemplate.workspace_id == workspace_id,
                PartMasterTemplate.id == template_id)
        .first()
    )
    if t is None:
        raise HTTPException(404, f"Template {template_id} not found")

    mask = t.mask
    if mask:
        generated = _generate_from_mask(db, workspace_id, mask)
    else:
        generated = _generate_from_template_id(db, workspace_id, template_id)

    return {"generatedId": generated}


@router.put("/workspaces/{workspace_id}/part-templates/{template_id}/acl")
@router.put("/workspaces/{workspace_id}/part-templates/{template_id}/acl/", include_in_schema=False)
def update_part_template_acl(workspace_id: str, template_id: str,
                             body: dict = Body(...),
                             current_user: Account = Depends(get_current_user),
                             db: Session = Depends(get_db)):
    t = (
        db.query(PartMasterTemplate)
        .filter(PartMasterTemplate.workspace_id == workspace_id,
                PartMasterTemplate.id == template_id)
        .first()
    )
    if t is None:
        raise HTTPException(404, f"Template {template_id} not found")
    user_entries = body.get("userEntries", {})
    group_entries = body.get("groupEntries", {})
    new_acl_id = apply_acl(db, t.acl_id, user_entries, group_entries)
    if t.acl_id != new_acl_id:
        t.acl_id = new_acl_id
        db.commit()
    return {"aclId": new_acl_id}

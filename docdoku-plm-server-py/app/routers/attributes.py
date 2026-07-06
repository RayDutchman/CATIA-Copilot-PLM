"""属性端点（AttributesResource）。

GET /workspaces/{ws}/attributes/part-iterations
GET /workspaces/{ws}/attributes/path-data
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.auth import Account

router = APIRouter(prefix="/docdoku-plm-server-rest/api")


def _filter_attributes(rows) -> list[dict]:
    """按 (name, attributeType) 去重，剥离 value/mandatory/locked。"""
    seen: set[str] = set()
    result = []
    for row in rows:
        key = f"{row.name}|{row.attributetype}"
        if key in seen:
            continue
        seen.add(key)
        result.append({
            "name": row.name,
            "attributeType": row.attributetype,
            "lovName": row.lov_name,
        })
    return result


@router.get("/workspaces/{workspace_id}/attributes/part-iterations")
@router.get("/workspaces/{workspace_id}/attributes/part-iterations/", include_in_schema=False)
def get_part_iterations_attributes(
    workspace_id: str,
    current_user: Account = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取工作空间中所有零件迭代版本上的实例属性（去重后只返回属性定义）。"""
    rows = db.execute(text(
        """
        SELECT DISTINCT ia.name, ia.dtype, ia.attributetype, ia.lov_name
        FROM instanceattribute ia
        JOIN partiteration_attr pia ON pia.instanceattribute_id = ia.id
        JOIN partiteration pi ON (
            pi.workspace_id = pia.workspace_id
            AND pi.partmaster_partnumber = pia.partmaster_partnumber
            AND pi.partrevision_version = pia.partrevision_version
            AND pi.iteration = pia.iteration
        )
        WHERE pi.workspace_id = :ws
        ORDER BY ia.name
        """
    ), {"ws": workspace_id}).fetchall()
    return _filter_attributes(rows)


@router.get("/workspaces/{workspace_id}/attributes/path-data")
@router.get("/workspaces/{workspace_id}/attributes/path-data/", include_in_schema=False)
def get_path_data_attributes(
    workspace_id: str,
    current_user: Account = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取工作空间中所有路径数据（PathData）上的实例属性（去重后只返回属性定义）。"""
    rows = db.execute(text(
        """
        SELECT DISTINCT ia.name, ia.dtype, ia.attributetype, ia.lov_name
        FROM instanceattribute ia
        JOIN pathdataiteration_attr pdia ON pdia.instanceattribute_id = ia.id
        JOIN pathdataiteration pdi ON (
            pdi.workspace_id = pdia.workspace_id
            AND pdi.configurationitem_id = pdia.configurationitem_id
            AND pdi.serialnumber = pdia.serialnumber
            AND pdi.pathdatamaster_id = pdia.pathdatamaster_id
            AND pdi.iteration = pdia.iteration
        )
        WHERE pdi.workspace_id = :ws
        ORDER BY ia.name
        """
    ), {"ws": workspace_id}).fetchall()
    return _filter_attributes(rows)

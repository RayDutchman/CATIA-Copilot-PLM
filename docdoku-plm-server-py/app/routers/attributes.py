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

# InstanceAttribute 单表继承的 dtype 判别符 → InstanceAttributeType 枚举
# 对齐 Java InstanceAttributeDozerConverter 的 instanceof 映射
_DTYPE_TO_ATTR_TYPE = {
    "InstanceBooleanAttribute": "BOOLEAN",
    "InstanceTextAttribute": "TEXT",
    "InstanceNumberAttribute": "NUMBER",
    "InstanceDateAttribute": "DATE",
    "InstanceURLAttribute": "URL",
    "InstanceListOfValuesAttribute": "LOV",
    "InstanceLongTextAttribute": "LONG_TEXT",
    "InstancePartNumberAttribute": "PART_NUMBER",
}


def _filter_attributes(rows) -> list[dict]:
    """按 (attributeType, name) 去重，只返回属性定义（对齐 Java filterAttributes 清空 value/mandatory/locked/lovName）。"""
    seen: set[str] = set()
    result = []
    for row in rows:
        attribute_type = _DTYPE_TO_ATTR_TYPE.get(row.dtype)
        key = f"{attribute_type}|{row.name}"
        if key in seen:
            continue
        seen.add(key)
        result.append({
            "name": row.name,
            "attributeType": attribute_type,
            "lovName": None,
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
        SELECT DISTINCT ia.name, ia.dtype
        FROM instanceattribute ia
        JOIN partiteration_attribute pia ON pia.instanceattribute_id = ia.id
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
        SELECT DISTINCT ia.name, ia.dtype
        FROM instanceattribute ia
        JOIN pathdataiteration_attribute pdia ON pdia.instanceattribute_id = ia.id
        JOIN prdinstiteration_pathdatamstr pipm ON pipm.pathdatamaster_id = pdia.pathdatamaster_id
        WHERE pipm.workspace_id = :ws
        ORDER BY ia.name
        """
    ), {"ws": workspace_id}).fetchall()
    return _filter_attributes(rows)

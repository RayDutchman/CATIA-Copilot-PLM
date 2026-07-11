"""实例体写入工具（对标 InstanceBodyWriterTools — 递归遍历装配树 + 矩阵组合 + JSON 流生成）。

使用 fastapi.responses.StreamingResponse 配合 generator 实现 JSON 数组流式输出。
"""
import math
import json
import logging
from dataclasses import dataclass
from typing import Iterator
from sqlalchemy.orm import Session

_logger = logging.getLogger(__name__)


@dataclass
class Matrix4:
    """4x4 变换矩阵（对齐 Java javax.vecmath.Matrix4d）。"""
    m: list[list[float]]

    def __init__(self, data: list[list[float]] | None = None):
        if data and len(data) == 4 and all(len(r) == 4 for r in data):
            self.m = [r[:] for r in data]
        else:
            self.m = [[1.0, 0, 0, 0], [0, 1.0, 0, 0], [0, 0, 1.0, 0], [0, 0, 0, 1.0]]

    def set_identity(self):
        self.m = [[1.0, 0, 0, 0], [0, 1.0, 0, 0], [0, 0, 1.0, 0], [0, 0, 0, 1.0]]

    def set_translation(self, x: float, y: float, z: float):
        self.m[0][3] = x
        self.m[1][3] = y
        self.m[2][3] = z

    def rot_x(self, rad: float):
        c, s = math.cos(rad), math.sin(rad)
        self.m = [
            [1, 0, 0, 0],
            [0, c, -s, 0],
            [0, s, c, 0],
            [0, 0, 0, 1],
        ]

    def rot_y(self, rad: float):
        c, s = math.cos(rad), math.sin(rad)
        self.m = [
            [c, 0, s, 0],
            [0, 1, 0, 0],
            [-s, 0, c, 0],
            [0, 0, 0, 1],
        ]

    def rot_z(self, rad: float):
        c, s = math.cos(rad), math.sin(rad)
        self.m = [
            [c, -s, 0, 0],
            [s, c, 0, 0],
            [0, 0, 1, 0],
            [0, 0, 0, 1],
        ]

    def mul(self, other: "Matrix4") -> "Matrix4":
        result = Matrix4()
        for i in range(4):
            for j in range(4):
                result.m[i][j] = sum(self.m[i][k] * other.m[k][j] for k in range(4))
        return result

    def to_list(self) -> list[float]:
        return [self.m[i][j] for i in range(4) for j in range(4)]


def combine_translation_rotation(matrix: Matrix4, tx: float, ty: float, tz: float,
                                  rx: float, ry: float, rz: float) -> Matrix4:
    """组合平移 + ZYX 欧拉角旋转。"""
    gM = Matrix4(matrix.m)
    # 平移
    tm = Matrix4()
    tm.set_translation(tx, ty, tz)
    gM = gM.mul(tm)
    # 旋转 Z → Y → X
    rm = Matrix4()
    rm.rot_z(math.radians(rz))
    gM = gM.mul(rm)
    rm.rot_y(math.radians(ry))
    gM = gM.mul(rm)
    rm.rot_x(math.radians(rx))
    gM = gM.mul(rm)
    return gM


def combine_matrix(matrix: Matrix4, transformation: Matrix4) -> Matrix4:
    return matrix.mul(transformation)


def generate_instance_stream(
    output_stream,
    workspace_id: str,
    configuration_item_id: str,
    filter_dict: dict | None = None,
    db_session: Session | None = None,
) -> Iterator[bytes]:
    """生成产品实例 JSON 流（SSE 风格的逐行 JSON 数组）。

    Args:
        output_stream: 回调写入器 (ignored in generator mode)
        workspace_id: 工作空间 ID
        configuration_item_id: 配置项 ID
        filter_dict: PSFilter 描述
        db_session: SQLAlchemy 会话

    Yields:
        逐行 JSON 文本字节流
    """
    yield b"[\n"

    # 遍历产品结构树（待对接 PSFilterVisitor）
    from app.services.product_structure import product_structure_service
    from app.models.part import CADInstance
    from app.models.product.part_revision import PartRevision

    db = db_session
    if db is None:
        from app.core.database import SessionLocal
        db = SessionLocal()

    try:
        comps = product_structure_service.filter_product_structure(
            db, workspace_id, configuration_item_id, config_spec=filter_dict, depth=None,
        )
        if not comps:
            yield b"]"
            return

        identity = Matrix4()
        root = comps[0] if isinstance(comps, list) else comps
        yield from _write_assembly_leaf(db, root, [], identity)
    finally:
        if db_session is None and db:
            db.close()

    yield b"\n]"


def _write_assembly_leaf(db: Session, component: dict, instance_ids: list[int],
                          matrix: Matrix4) -> Iterator[bytes]:
    """递归写出装配树叶子节点 JSON。"""
    from app.models.product.cad_instance import CADInstance
    from app.models.product.part_iteration import PartIteration

    pn = component.get("number", "")
    path = component.get("path", "")
    it_num = component.get("iteration", 0)

    # 查找 CADInstances（如有）
    it = db.query(PartIteration).filter(
        PartIteration.workspace_id == component.get("workspace_id", ""),
        PartIteration.partmaster_partnumber == pn,
        PartIteration.partrevision_version == component.get("version", ""),
        PartIteration.iteration == it_num,
    ).first()

    cad_instances = []
    if it:
        cad_rows = db.execute(
            __import__("sqlalchemy").text(
                "SELECT ci.* FROM cadinstance ci "
                "JOIN usage_link_cadinstances ulc ON ulc.cadinstance_id = ci.id "
                "JOIN partusagelink pul ON pul.id = ulc.usage_link_id "
                "WHERE pul.component_workspace_id = :ws "
                "AND pul.component_partnumber = :pn"
            ),
            {"ws": component.get("workspace_id", ""), "pn": pn},
        ).fetchall()
        cad_instances = [dict(r._mapping) for r in cad_rows]

    for inst in cad_instances or [{"id": 0, "tx": 0, "ty": 0, "tz": 0, "rx": 0, "ry": 0, "rz": 0}]:
        copy_ids = list(instance_ids) + [inst.get("id", 0)]
        combined = combine_translation_rotation(
            matrix,
            float(inst.get("tx", 0) or 0),
            float(inst.get("ty", 0) or 0),
            float(inst.get("tz", 0) or 0),
            float(inst.get("rx", 0) or 0),
            float(inst.get("ry", 0) or 0),
            float(inst.get("rz", 0) or 0),
        )

        if component.get("assembly"):
            for child in component.get("components", []):
                yield from _write_assembly_leaf(db, child, copy_ids, combined)
        else:
            obj = {
                "id": path,
                "partIterationId": f"{pn}-{component.get('version', 'A')}-{it_num}",
                "path": path,
                "matrix": combined.to_list(),
                "qualities": 0,
                "xMin": 0, "yMin": 0, "zMin": 0,
                "xMax": 0, "yMax": 0, "zMax": 0,
                "files": [],
                "attributes": [],
            }
            yield json.dumps(obj).encode() + b",\n"

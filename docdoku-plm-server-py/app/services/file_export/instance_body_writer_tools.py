"""实例体写入工具（对标 InstanceBodyWriterTools — 递归遍历装配树 + 矩阵组合 + JSON 流生成）。

两个入口：
  collect_leaf_instances() — 按 PartIteration ORM 对象递归收集，返回 list[dict]（part.py instances 端点用）
  generate_instance_stream()  — PSFilterVisitor + generator 流式输出（virtual_instance_collection 用）
"""
import math
import json
import logging
from dataclasses import dataclass
from typing import Iterator, Optional
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
                "JOIN partusagelink_cadinstance ulc ON ulc.cadinstance_id = ci.id "
                "JOIN partusagelink pul ON pul.id = ulc.partusagelink_id "
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


# ── PartIteration ORM 递归遍历（part.py instances 端点用） ──────────────────


def identity_matrix() -> list[float]:
    """返回 4×4 单位矩阵（行主序）。"""
    return [
        1.0, 0, 0, 0,
        0, 1.0, 0, 0,
        0, 0, 1.0, 0,
        0, 0, 0, 1.0,
    ]


def multiply_matrices(a: list[float], b: list[float]) -> list[float]:
    """4×4 行主序矩阵乘法：result = a × b"""
    result = [0.0] * 16
    for i in range(4):
        for j in range(4):
            result[i * 4 + j] = sum(
                a[i * 4 + k] * b[k * 4 + j] for k in range(4)
            )
    return result


def cad_instance_local_matrix(ci) -> list[float]:
    """从 CADInstance ORM 对象构造局部 4×4 行主序变换矩阵（平移 + 旋转）。

    支持 rotation_type='ANGLE'（rx/ry/rz 欧拉角 ZYX）和 'MATRIX'（m00-m22）。
    """
    from app.models.product.cad_instance import CADInstance
    m = identity_matrix()

    if ci and ci.rotation_type == "MATRIX":
        if ci.m00 is not None:
            m[0] = ci.m00;  m[1] = ci.m01;  m[2] = ci.m02
            m[4] = ci.m10;  m[5] = ci.m11;  m[6] = ci.m12
            m[8] = ci.m20;  m[9] = ci.m21;  m[10] = ci.m22
    elif ci and ci.rotation_type == "ANGLE":
        rz = math.radians(ci.rz or 0)
        ry = math.radians(ci.ry or 0)
        rx = math.radians(ci.rx or 0)
        cx, sx = math.cos(rx), math.sin(rx)
        cy, sy = math.cos(ry), math.sin(ry)
        cz, sz = math.cos(rz), math.sin(rz)
        m[0] = cy * cz;  m[1] = sx * sy * cz - cx * sz;  m[2] = cx * sy * cz + sx * sz
        m[4] = cy * sz;  m[5] = sx * sy * sz + cx * cz;  m[6] = cx * sy * sz - sx * cz
        m[8] = -sy;      m[9] = sx * cy;                  m[10] = cx * cy

    m[3] = ci.tx or 0
    m[7] = ci.ty or 0
    m[11] = ci.tz or 0
    return m


def collect_leaf_instances(
    db: Session,
    pi,  # PartIteration
    parent_matrix: list[float],
    instance_ids: list[int],
    result: list[dict],
) -> None:
    """递归遍历装配树，收集叶子零件实例。

    - 叶子节点（无子组件且有几何体）→ 调用 write_leaf_instance 输出
    - 装配节点 → 遍历每个 PartLink × CADInstance，递归处理子组件
    """
    from app.models.product.part_iteration import PartIteration
    from app.models.product.part_usage_link import PartUsageLink

    geometries = sorted(pi.geometries or [], key=lambda g: g.quality or 0)

    if not geometries and not pi.components:
        return

    if geometries and not pi.components:
        write_leaf_instance(pi, parent_matrix, instance_ids, geometries, result)
        return

    if pi.components:
        for link in pi.components:
            link_id = link.id
            cad_instances = link.cad_instances or []

            if not cad_instances:
                _handle_child_component(
                    db, link, identity_matrix(),
                    instance_ids + [link_id], result,
                )
            else:
                for ci in cad_instances:
                    local = cad_instance_local_matrix(ci)
                    combined = multiply_matrices(parent_matrix, local)
                    _handle_child_component(
                        db, link, combined,
                        instance_ids + [link_id], result,
                    )

        if geometries:
            write_leaf_instance(pi, parent_matrix, instance_ids, geometries, result)


def _handle_child_component(
    db: Session,
    link,  # PartUsageLink
    combined_matrix: list[float],
    instance_ids: list[int],
    result: list[dict],
) -> None:
    """查找子组件的最新已签入迭代，递归收集。"""
    from app.models.product.part_iteration import PartIteration
    child_pi = db.query(PartIteration).filter(
        PartIteration.workspace_id == link.component_workspace_id,
        PartIteration.partmaster_partnumber == link.component_partnumber,
    ).order_by(PartIteration.iteration.desc()).first()

    if child_pi:
        collect_leaf_instances(db, child_pi, combined_matrix, instance_ids, result)


def write_leaf_instance(
    pi,  # PartIteration
    matrix: list[float],
    instance_ids: list[int],
    geometries,  # list[BinaryResource] (sorted by quality)
    result: list[dict],
) -> None:
    """将叶子零件的几何信息写入实例 JSON（对齐 Java InstanceBodyWriterTools.writeLeaf）。"""
    from app.models.part import BinaryResource

    id_str = "-".join(str(i) for i in instance_ids)

    # path 格式对齐 Java Tools.getPathAsString（linkId-pair 编码）
    path_parts = []
    for i in range(0, len(instance_ids) - 1, 2):
        if i + 1 < len(instance_ids):
            path_parts.append(f"{instance_ids[i]}-{instance_ids[i+1]}")
        else:
            path_parts.append(str(instance_ids[i]))
    path = "-".join(path_parts) if path_parts else str(instance_ids[-1])

    first = geometries[0]
    files = [{"fullName": f"api/files/{g.full_name}"} for g in geometries]

    instance = {
        "id": id_str,
        "partIterationId": f"{pi.workspace_id}-{pi.partmaster_partnumber}-{pi.partrevision_version}-{pi.iteration}",
        "path": path,
        "matrix": matrix,
        "qualities": len(geometries),
        "xMin": first.x_min or 0.0,
        "yMin": first.y_min or 0.0,
        "zMin": first.z_min or 0.0,
        "xMax": first.x_max or 0.0,
        "yMax": first.y_max or 0.0,
        "zMax": first.z_max or 0.0,
        "files": files,
        "attributes": [],
    }
    result.append(instance)

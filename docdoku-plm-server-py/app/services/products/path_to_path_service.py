"""PathToPathLink Service。

对齐 Payara ProductManagerBean 和 ProductInstanceManagerBean 的 PathToPathLink 方法。

- CI 级操作（create/update/delete/getTypes/getFromSourceTarget）对应 ProductManagerBean
- 实例级操作（getLinks/getTypes/getRoots 按 serialNumber）对应 ProductInstanceManagerBean
"""
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import text


class PathToPathLinkService:
    """PathToPathLink CRUD + 环检测。"""

    # ─────────────────────────────────────────
    # CI 级查询
    # ─────────────────────────────────────────

    def get_link_types_for_ci(self, db: Session, ws: str, ci_id: str) -> List[str]:
        """获取 CI 的所有 link 类型（去重）。"""
        rows = db.execute(text(
            "SELECT DISTINCT ppl.type "
            "FROM pathtopathlink ppl "
            "JOIN configurationitem_p2plink cp "
            "  ON cp.pathtopathlink_id = ppl.id "
            "WHERE cp.workspace_id = :ws AND cp.configurationitem_id = :ci"
        ), {"ws": ws, "ci": ci_id}).fetchall()
        return [r[0] for r in rows if r[0]]

    def get_links_for_ci(self, db: Session, ws: str, ci_id: str) -> list:
        """获取 CI 的所有 PathToPathLink。"""
        rows = db.execute(text(
            "SELECT ppl.id, ppl.type, ppl.sourcepath, ppl.targetpath, ppl.description "
            "FROM pathtopathlink ppl "
            "JOIN configurationitem_p2plink cp "
            "  ON cp.pathtopathlink_id = ppl.id "
            "WHERE cp.workspace_id = :ws AND cp.configurationitem_id = :ci"
        ), {"ws": ws, "ci": ci_id}).fetchall()
        return [self._link_row_to_dict(r) for r in rows]

    def get_link_by_id(self, db: Session, link_id: int) -> Optional[dict]:
        """按 ID 加载单个 PathToPathLink。"""
        row = db.execute(text(
            "SELECT id, type, sourcepath, targetpath, description "
            "FROM pathtopathlink WHERE id = :id"
        ), {"id": link_id}).first()
        return self._link_row_to_dict(row) if row else None

    def get_links_from_source_and_target(self, db: Session, ws: str, ci_id: str,
                                          source: str, target: str) -> list:
        """按 sourcePath + targetPath 筛选（CI 级）。"""
        rows = db.execute(text(
            "SELECT ppl.id, ppl.type, ppl.sourcepath, ppl.targetpath, ppl.description "
            "FROM pathtopathlink ppl "
            "JOIN configurationitem_p2plink cp "
            "  ON cp.pathtopathlink_id = ppl.id "
            "WHERE cp.workspace_id = :ws AND cp.configurationitem_id = :ci "
            "  AND ppl.sourcepath = :src AND ppl.targetpath = :tgt"
        ), {"ws": ws, "ci": ci_id, "src": source, "tgt": target}).fetchall()
        return [self._link_row_to_dict(r) for r in rows]

    # ─────────────────────────────────────────
    # 实例级查询
    # ─────────────────────────────────────────

    def get_link_types_for_instance(self, db: Session, ws: str,
                                     ci_id: str, sn: str) -> List[str]:
        """获取产品实例的所有 link 类型（通过 prdinstiteration_p2plink）。"""
        rows = db.execute(text(
            "SELECT DISTINCT ppl.type "
            "FROM pathtopathlink ppl "
            "JOIN prdinstiteration_p2plink pip "
            "  ON pip.pathtopathlink_id = ppl.id "
            "WHERE pip.workspace_id = :ws "
            "  AND pip.configurationitem_id = :ci "
            "  AND pip.prdinstancemaster_serialnumber = :sn"
        ), {"ws": ws, "ci": ci_id, "sn": sn}).fetchall()
        return [r[0] for r in rows if r[0]]

    def get_links_for_instance(self, db: Session, ws: str,
                                ci_id: str, sn: str) -> list:
        """获取产品实例的所有 PathToPathLink（通过 prdinstiteration_p2plink）。"""
        rows = db.execute(text(
            "SELECT DISTINCT ppl.id, ppl.type, ppl.sourcepath, ppl.targetpath, ppl.description "
            "FROM pathtopathlink ppl "
            "JOIN prdinstiteration_p2plink pip "
            "  ON pip.pathtopathlink_id = ppl.id "
            "WHERE pip.workspace_id = :ws "
            "  AND pip.configurationitem_id = :ci "
            "  AND pip.prdinstancemaster_serialnumber = :sn"
        ), {"ws": ws, "ci": ci_id, "sn": sn}).fetchall()
        return [self._link_row_to_dict(r) for r in rows]

    def get_links_from_source_and_target_for_instance(self, db: Session, ws: str,
                                                        ci_id: str, sn: str,
                                                        source: str, target: str) -> list:
        """按 sourcePath + targetPath 筛选（实例级）。"""
        rows = db.execute(text(
            "SELECT DISTINCT ppl.id, ppl.type, ppl.sourcepath, ppl.targetpath, ppl.description "
            "FROM pathtopathlink ppl "
            "JOIN prdinstiteration_p2plink pip "
            "  ON pip.pathtopathlink_id = ppl.id "
            "WHERE pip.workspace_id = :ws "
            "  AND pip.configurationitem_id = :ci "
            "  AND pip.prdinstancemaster_serialnumber = :sn "
            "  AND ppl.sourcepath = :src AND ppl.targetpath = :tgt"
        ), {"ws": ws, "ci": ci_id, "sn": sn, "src": source, "tgt": target}).fetchall()
        return [self._link_row_to_dict(r) for r in rows]

    def get_root_links_for_instance(self, db: Session, ws: str,
                                     ci_id: str, sn: str, link_type: str) -> list:
        """获取指定类型的根 PathToPathLink（其 sourcePath 不是其他 link 的 targetPath）。"""
        all_links = self.get_links_for_instance(db, ws, ci_id, sn)
        target_paths = {lk["targetPath"] for lk in all_links if lk.get("targetPath")}
        roots = [
            lk for lk in all_links
            if lk.get("type") == link_type
            and lk.get("sourcePath") not in target_paths
        ]
        return roots

    # ─────────────────────────────────────────
    # CI 级 CRUD
    # ─────────────────────────────────────────

    def create_path_to_path_link(self, db: Session, ws: str, ci_id: str,
                                  link_type: str, path_from: str, path_to: str,
                                  description: str) -> dict:
        """创建 PathToPathLink（含环检测）。

        对齐 Java ProductManagerBean.createPathToPathLink：
        1. pathFrom != pathTo 校验（pathFrom==pathTo → NotAllowedException57）
        2. decodePath() 验证路径有效性（无效路径 → PartUsageLinkNotFoundException）
        3. 重复检测（同 type+source+target 已存在 → PathToPathLinkAlreadyExistsException）
        4. INSERT + CI 关联
        5. DFS 环检测（发现环 → PathToPathCyclicException + rollback）
        """
        from app.core.exceptions import (
            NotAllowedException,
            PathToPathLinkAlreadyExistsException,
            PathToPathCyclicException,
        )

        # pathFrom == pathTo：对齐 Java NotAllowedException57
        if path_from == path_to:
            raise NotAllowedException("NotAllowedException57")

        # decodePath() 路径验证：对齐 Java createPathToPathLink 在 INSERT 前调用 decodePath
        # 路径格式 "-1-u2-u5"，decode_path 接受 "u2-u5"（去掉 "-1-" 前缀）
        self._validate_path(db, ws, ci_id, path_from)
        self._validate_path(db, ws, ci_id, path_to)

        # 重复检测
        existing = db.execute(text(
            "SELECT ppl.id FROM pathtopathlink ppl "
            "JOIN configurationitem_p2plink cp ON cp.pathtopathlink_id = ppl.id "
            "WHERE cp.workspace_id = :ws AND cp.configurationitem_id = :ci "
            "  AND ppl.sourcepath = :src AND ppl.targetpath = :tgt "
            "  AND ppl.type = :t"
        ), {"ws": ws, "ci": ci_id, "src": path_from, "tgt": path_to, "t": link_type}).first()
        if existing:
            raise PathToPathLinkAlreadyExistsException(
                "PathToPathLinkAlreadyExistsException",
                f"{path_from}->{path_to}"
            )

        # 创建 link
        result = db.execute(text(
            "INSERT INTO pathtopathlink (type, sourcepath, targetpath, description) "
            "VALUES (:t, :src, :tgt, :desc) RETURNING id"
        ), {"t": link_type, "src": path_from, "tgt": path_to, "desc": description or ""})
        link_id = result.fetchone()[0]

        # 挂到 CI
        db.execute(text(
            "INSERT INTO configurationitem_p2plink "
            "(configurationitem_id, workspace_id, pathtopathlink_id) "
            "VALUES (:ci, :ws, :lid) ON CONFLICT DO NOTHING"
        ), {"ci": ci_id, "ws": ws, "lid": link_id})

        db.flush()  # 使 link 可被后续查询看到

        # DFS 环检测——任何异常均回滚（包括 DB 错误）
        new_link = {"id": link_id, "type": link_type,
                    "sourcePath": path_from, "targetPath": path_to,
                    "description": description}
        visited = []
        try:
            self._check_cyclic(db, ws, ci_id, new_link, visited)
        except Exception:
            db.rollback()
            raise

        db.commit()
        return new_link

    def update_path_to_path_link(self, db: Session, ws: str, ci_id: str,
                                  link_id: int, description: str) -> dict:
        """更新 PathToPathLink 的 description（对齐 Java：只允许改 description）。"""
        from app.core.exceptions import PathToPathLinkNotFoundException

        # 验证 link 属于此 CI
        row = db.execute(text(
            "SELECT ppl.id FROM pathtopathlink ppl "
            "JOIN configurationitem_p2plink cp ON cp.pathtopathlink_id = ppl.id "
            "WHERE cp.workspace_id = :ws AND cp.configurationitem_id = :ci "
            "  AND ppl.id = :lid"
        ), {"ws": ws, "ci": ci_id, "lid": link_id}).first()
        if not row:
            raise PathToPathLinkNotFoundException("PathToPathLinkNotFoundException", str(link_id))

        db.execute(text(
            "UPDATE pathtopathlink SET description = :desc WHERE id = :id"
        ), {"desc": description or "", "id": link_id})
        db.commit()

        return self.get_link_by_id(db, link_id)

    def delete_path_to_path_link(self, db: Session, ws: str, ci_id: str,
                                  link_id: int) -> None:
        """删除 PathToPathLink（移除 CI 关联 + 删除 link 记录）。"""
        from app.core.exceptions import PathToPathLinkNotFoundException

        # 验证存在
        row = db.execute(text(
            "SELECT ppl.id FROM pathtopathlink ppl "
            "JOIN configurationitem_p2plink cp ON cp.pathtopathlink_id = ppl.id "
            "WHERE cp.workspace_id = :ws AND cp.configurationitem_id = :ci "
            "  AND ppl.id = :lid"
        ), {"ws": ws, "ci": ci_id, "lid": link_id}).first()
        if not row:
            raise PathToPathLinkNotFoundException("PathToPathLinkNotFoundException", str(link_id))

        # 移除关联
        db.execute(text(
            "DELETE FROM configurationitem_p2plink "
            "WHERE workspace_id = :ws AND configurationitem_id = :ci "
            "AND pathtopathlink_id = :lid"
        ), {"ws": ws, "ci": ci_id, "lid": link_id})

        # 删除 link 本体
        db.execute(text("DELETE FROM pathtopathlink WHERE id = :id"), {"id": link_id})
        db.commit()

    # ─────────────────────────────────────────
    # 路径验证
    # ─────────────────────────────────────────

    def _validate_path(self, db: Session, ws: str, ci_id: str, path_str: str):
        """验证路径字符串有效性，无效时抛 PartUsageLinkNotFoundException。

        对齐 Java ProductManagerBean.decodePath() 在创建 P2P link 前的调用。
        路径格式："-1-u2-u5"；decode_path 接受 "u2-u5"（去掉 "-1-" 前缀或 "-1" 根节点）。
        """
        from app.core.exceptions import PartUsageLinkNotFoundException
        from app.services.product_structure import ProductStructureService

        if not path_str:
            return  # 空路径不验证（根节点情况）

        # 去掉 "-1" 或 "-1-" 前缀，得到 "u2-u5" 格式
        stripped = path_str.lstrip("-")  # 去掉前导 "-"
        if stripped.startswith("1-"):
            stripped = stripped[2:]  # 去掉 "1-"
        elif stripped == "1":
            return  # 只有根节点，无 link，不验证

        if not stripped:
            return

        # decode_path 会在遇到不存在的 link id 时抛 PartUsageLinkNotFoundException
        svc = ProductStructureService()
        try:
            svc.decode_path(db, ws, ci_id, stripped)
        except PartUsageLinkNotFoundException:
            raise
        except Exception as e:
            # CI 不存在等其他错误也视为路径无效
            raise PartUsageLinkNotFoundException("PartUsageLinkNotFoundException", path_str) from e

    # ─────────────────────────────────────────
    # 环检测（DFS，对齐 Java checkCyclicPathToPathLink）
    # ─────────────────────────────────────────

    def _check_cyclic(self, db: Session, ws: str, ci_id: str,
                       start_link: dict, visited: list):
        """DFS 环检测。

        从 start_link 出发，沿 targetPath → 匹配其他 link 的 sourcePath 递归遍历。
        若发现已经访问过的 link，抛 PathToPathCyclicException。
        """
        from app.core.exceptions import PathToPathCyclicException

        # 找以 start_link.targetPath 为 sourcePath 的下一批 links
        next_rows = db.execute(text(
            "SELECT ppl.id, ppl.type, ppl.sourcepath, ppl.targetpath, ppl.description "
            "FROM pathtopathlink ppl "
            "JOIN configurationitem_p2plink cp ON cp.pathtopathlink_id = ppl.id "
            "WHERE cp.workspace_id = :ws AND cp.configurationitem_id = :ci "
            "  AND ppl.sourcepath = :target_path"
        ), {"ws": ws, "ci": ci_id, "target_path": start_link.get("targetPath", "")}).fetchall()

        for row in next_rows:
            next_link = self._link_row_to_dict(row)
            if any(v["id"] == next_link["id"] for v in visited):
                raise PathToPathCyclicException("PathToPathCyclicException", "cycle detected")
            visited.append(next_link)
            self._check_cyclic(db, ws, ci_id, next_link, visited)

    # ─────────────────────────────────────────
    # 辅助
    # ─────────────────────────────────────────

    def _link_row_to_dict(self, row) -> dict:
        """将 DB 行转换为 PathToPathLinkDTO dict（对齐 Java DTO 字段）。"""
        return {
            "id": row[0],
            "type": row[1],
            "sourcePath": row[2],
            "targetPath": row[3],
            "description": row[4],
            "sourceComponents": [],
            "targetComponents": [],
        }


path_to_path_service = PathToPathLinkService()

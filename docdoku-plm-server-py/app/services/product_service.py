"""零件业务逻辑服务：CRUD、签出签入、装配同步。"""
from datetime import datetime
from typing import Optional
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.models.part import (
    PartMaster, PartRevision, PartIteration,
    PartUsageLink, CADInstance, Conversion,
    part_iteration_usagelink, usage_link_cadinstances,
)
from app.schemas.part import PartCreationDTO, PartIterationUpdateDTO


class ProductService:

    # ── 查询 ──────────────────────────────────────────────────

    def list_revisions(self, db: Session, workspace_id: str,
                       start: int = 0, length: int = 50) -> list:
        return (
            db.query(PartRevision)
            .filter(PartRevision.workspace_id == workspace_id)
            .order_by(PartRevision.partmaster_partnumber, PartRevision.version)
            .offset(start).limit(length).all()
        )

    def count_parts(self, db: Session, workspace_id: str) -> int:
        return (
            db.query(PartMaster)
            .filter(
                PartMaster.workspace_id == workspace_id,
                PartMaster.revisions.any(),
            )
            .count()
        )

    def get_revision(self, db: Session, workspace_id: str,
                     number: str, version: str) -> PartRevision:
        pr = (
            db.query(PartRevision)
            .filter(
                PartRevision.workspace_id == workspace_id,
                PartRevision.partmaster_partnumber == number,
                PartRevision.version == version,
            )
            .first()
        )
        if pr is None:
            raise HTTPException(status_code=404,
                                detail=f"Part {number}-{version} not found")
        return pr

    def get_latest_revision(self, db: Session, workspace_id: str,
                            number: str) -> PartRevision:
        master = (
            db.query(PartMaster)
            .filter(PartMaster.workspace_id == workspace_id,
                    PartMaster.number == number)
            .first()
        )
        if master is None or not master.revisions:
            raise HTTPException(status_code=404,
                                detail=f"Part {number} not found")
        return master.last_revision

    def search_numbers(self, db: Session, workspace_id: str,
                       q: str, limit: int = 8) -> list:
        pattern = f"%{q}%"
        return (
            db.query(PartMaster)
            .filter(
                PartMaster.workspace_id == workspace_id,
                PartMaster.number.ilike(pattern),
            )
            .limit(limit).all()
        )

    def list_checked_out(self, db: Session, workspace_id: str) -> list:
        return (
            db.query(PartRevision)
            .filter(
                PartRevision.workspace_id == workspace_id,
                PartRevision.checkout_user_login.isnot(None),
            )
            .all()
        )

    def get_conversion(self, db: Session, workspace_id: str,
                       number: str, version: str, iteration: int
                       ) -> Optional[Conversion]:
        return (
            db.query(Conversion)
            .filter(
                Conversion.workspace_id == workspace_id,
                Conversion.partmaster_partnumber == number,
                Conversion.partrevision_version == version,
                Conversion.iteration == iteration,
            )
            .first()
        )

    def create_conversion(self, db: Session, ws: str, pn: str,
                          ver: str, iteration: int) -> Conversion:
        """建 pending Conversion（已存在则复用并重置为 pending）。"""
        conv = self.get_conversion(db, ws, pn, ver, iteration)
        now = datetime.utcnow()
        if conv is None:
            conv = Conversion(
                workspace_id=ws, partmaster_partnumber=pn,
                partrevision_version=ver, iteration=iteration,
                pending=True, succeed=False, start_date=now,
            )
            db.add(conv)
        else:
            conv.pending = True
            conv.succeed = False
            conv.start_date = now
            conv.end_date = None
        db.flush()
        return conv

    # ── 辅助 ──────────────────────────────────────────────────

    def find_or_create_part_master(self, db: Session,
                                   workspace_id: str, number: str) -> PartMaster:
        master = (
            db.query(PartMaster)
            .filter(PartMaster.workspace_id == workspace_id,
                    PartMaster.number == number)
            .first()
        )
        if master is None:
            master = PartMaster(
                workspace_id=workspace_id,
                number=number,
                creation_date=datetime.utcnow(),
            )
            db.add(master)
            db.flush()
        return master

    def _next_version(self, current: str) -> str:
        if not current:
            return "A"
        last_char = current[-1]
        if last_char == "Z":
            return current + "A"
        return current[:-1] + chr(ord(last_char) + 1)

    # ── 写操作 ────────────────────────────────────────────────

    def create_part(self, db: Session, workspace_id: str,
                    creator_login: str, body: PartCreationDTO) -> PartRevision:
        from app.core.exceptions import EntityAlreadyExistsException
        # 检查零件号唯一性
        existing = (
            db.query(PartMaster)
            .filter(PartMaster.workspace_id == workspace_id,
                    PartMaster.number == body.number)
            .first()
        )
        if existing:
            raise EntityAlreadyExistsException(
                "PartMasterAlreadyExistsException", body.number)
        now = datetime.utcnow()
        # 创建 PartMaster
        master = PartMaster(
            workspace_id=workspace_id,
            number=body.number,
            name=body.name,
            standard_part=body.standard_part,
            creation_date=now,
            author_workspace_id=workspace_id,
            author_login=creator_login,
        )
        db.add(master)
        db.flush()
        # 创建首个 PartRevision（版本 A）
        revision = PartRevision(
            workspace_id=workspace_id,
            partmaster_partnumber=body.number,
            version="A",
            description=body.description,
            status=0,
            creation_date=now,
            author_workspace_id=workspace_id,
            author_login=creator_login,
            checkout_user_workspace_id=workspace_id,
            checkout_user_login=creator_login,
            check_out_date=now,
        )
        db.add(revision)
        db.flush()
        # 创建首个 PartIteration（iteration=1）
        iteration = PartIteration(
            workspace_id=workspace_id,
            partmaster_partnumber=body.number,
            partrevision_version="A",
            iteration=1,
            creation_date=now,
            author_workspace_id=workspace_id,
            author_login=creator_login,
        )
        db.add(iteration)
        db.commit()
        db.refresh(revision)
        return revision

    def delete_revision(self, db: Session, workspace_id: str,
                        number: str, version: str, user_login: str) -> None:
        from app.core.exceptions import EntityConstraintException
        pr = self.get_revision(db, workspace_id, number, version)
        if pr.checkout_user_login and pr.checkout_user_login != user_login:
            raise HTTPException(403, "Part is checked out by another user")
        if pr.status == 1:
            raise HTTPException(403, "Cannot delete a released revision")
        # 被用作组件（对齐 Payara EntityConstraintException2）
        used_as_component = (
            db.query(PartUsageLink)
            .filter(PartUsageLink.component_workspace_id == workspace_id,
                    PartUsageLink.component_partnumber == number)
            .count()
        )
        if used_as_component > 0:
            raise EntityConstraintException("EntityConstraintException2")

        from sqlalchemy import text

        # EntityConstraintException1: 配置项根零件（P3 已落地）
        is_root = db.execute(
            text("SELECT COUNT(*) FROM configurationitem "
                 "WHERE partmaster_workspace_id=:ws AND partmaster_partnumber=:pn"),
            {"ws": workspace_id, "pn": number},
        ).scalar()
        if is_root:
            raise EntityConstraintException("EntityConstraintException1")

        # EntityConstraintException22: 被用作替代品（P3 已落地）
        is_substitute = db.execute(
            text("SELECT COUNT(*) FROM partsubstitutelink "
                 "WHERE substitute_workspace_id=:ws AND substitute_partnumber=:pn"),
            {"ws": workspace_id, "pn": number},
        ).scalar()
        if is_substitute:
            raise EntityConstraintException("EntityConstraintException22")

        # EntityConstraintException5: 已在基线中（P3 已落地）
        is_baselined = db.execute(
            text("SELECT COUNT(*) FROM baselinedpart "
                 "WHERE target_workspace_id=:ws AND target_partmaster_partnumber=:pn "
                 "AND target_partrevision_version=:ver"),
            {"ws": workspace_id, "pn": number, "ver": version},
        ).scalar()
        if is_baselined:
            raise EntityConstraintException("EntityConstraintException5")

        # EntityConstraintException21: 已分配到变更项（P4 已落地）
        has_change_item = db.execute(
            text("SELECT 1 FROM changeissue_affected_part "
                 "WHERE partmaster_workspace_id=:ws AND partmaster_partnumber=:pn "
                 "UNION ALL SELECT 1 FROM changeorder_affected_part "
                 "WHERE partmaster_workspace_id=:ws AND partmaster_partnumber=:pn "
                 "UNION ALL SELECT 1 FROM changereq_affected_part "
                 "WHERE partmaster_workspace_id=:ws AND partmaster_partnumber=:pn "
                 "LIMIT 1"),
            {"ws": workspace_id, "pn": number},
        ).scalar()
        if has_change_item is not None:
            raise EntityConstraintException("EntityConstraintException21")

        if pr.tags:
            pr.tags[:] = []
        for it in pr.iterations:
            # 清理 modificationnotification 引用（FK 到 partiteration）
            db.execute(
                text("DELETE FROM modificationnotification "
                     "WHERE impacted_workspace_id=:ws "
                     "AND impacted_partmaster_partnumber=:pn "
                     "AND impacted_partrevision_version=:ver "
                     "AND impacted_iteration=:it"),
                {"ws": workspace_id, "pn": number, "ver": version, "it": it.iteration},
            )
            if it.conversions:
                it.conversions[:] = []
            if it.attached_files:
                it.attached_files[:] = []
            if it.geometries:
                it.geometries[:] = []
        db.delete(pr)
        db.commit()

    def checkout(self, db: Session, workspace_id: str,
                 number: str, version: str, user_login: str) -> PartRevision:
        from app.core.exceptions import NotAllowedException
        pr = self.get_revision(db, workspace_id, number, version)
        if pr.checkout_user_login:
            raise NotAllowedException("NotAllowedException37")
        if pr.status != 0:
            raise NotAllowedException("NotAllowedException47")
        now = datetime.utcnow()
        pr.checkout_user_login = user_login
        pr.checkout_user_workspace_id = workspace_id
        pr.check_out_date = now
        # 新建迭代（iteration+1）
        last_iter = pr.last_iteration_number
        new_iter = PartIteration(
            workspace_id=workspace_id,
            partmaster_partnumber=number,
            partrevision_version=version,
            iteration=last_iter + 1,
            creation_date=now,
            author_workspace_id=workspace_id,
            author_login=user_login,
        )
        db.add(new_iter)
        db.commit()
        db.refresh(pr)
        return pr

    def checkin(self, db: Session, workspace_id: str,
                number: str, version: str, user_login: str) -> PartRevision:
        from app.core.exceptions import NotAllowedException
        pr = self.get_revision(db, workspace_id, number, version)
        if pr.checkout_user_login != user_login:
            raise NotAllowedException("NotAllowedException20")
        now = datetime.utcnow()
        # 标记最新迭代为已签入
        last = pr.last_iteration
        if last:
            last.check_in_date = now
        # 清空签出信息
        pr.checkout_user_login = None
        pr.checkout_user_workspace_id = None
        pr.check_out_date = None
        db.commit()
        db.refresh(pr)
        return pr

    def undo_checkout(self, db: Session, workspace_id: str,
                      number: str, version: str, user_login: str) -> PartRevision:
        from app.core.exceptions import NotAllowedException
        pr = self.get_revision(db, workspace_id, number, version)
        if pr.checkout_user_login != user_login:
            raise NotAllowedException("NotAllowedException19")
        if len(pr.iterations) <= 1:
            raise NotAllowedException("NotAllowedException41")
        # 删除未签入的最新迭代
        last = pr.last_iteration
        if last and last.check_in_date is None:
            db.delete(last)
        pr.checkout_user_login = None
        pr.checkout_user_workspace_id = None
        pr.check_out_date = None
        db.commit()
        db.refresh(pr)
        return pr

    def update_iteration(self, db: Session, workspace_id: str,
                         number: str, version: str, iteration_num: int,
                         user_login: str,
                         body: PartIterationUpdateDTO) -> PartRevision:
        from app.core.exceptions import NotAllowedException
        pr = self.get_revision(db, workspace_id, number, version)
        if pr.checkout_user_login != user_login:
            raise NotAllowedException("NotAllowedException25", number)
        # 找目标迭代
        target = next(
            (it for it in pr.iterations if it.iteration == iteration_num), None
        )
        if target is None:
            raise HTTPException(404, f"Iteration {iteration_num} not found")
        now = datetime.utcnow()
        target.modification_date = now
        if body.iterationNote is not None:
            target.iteration_note = body.iterationNote
        # 更新子件列表
        if body.components is not None:
            self._sync_components(db, target, body.components, workspace_id)
        db.commit()
        db.refresh(pr)
        return pr

    def _sync_components(self, db: Session, iteration: PartIteration,
                          components_dto: list, workspace_id: str) -> None:
        # 注意：高并发下同一 iteration 同时更新可能导致孤儿记录，
        # 未来多用户场景需加 SELECT ... FOR UPDATE 保护
        # 收集旧 link id，清理关联后删除孤儿 PartUsageLink
        old_link_ids = [
            row[0] for row in db.execute(
                part_iteration_usagelink.select().with_only_columns(
                    part_iteration_usagelink.c.component_id
                ).where(
                    part_iteration_usagelink.c.workspace_id == iteration.workspace_id,
                    part_iteration_usagelink.c.partmaster_partnumber == iteration.partmaster_partnumber,
                    part_iteration_usagelink.c.partrevision_version == iteration.partrevision_version,
                    part_iteration_usagelink.c.iteration == iteration.iteration,
                )
            )
        ]
        # 清空旧关联
        db.execute(
            part_iteration_usagelink.delete().where(
                part_iteration_usagelink.c.workspace_id == iteration.workspace_id,
                part_iteration_usagelink.c.partmaster_partnumber == iteration.partmaster_partnumber,
                part_iteration_usagelink.c.partrevision_version == iteration.partrevision_version,
                part_iteration_usagelink.c.iteration == iteration.iteration,
            )
        )
        # 删除孤儿 PartUsageLink（关联表 partusagelink_cadinstance 会自动级联清理）
        if old_link_ids:
            db.query(PartUsageLink).filter(
                PartUsageLink.id.in_(old_link_ids)
            ).delete(synchronize_session=False)
        for order, comp_dto in enumerate(components_dto):
            comp_number = comp_dto.component.number if comp_dto.component else None
            if not comp_number:
                continue
            # 确保子件 PartMaster 存在
            self.find_or_create_part_master(db, workspace_id, comp_number)
            # 创建 PartUsageLink
            link = PartUsageLink(
                amount=comp_dto.amount,
                comment=comp_dto.comment,
                optional=comp_dto.optional,
                reference_description=comp_dto.referenceDescription,
                unit=comp_dto.unit,
                component_workspace_id=workspace_id,
                component_partnumber=comp_number,
            )
            db.add(link)
            db.flush()
            # 处理 CAD 实例
            for cad_dto in (comp_dto.cadInstances or []):
                cad = CADInstance(
                    rotation_type=cad_dto.rotationType,
                    rx=cad_dto.rx, ry=cad_dto.ry, rz=cad_dto.rz,
                    tx=cad_dto.tx, ty=cad_dto.ty, tz=cad_dto.tz,
                    m00=cad_dto.m00, m01=cad_dto.m01, m02=cad_dto.m02,
                    m10=cad_dto.m10, m11=cad_dto.m11, m12=cad_dto.m12,
                    m20=cad_dto.m20, m21=cad_dto.m21, m22=cad_dto.m22,
                )
                db.add(cad)
                db.flush()
                db.execute(
                    usage_link_cadinstances.insert().values(
                        partusagelink_id=link.id,
                        cadinstance_id=cad.id,
                    )
                )
            # 建立迭代→链接关联
            db.execute(
                part_iteration_usagelink.insert().values(
                    workspace_id=iteration.workspace_id,
                    partmaster_partnumber=iteration.partmaster_partnumber,
                    partrevision_version=iteration.partrevision_version,
                    iteration=iteration.iteration,
                    component_id=link.id,
                    component_order=order,
                )
            )

    def release(self, db: Session, ws: str, pn: str, ver: str,
                user_login: str) -> PartRevision:
        from app.core.exceptions import NotAllowedException
        pr = self.get_revision(db, ws, pn, ver)
        if pr.checkout_user_login:
            raise NotAllowedException("NotAllowedException46")
        if not pr.iterations:
            raise NotAllowedException("NotAllowedException41")
        if pr.status == 2:
            raise NotAllowedException("NotAllowedException38")
        pr.status = 1
        pr.release_date = datetime.utcnow()
        pr.release_user_login = user_login
        pr.release_user_workspace = ws
        db.commit()
        db.refresh(pr)
        return pr

    def mark_obsolete(self, db: Session, ws: str, pn: str, ver: str,
                      user_login: str) -> PartRevision:
        from app.core.exceptions import NotAllowedException
        pr = self.get_revision(db, ws, pn, ver)
        if pr.status != 1:
            raise NotAllowedException("NotAllowedException36")
        pr.status = 2
        pr.obsolete_date = datetime.utcnow()
        pr.obsolete_user_login = user_login
        pr.obsolete_user_workspace = ws
        db.commit()
        db.refresh(pr)
        return pr

    def create_new_version(self, db: Session, ws: str, pn: str, ver: str,
                           user_login: str) -> PartRevision:
        from app.core.exceptions import NotAllowedException
        pr = self.get_revision(db, ws, pn, ver)
        if pr.checkout_user_login:
            raise NotAllowedException("NotAllowedException40")
        if not pr.iterations:
            raise NotAllowedException("NotAllowedException41")
        now = datetime.utcnow()
        new_ver = self._next_version(ver)
        new_pr = PartRevision(
            workspace_id=ws, partmaster_partnumber=pn, version=new_ver,
            description=pr.description, status=0, creation_date=now,
            author_workspace_id=ws, author_login=user_login,
            checkout_user_workspace_id=ws, checkout_user_login=user_login,
            check_out_date=now,
        )
        db.add(new_pr)
        db.flush()
        db.add(PartIteration(
            workspace_id=ws, partmaster_partnumber=pn,
            partrevision_version=new_ver, iteration=1,
            creation_date=now, author_workspace_id=ws, author_login=user_login,
        ))
        db.commit()
        db.refresh(new_pr)
        return new_pr

    def _ensure_tag(self, db: Session, ws: str, label: str) -> None:
        from app.models.part import Tag
        t = db.query(Tag).filter(Tag.workspace_id == ws,
                                 Tag.label == label).first()
        if t is None:
            db.add(Tag(workspace_id=ws, label=label))
            db.flush()

    def set_tags(self, db: Session, ws: str, pn: str, ver: str,
                 labels: list) -> PartRevision:
        from app.models.part import part_revision_tags
        pr = self.get_revision(db, ws, pn, ver)
        db.execute(part_revision_tags.delete().where(
            part_revision_tags.c.partmaster_workspace_id == ws,
            part_revision_tags.c.partmaster_partnumber == pn,
            part_revision_tags.c.partrevision_version == ver,
        ))
        for label in labels:
            self._ensure_tag(db, ws, label)
            db.execute(part_revision_tags.insert().values(
                partmaster_workspace_id=ws, partmaster_partnumber=pn,
                partrevision_version=ver, tag_workspace_id=ws, tag_label=label,
            ))
        db.commit()
        db.refresh(pr)
        return pr

    def add_tag(self, db: Session, ws: str, pn: str, ver: str,
                label: str) -> PartRevision:
        from app.models.part import part_revision_tags
        pr = self.get_revision(db, ws, pn, ver)
        self._ensure_tag(db, ws, label)
        exists = db.execute(part_revision_tags.select().where(
            part_revision_tags.c.partmaster_workspace_id == ws,
            part_revision_tags.c.partmaster_partnumber == pn,
            part_revision_tags.c.partrevision_version == ver,
            part_revision_tags.c.tag_label == label,
        )).first()
        if exists is None:
            db.execute(part_revision_tags.insert().values(
                partmaster_workspace_id=ws, partmaster_partnumber=pn,
                partrevision_version=ver, tag_workspace_id=ws, tag_label=label,
            ))
        db.commit()
        db.refresh(pr)
        return pr

    def remove_tag(self, db: Session, ws: str, pn: str, ver: str,
                   label: str) -> PartRevision:
        from app.models.part import part_revision_tags
        pr = self.get_revision(db, ws, pn, ver)
        db.execute(part_revision_tags.delete().where(
            part_revision_tags.c.partmaster_workspace_id == ws,
            part_revision_tags.c.partmaster_partnumber == pn,
            part_revision_tags.c.partrevision_version == ver,
            part_revision_tags.c.tag_label == label,
        ))
        db.commit()
        db.refresh(pr)
        return pr

    def search_parts(self, db: Session, ws: str, name=None,
                     number=None, type_=None) -> list:
        q = db.query(PartMaster).filter(PartMaster.workspace_id == ws)
        if name:
            q = q.filter(PartMaster.name.ilike(f"%{name}%"))
        if number:
            q = q.filter(PartMaster.number.ilike(f"%{number}%"))
        if type_:
            q = q.filter(PartMaster.type.ilike(f"%{type_}%"))
        masters = q.limit(100).all()
        result = []
        for m in masters:
            result.extend(m.revisions)
        return result

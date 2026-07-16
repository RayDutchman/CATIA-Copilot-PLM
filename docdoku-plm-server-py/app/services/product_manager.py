"""零件业务逻辑服务：CRUD、签出签入、装配同步。"""
from datetime import datetime
from pathlib import Path
from typing import Optional
from sqlalchemy.orm import Session
from app.core.exceptions import (
    AccessRightException, EntityConstraintException,
    EntityNotFoundException, NotAllowedException,
    PartMasterNotFoundException, PartRevisionNotFoundException,
    PartIterationNotFoundException,
    WorkspaceNotEnabledException, WrongInputException,
)
from app.models.part import (
    PartMaster, PartRevision, PartIteration,
    PartUsageLink, CADInstance, Conversion,
    BinaryResource,
    part_iteration_usagelink, usage_link_cadinstances,
)
from app.schemas.part import PartCreationDTO, PartIterationUpdateDTO
from app.services.indexer_manager import indexer_manager


def _validate_mask(mask: str, value: str) -> bool:
    """验证给定值是否匹配掩码（*匹配字母数字，#匹配数字）。"""
    if not mask:
        return True
    if len(mask) != len(value):
        return False
    import re
    alphanum = re.compile(r'[a-zA-Z0-9]')
    for mc, vc in zip(mask, value):
        if mc == '*' and not alphanum.match(vc):
            return False
        if mc == '#' and not vc.isdigit():
            return False
    return True


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
            db.query(PartRevision)
            .filter(PartRevision.workspace_id == workspace_id)
            .count()
        )

    def get_revision(self, db: Session, workspace_id: str,
                     number: str, version: str,
                     for_update: bool = False,
                     current_user_login: str = None) -> PartRevision:
        if current_user_login:
            self._check_workspace_member(db, workspace_id, current_user_login)
        q = (
            db.query(PartRevision)
            .filter(
                PartRevision.workspace_id == workspace_id,
                PartRevision.partmaster_partnumber == number,
                PartRevision.version == version,
            )
        )
        if for_update:
            q = q.with_for_update()
        pr = q.first()
        if pr is None:
            raise EntityNotFoundException("PartRevisionNotFoundException", number, version)
        # 数据泄漏保护：签出状态对其他用户隐藏最新迭代
        if (not for_update and pr.checkout_user_login
                and current_user_login
                and pr.checkout_user_login != current_user_login):
            db.expunge(pr)
            if list(pr.iterations):
                pr.iterations.remove(pr.iterations[-1])
        return pr

    def get_latest_revision(self, db: Session, workspace_id: str,
                            number: str,
                            current_user_login: str = None,
                            is_admin: bool = False) -> PartRevision:
        master = (
            db.query(PartMaster)
            .filter(PartMaster.workspace_id == workspace_id,
                    PartMaster.number == number)
            .first()
        )
        if master is None or not master.revisions:
            raise PartMasterNotFoundException("PartMasterNotFoundException", number)
        pr = master.last_revision
        if current_user_login:
            self._check_workspace_member(db, workspace_id, current_user_login)
            # ACL 读权限检查（对齐 Java checkPartRevisionReadAccess → hasPartRevisionReadAccess）
            from app.services.factory.acl_factory import check_read_access
            if not check_read_access(db, pr.acl_id, current_user_login, is_admin, workspace_id):
                raise AccessRightException("AccessRightException", current_user_login)
        return pr

    def search_numbers(self, db: Session, workspace_id: str,
                       q: str, limit: int = 8,
                       current_user_login: str = None) -> list:
        if current_user_login:
            self._check_workspace_member(db, workspace_id, current_user_login)
        from sqlalchemy import or_
        pattern = f"%{q}%"
        return (
            db.query(PartMaster)
            .filter(
                PartMaster.workspace_id == workspace_id,
                or_(PartMaster.number.ilike(pattern),
                    PartMaster.name.ilike(pattern)),
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

    def _check_workspace_member(self, db: Session, workspace_id: str,
                                 login: str) -> None:
        from sqlalchemy import text
        # 检查 workspace 是否启用
        enabled = db.execute(text(
            "SELECT enabled FROM workspace WHERE id = :ws"
        ), {"ws": workspace_id}).scalar()
        if enabled is None or not enabled:
            raise WorkspaceNotEnabledException(
                "WorkspaceNotEnabledException", workspace_id)
        row = db.execute(text(
            "SELECT 1 FROM userdata WHERE login = :l AND workspace_id = :w"
        ), {"l": login, "w": workspace_id}).first()
        if not row:
            raise AccessRightException("AccessRightException", login)

    def _next_version(self, current: str) -> str:
        if not current:
            return "A"
        chars = list(current)
        for i in range(len(chars) - 1, -1, -1):
            if chars[i] == 'Z':
                chars[i] = 'A'
            else:
                chars[i] = chr(ord(chars[i]) + 1)
                return ''.join(chars)
        return 'A' + ''.join(chars)

    # ── 写操作 ────────────────────────────────────────────────

    def create_part(self, db: Session, workspace_id: str,
                    creator_login: str, body: PartCreationDTO) -> PartRevision:
        from app.core.exceptions import EntityAlreadyExistsException, PartRevisionAlreadyExistsException
        from app.services.factory.acl_factory import apply_acl, check_write_access, parse_acl_entries
        from sqlalchemy import text as sql_text
        # workspace 写权限检查（对齐 Java checkWorkspaceWriteAccess）
        if not check_write_access(db, None, creator_login, False, workspace_id=workspace_id):
            raise AccessRightException("AccessRightException", creator_login)
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
        # 模板处理：设置 type 和 attributes_locked
        if body.template_id:
            from app.models.product.part_master_template import PartMasterTemplate
            tpl = (
                db.query(PartMasterTemplate)
                .filter(PartMasterTemplate.workspace_id == workspace_id,
                        PartMasterTemplate.id == body.template_id)
                .first()
            )
            if tpl is None:
                from app.core.exceptions import PartMasterTemplateNotFoundException
                raise PartMasterTemplateNotFoundException(
                    "PartMasterTemplateNotFoundException", body.template_id)
            if tpl.mask and not _validate_mask(tpl.mask, body.number):
                raise NotAllowedException("NotAllowedException42")
            master.type = tpl.part_type or ""
            master.attributes_locked = tpl.attributes_locked or False
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
        # 处理 ACL（对齐 Java ACLDTO：前端发送 userEntries/groupEntries 数组格式）
        if body.acl:
            user_entries = parse_acl_entries(body.acl.get("userEntries"))
            group_entries = parse_acl_entries(body.acl.get("groupEntries"))
            if user_entries or group_entries:
                new_acl_id = apply_acl(db, None, user_entries, group_entries,
                                       workspace_id=workspace_id)
                revision.acl_id = new_acl_id
        # 创建工作流：用 instantiate_workflow 创建完整 Workflow/Activity/Task 对象图
        if body.workflow_model_id:
            from app.services.workflow_manager import workflow_service
            # 将 role_mapping 列表转为 instantiate_workflow 期望的 dict 格式
            # （instantiate_workflow 内部写 task_user / task_usergroup，无 workflow_usergroup 表）
            role_map = {}
            for rm in (body.role_mapping or []):
                role_name = rm.get("roleName", "")
                if not role_name:
                    continue
                role_map[role_name] = {
                    "users": rm.get("userLogins", []) or [],
                    "groups": rm.get("groupIds", []) or [],
                }
            result = workflow_service.instantiate_workflow(
                db, workspace_id, body.workflow_model_id, role_mapping=role_map)
            wf_id = result["workflowId"]
            revision.workflow_id = wf_id
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
        # 模板处理：复制 instance attributes 和 nativecad 文件
        if body.template_id:
            self._copy_template_instance_attrs_to_part(
                db, workspace_id, body.template_id, body.number)
            self._copy_template_nativecad_to_part(
                db, workspace_id, body.template_id, body.number, iteration)
        db.commit()
        db.refresh(revision)
        return revision

    def delete_revision(self, db: Session, workspace_id: str,
                        number: str, version: str, user_login: str) -> None:
        from app.core.exceptions import EntityConstraintException, AccessRightException
        pr = self.get_revision(db, workspace_id, number, version)
        if pr.checkout_user_login and pr.checkout_user_login != user_login:
            raise NotAllowedException("NotAllowedException47")
        if pr.status == 1:
            raise NotAllowedException("NotAllowedException36")
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
            # 清理 instance attributes（FK 到 partiteration）
            db.execute(
                text("DELETE FROM partiteration_attribute "
                     "WHERE workspace_id=:ws AND partmaster_partnumber=:pn "
                     "AND partrevision_version=:ver AND iteration=:it"),
                {"ws": workspace_id, "pn": number, "ver": version, "it": it.iteration},
            )
            # 清理 vault 物理文件（对齐 Payara removeCADFile/removeAttachedFiles）
            try:
                import shutil
                from pathlib import Path
                from app.core.config import settings
                vault_dir = Path(settings.VAULT_PATH) / workspace_id / "parts" / number / version / str(it.iteration)
                if vault_dir.exists():
                    shutil.rmtree(vault_dir)
            except Exception:
                pass
        indexer_manager.delete_part_revision(pr)  # 对标 deletePartRevision:2154
        db.delete(pr)
        db.commit()

    def checkout(self, db: Session, workspace_id: str,
                 number: str, version: str, user_login: str,
                 auto_commit: bool = True) -> PartRevision:
        from app.core.exceptions import NotAllowedException
        from app.services.factory.acl_factory import check_write_access
        pr = self.get_revision(db, workspace_id, number, version, for_update=True)
        if not check_write_access(db, pr.acl_id, user_login, False, workspace_id=workspace_id):
            raise AccessRightException("AccessRightException", user_login)
        if not pr.is_last_revision:
            raise NotAllowedException("NotAllowedException72")
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
        db.flush()
        # 复制附件、几何体、子件链接到新迭代
        self._copy_iteration_files(db, workspace_id, number, version,
                                   last_iter, last_iter + 1)
        if auto_commit:
            db.commit()
        else:
            db.flush()
        db.refresh(pr)
        return pr

    def checkin(self, db: Session, workspace_id: str,
                number: str, version: str, user_login: str,
                auto_commit: bool = True) -> PartRevision:
        from app.core.exceptions import NotAllowedException
        pr = self.get_revision(db, workspace_id, number, version, for_update=True)
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
        if auto_commit:
            db.commit()
        else:
            db.flush()
        db.refresh(pr)
        indexer_manager.index_part_revision(pr)  # 对标 checkInPart:600
        return pr

    def undo_checkout(self, db: Session, workspace_id: str,
                      number: str, version: str, user_login: str) -> PartRevision:
        from app.core.exceptions import NotAllowedException
        pr = self.get_revision(db, workspace_id, number, version, for_update=True)
        if pr.checkout_user_login != user_login:
            raise NotAllowedException("NotAllowedException19")
        if len(pr.iterations) <= 1:
            raise NotAllowedException("NotAllowedException41")
        # 删除未签入的最新迭代
        last = pr.last_iteration
        if last and last.check_in_date is None:
            last_iter_num = last.iteration
            # 清理 join 表 + 孤儿行，避免 db.delete(last) 时 FK 约束冲突
            # （Java 靠 JPA orphanRemoval 级联，Python 需手动清理裸 SQL 层的 join 表）
            ws_p, pn_p, ver_p, it = workspace_id, number, version, last_iter_num
            from sqlalchemy import text as _undo_text

            # 1. partiteration_attribute + 孤儿 instanceattribute
            old_attr_ids = [r[0] for r in db.execute(_undo_text(
                "SELECT instanceattribute_id FROM partiteration_attribute "
                "WHERE workspace_id=:ws AND partmaster_partnumber=:pn "
                "AND partrevision_version=:ver AND iteration=:it"
            ), {"ws": ws_p, "pn": pn_p, "ver": ver_p, "it": it}).fetchall()]
            db.execute(_undo_text(
                "DELETE FROM partiteration_attribute "
                "WHERE workspace_id=:ws AND partmaster_partnumber=:pn "
                "AND partrevision_version=:ver AND iteration=:it"
            ), {"ws": ws_p, "pn": pn_p, "ver": ver_p, "it": it})
            for oid in old_attr_ids:
                still = db.execute(_undo_text(
                    "SELECT 1 FROM partiteration_attribute WHERE instanceattribute_id=:id LIMIT 1"
                ), {"id": oid}).first()
                if not still:
                    db.execute(_undo_text("DELETE FROM instanceattribute WHERE id=:id"), {"id": oid})

            # 2. partiteration_pathdata_attr + 孤儿 instanceattributetemplate
            old_tmpl_ids = [r[0] for r in db.execute(_undo_text(
                "SELECT instanceattribute_template_id FROM partiteration_pathdata_attr "
                "WHERE workspace_id=:ws AND partmaster_partnumber=:pn "
                "AND partrevision_version=:ver AND iteration=:it"
            ), {"ws": ws_p, "pn": pn_p, "ver": ver_p, "it": it}).fetchall()]
            db.execute(_undo_text(
                "DELETE FROM partiteration_pathdata_attr "
                "WHERE workspace_id=:ws AND partmaster_partnumber=:pn "
                "AND partrevision_version=:ver AND iteration=:it"
            ), {"ws": ws_p, "pn": pn_p, "ver": ver_p, "it": it})
            for tid in old_tmpl_ids:
                still = db.execute(_undo_text(
                    "SELECT 1 FROM partiteration_pathdata_attr "
                    "WHERE instanceattribute_template_id=:id LIMIT 1"
                ), {"id": tid}).first()
                if not still:
                    db.execute(_undo_text("DELETE FROM instanceattributetemplate WHERE id=:id"), {"id": tid})

            # 3. partiteration_documentlink + 孤儿 documentlink
            old_dl_ids = [r[0] for r in db.execute(_undo_text(
                "SELECT documentlink_id FROM partiteration_documentlink "
                "WHERE workspace_id=:ws AND partmaster_partnumber=:pn "
                "AND partrevision_version=:ver AND iteration=:it"
            ), {"ws": ws_p, "pn": pn_p, "ver": ver_p, "it": it}).fetchall()]
            db.execute(_undo_text(
                "DELETE FROM partiteration_documentlink "
                "WHERE workspace_id=:ws AND partmaster_partnumber=:pn "
                "AND partrevision_version=:ver AND iteration=:it"
            ), {"ws": ws_p, "pn": pn_p, "ver": ver_p, "it": it})
            for did in old_dl_ids:
                still = db.execute(_undo_text(
                    "SELECT 1 FROM partiteration_documentlink WHERE documentlink_id=:id LIMIT 1"
                ), {"id": did}).first()
                if not still:
                    db.execute(_undo_text("DELETE FROM documentlink WHERE id=:id"), {"id": did})

            # 4. partiteration_partusagelink + 孤儿 PartUsageLink 深链
            old_link_ids = [r[0] for r in db.execute(_undo_text(
                "SELECT component_id FROM partiteration_partusagelink "
                "WHERE workspace_id=:ws AND partmaster_partnumber=:pn "
                "AND partrevision_version=:ver AND iteration=:it"
            ), {"ws": ws_p, "pn": pn_p, "ver": ver_p, "it": it}).fetchall()]
            db.execute(_undo_text(
                "DELETE FROM partiteration_partusagelink "
                "WHERE workspace_id=:ws AND partmaster_partnumber=:pn "
                "AND partrevision_version=:ver AND iteration=:it"
            ), {"ws": ws_p, "pn": pn_p, "ver": ver_p, "it": it})
            if old_link_ids:
                self._delete_orphan_usage_links(db, old_link_ids)

            # 5. partiteration_binres + partiteration_geometry（join 表先行）
            db.execute(_undo_text(
                "DELETE FROM partiteration_binres "
                "WHERE workspace_id=:ws AND partmaster_partnumber=:pn "
                "AND partrevision_version=:ver AND iteration=:it"
            ), {"ws": ws_p, "pn": pn_p, "ver": ver_p, "it": it})
            db.execute(_undo_text(
                "DELETE FROM partiteration_geometry "
                "WHERE workspace_id=:ws AND partmaster_partnumber=:pn "
                "AND partrevision_version=:ver AND iteration=:it"
            ), {"ws": ws_p, "pn": pn_p, "ver": ver_p, "it": it})

            db.delete(last)
            db.flush()
            # 删除 BinaryResource 行（属于已删除迭代）
            db.query(BinaryResource).filter(
                BinaryResource.full_name.like(
                    f"{workspace_id}/parts/{number}/{version}/{last_iter_num}/%")
            ).delete(synchronize_session=False)
            # 清理 vault 物理文件
            try:
                import shutil
                from pathlib import Path
                from app.core.config import settings
                vault_dir = Path(settings.VAULT_PATH) / workspace_id / "parts" / number / version / str(last_iter_num)
                if vault_dir.exists():
                    shutil.rmtree(vault_dir)
            except Exception:
                pass
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
        from app.core.exceptions import NotAllowedException, AccessRightException
        pr = self.get_revision(db, workspace_id, number, version, for_update=True)
        if pr.checkout_user_login != user_login:
            raise NotAllowedException("NotAllowedException25", number)
        if iteration_num != pr.last_iteration_number:
            raise AccessRightException("AccessRightException", user_login)
        # 找目标迭代
        target = next(
            (it for it in pr.iterations if it.iteration == iteration_num), None
        )
        if target is None:
            raise PartIterationNotFoundException("PartIterationNotFoundException", number, version, str(iteration_num))
        now = datetime.utcnow()
        target.modification_date = now
        if body.iterationNote is not None:
            target.iteration_note = body.iterationNote
        # 更新关联文档
        if body.linkedDocuments is not None:
            self._sync_linked_documents(db, target, body.linkedDocuments)
        # 更新实例属性
        if body.instanceAttributes is not None:
            # hasValidChange 校验（对齐 Java AttributesConsistencyUtils）
            from types import SimpleNamespace
            from sqlalchemy import text as sql_text
            rows = db.execute(sql_text(
                "SELECT ia.id, ia.name, ia.locked, ia.mandatory, "
                "ia.textvalue, ia.datevalue, ia.numbervalue, ia.indexvalue, ia.urlvalue, "
                "ia.booleanvalue "
                "FROM instanceattribute ia "
                "JOIN partiteration_attribute pia ON pia.instanceattribute_id = ia.id "
                "WHERE pia.workspace_id=:ws AND pia.partmaster_partnumber=:pn "
                "AND pia.partrevision_version=:ver AND pia.iteration=:it "
                "ORDER BY pia.attribute_order"
            ), {"ws": workspace_id, "pn": number, "ver": version, "it": iteration_num}).fetchall()
            def _extract_value(row):
                vals = []
                if row.textvalue is not None:
                    vals.append(str(row.textvalue))
                if row.datevalue is not None:
                    vals.append(str(row.datevalue))
                if row.numbervalue is not None:
                    vals.append(str(row.numbervalue))
                if row.indexvalue is not None:
                    vals.append(str(row.indexvalue))
                if row.urlvalue is not None:
                    vals.append(str(row.urlvalue))
                if row.booleanvalue is not None:
                    vals.append(str(row.booleanvalue))
                return vals[0] if vals else None
            current_attrs = [
                SimpleNamespace(
                    name=row.name or "",
                    locked=row.locked or False,
                    mandatory=row.mandatory or False,
                    value=_extract_value(row),
                )
                for row in rows
            ]
            def _dto_value(d):
                for key in ("textValue", "longTextValue", "numberValue", "dateValue", "urlValue", "booleanValue"):
                    v = d.get(key)
                    if v is not None:
                        return str(v)
                return None
            new_attrs = [
                SimpleNamespace(
                    name=a.get("name", ""),
                    locked=a.get("locked", False),
                    mandatory=a.get("mandatory", False),
                    value=_dto_value(a),
                )
                for a in body.instanceAttributes
            ]
            from app.services.validation.attributes_consistency_utils import has_valid_change
            if not has_valid_change(current_attrs, pr.part_master.attributes_locked or False, new_attrs):
                raise NotAllowedException("NotAllowedException59")
            self._sync_instance_attributes(db, target, body.instanceAttributes)
        # 同步实例属性模板（对齐 Java updatePartIteration 中的模板同步）
        if body.instanceAttributeTemplates is not None:
            self._sync_instance_attribute_templates(db, target, body.instanceAttributeTemplates)
        # 更新子件列表
        if body.components is not None:
            self._check_cyclic_assembly(db, target, body.components, workspace_id)
            self._sync_components(db, target, body.components, workspace_id)
        db.commit()
        db.refresh(pr)
        indexer_manager.index_part_revision(pr)
        return pr

    def _check_cyclic_assembly(self, db: Session, iteration: PartIteration,
                              components_dto: list, workspace_id: str) -> None:
        """检查新增子件是否会形成循环引用（BFS 遍历子件的子件链）。"""
        from app.core.exceptions import EntityConstraintException
        current_pn = iteration.partmaster_partnumber
        # 收集所有新增子件的零件号
        new_comp_numbers = set()
        for comp_dto in components_dto:
            if comp_dto.component and comp_dto.component.number:
                new_comp_numbers.add(comp_dto.component.number)
        if not new_comp_numbers:
            return
        # BFS：从每个新子件出发，检查其子件链是否包含当前零件号
        visited = set()
        queue = list(new_comp_numbers)
        while queue:
            pn = queue.pop(0)
            if pn == current_pn:
                raise EntityConstraintException("EntityConstraintException12")
            if pn in visited:
                continue
            visited.add(pn)
            # 查 pn 的装配使用了哪些子件（BFS 前向遍历）
            sub_rows = db.query(PartUsageLink.component_partnumber).join(
                part_iteration_usagelink,
                part_iteration_usagelink.c.component_id == PartUsageLink.id,
            ).filter(
                part_iteration_usagelink.c.partmaster_partnumber == pn,
                part_iteration_usagelink.c.workspace_id == workspace_id,
            ).distinct().all()
            for sr in sub_rows:
                if sr[0] and sr[0] not in visited:
                    queue.append(sr[0])
        return

    def _sync_components(self, db: Session, iteration: PartIteration,
                          components_dto: list, workspace_id: str) -> None:
        # 并发保护：父级 update_iteration 已通过 SELECT FOR UPDATE 锁定 PartRevision 行，
        # 同一 revision 的并发请求被串行化，DELETE→INSERT 不可交错，避免孤儿 PartUsageLink。
        # savepoint：内部任一 flush 失败时只回滚本次同步，不污染外层 session。
        with db.begin_nested():
            self.__do_sync_components(db, iteration, components_dto, workspace_id)

    def __do_sync_components(self, db: Session, iteration: PartIteration,
                              components_dto: list, workspace_id: str) -> None:
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
        # 删除孤儿 PartUsageLink：所有 FK 均为 NO ACTION（无级联），
        # 必须先按依赖顺序清理关联表 + 各自的 cadinstance/substitute 行，再删 partusagelink。
        if old_link_ids:
            self._delete_orphan_usage_links(db, old_link_ids)
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
                # 对齐 Java: matrix 数组 → 独立 m00~m22 字段
                mat = cad_dto.matrix or []
                m00 = cad_dto.m00 if cad_dto.m00 is not None else (mat[0] if len(mat) > 0 else None)
                m01 = cad_dto.m01 if cad_dto.m01 is not None else (mat[1] if len(mat) > 1 else None)
                m02 = cad_dto.m02 if cad_dto.m02 is not None else (mat[2] if len(mat) > 2 else None)
                m10 = cad_dto.m10 if cad_dto.m10 is not None else (mat[3] if len(mat) > 3 else None)
                m11 = cad_dto.m11 if cad_dto.m11 is not None else (mat[4] if len(mat) > 4 else None)
                m12 = cad_dto.m12 if cad_dto.m12 is not None else (mat[5] if len(mat) > 5 else None)
                m20 = cad_dto.m20 if cad_dto.m20 is not None else (mat[6] if len(mat) > 6 else None)
                m21 = cad_dto.m21 if cad_dto.m21 is not None else (mat[7] if len(mat) > 7 else None)
                m22 = cad_dto.m22 if cad_dto.m22 is not None else (mat[8] if len(mat) > 8 else None)
                # 推断 rotation_type：DTO 未提供时，有矩阵值走 MATRIX，否则 ANGLE（对齐 Java RotationType 兜底）
                rot_type = cad_dto.rotationType
                if rot_type is None:
                    rot_type = "MATRIX" if m00 is not None else "ANGLE"
                cad = CADInstance(
                    rotation_type=rot_type,
                    rx=cad_dto.rx, ry=cad_dto.ry, rz=cad_dto.rz,
                    tx=cad_dto.tx, ty=cad_dto.ty, tz=cad_dto.tz,
                    m00=m00, m01=m01, m02=m02,
                    m10=m10, m11=m11, m12=m12,
                    m20=m20, m21=m21, m22=m22,
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

    def _delete_orphan_usage_links(self, db: Session, old_link_ids: list) -> None:
        """删除孤儿 PartUsageLink 深链（undo_checkout 与 sync_components 共用）。

        所有 FK 均为 NO ACTION（无级联），必须按依赖顺序清理关联表
        + 各自的 cadinstance/substitute 行，最后再删 partusagelink。
        """
        from sqlalchemy import text
        # 1. 收集将成孤儿的 cadinstance id（经 partusagelink_cadinstance 关联）
        orphan_cad_ids = [
            r[0] for r in db.execute(text(
                "SELECT cadinstance_id FROM partusagelink_cadinstance "
                "WHERE partusagelink_id = ANY(:ids)"
            ), {"ids": old_link_ids}).fetchall()
        ]
        # 2. 收集将成孤儿的 substitute link id（经 pusagelink_psubstitutelink 关联）
        orphan_sub_ids = [
            r[0] for r in db.execute(text(
                "SELECT partsubstitute_id FROM pusagelink_psubstitutelink "
                "WHERE partusagelink_id = ANY(:ids)"
            ), {"ids": old_link_ids}).fetchall()
        ]
        # 3. 收集 substitute link 关联的 cadinstance id
        orphan_sub_cad_ids = []
        if orphan_sub_ids:
            orphan_sub_cad_ids = [
                r[0] for r in db.execute(text(
                    "SELECT cadinstance_id FROM partsubstitutelink_cadinstance "
                    "WHERE partsubstitutelink_id = ANY(:ids)"
                ), {"ids": orphan_sub_ids}).fetchall()
            ]
        # 4. 按依赖顺序删除关联表
        db.execute(text(
            "DELETE FROM partusagelink_cadinstance WHERE partusagelink_id = ANY(:ids)"
        ), {"ids": old_link_ids})
        db.execute(text(
            "DELETE FROM pusagelink_psubstitutelink WHERE partusagelink_id = ANY(:ids)"
        ), {"ids": old_link_ids})
        if orphan_sub_ids:
            db.execute(text(
                "DELETE FROM partsubstitutelink_cadinstance WHERE partsubstitutelink_id = ANY(:ids)"
            ), {"ids": orphan_sub_ids})
            db.execute(text(
                "DELETE FROM partsubstitutelink WHERE id = ANY(:ids)"
            ), {"ids": orphan_sub_ids})
        # 5. 删除孤儿 cadinstance 行（substitute 与 usage 两批）
        all_orphan_cad = orphan_cad_ids + orphan_sub_cad_ids
        if all_orphan_cad:
            db.execute(text(
                "DELETE FROM cadinstance WHERE id = ANY(:ids)"
            ), {"ids": all_orphan_cad})
        # 6. 最后删除孤儿 PartUsageLink
        db.query(PartUsageLink).filter(
            PartUsageLink.id.in_(old_link_ids)
        ).delete(synchronize_session=False)

    def _sync_linked_documents(self, db: Session, iteration: PartIteration,
                                linked_docs: list) -> None:
        """同步关联文档（替换当前迭代的全部 documentlink）。"""
        from sqlalchemy import text
        ws = iteration.workspace_id
        pn = iteration.partmaster_partnumber
        ver = iteration.partrevision_version
        it = iteration.iteration
        # 清除旧关联
        db.execute(text(
            "DELETE FROM partiteration_documentlink "
            "WHERE workspace_id=:ws AND partmaster_partnumber=:pn "
            "AND partrevision_version=:ver AND iteration=:it"
        ), {"ws": ws, "pn": pn, "ver": ver, "it": it})
        for ld in (linked_docs or []):
            result = db.execute(text(
                "INSERT INTO documentlink (commentdata, target_documentmaster_id, "
                "target_docrevision_version, target_workspace_id) "
                "VALUES (:comment, :dm, :drv, :tws) RETURNING id"
            ), {
                "comment": ld.get("commentLink", ""),
                "dm": ld.get("documentMasterId", ""),
                "drv": ld.get("version", "A"),
                "tws": ws,
            })
            link_id = result.fetchone()[0]
            db.execute(text(
                "INSERT INTO partiteration_documentlink "
                "(workspace_id, partmaster_partnumber, partrevision_version, "
                "iteration, documentlink_id) "
                "VALUES (:ws, :pn, :ver, :it, :lid)"
            ), {"ws": ws, "pn": pn, "ver": ver, "it": it, "lid": link_id})

    def _sync_instance_attributes(self, db: Session, iteration: PartIteration,
                                   attrs: list) -> None:
        """同步实例属性（替换当前迭代的全部 instanceattribute）。"""
        from sqlalchemy import text
        ws = iteration.workspace_id
        pn = iteration.partmaster_partnumber
        ver = iteration.partrevision_version
        it = iteration.iteration
        # 查旧属性 ID
        old_ids = [
            row[0] for row in db.execute(text(
                "SELECT instanceattribute_id FROM partiteration_attribute "
                "WHERE workspace_id=:ws AND partmaster_partnumber=:pn "
                "AND partrevision_version=:ver AND iteration=:it"
            ), {"ws": ws, "pn": pn, "ver": ver, "it": it}).fetchall()
        ]
        # 清除旧关联
        db.execute(text(
            "DELETE FROM partiteration_attribute "
            "WHERE workspace_id=:ws AND partmaster_partnumber=:pn "
            "AND partrevision_version=:ver AND iteration=:it"
        ), {"ws": ws, "pn": pn, "ver": ver, "it": it})
        # 删除孤儿 InstanceAttribute：仅当无其它迭代/关联仍引用该行时才删，
        # 避免历史"浅拷贝"共享行触发 FK 冲突（fk_partiteration_attribute_instanceattribute_id）
        if old_ids:
            for oid in old_ids:
                still_referenced = db.execute(text(
                    "SELECT 1 FROM partiteration_attribute "
                    "WHERE instanceattribute_id=:id LIMIT 1"
                ), {"id": oid}).first()
                if still_referenced:
                    continue
                db.execute(text(
                    "DELETE FROM instanceattribute WHERE id=:id"
                ), {"id": oid})
        # 插入新属性
        for order, attr in enumerate(attrs):
            dtype = self._infer_attribute_dtype(attr)
            result = db.execute(text(
                "INSERT INTO instanceattribute (name, mandatory, locked, dtype, "
                "booleanvalue, datevalue, indexvalue, numbervalue, "
                "textvalue, longtextvalue, urlvalue) "
                "VALUES (:name, :mand, :locked, :dtype, "
                ":bv, :dv, :iv, :nv, :tv, :ltv, :uv) RETURNING id"
            ), {
                "name": attr.get("name", ""),
                "mand": attr.get("mandatory", False),
                "locked": attr.get("locked", False),
                "dtype": dtype,
                "bv": attr.get("booleanValue"),
                "dv": attr.get("dateValue"),
                "iv": attr.get("indexValue"),
                "nv": attr.get("numberValue"),
                "tv": attr.get("textValue"),
                "ltv": attr.get("longTextValue"),
                "uv": attr.get("urlValue"),
            })
            attr_id = result.fetchone()[0]
            db.execute(text(
                "INSERT INTO partiteration_attribute "
                "(workspace_id, partmaster_partnumber, partrevision_version, "
                "iteration, instanceattribute_id, attribute_order) "
                "VALUES (:ws, :pn, :ver, :it, :aid, :order)"
            ), {"ws": ws, "pn": pn, "ver": ver, "it": it,
                "aid": attr_id, "order": order})

    @staticmethod
    def _infer_attribute_dtype(attr: dict) -> str:
        """根据属性值字段推断 JPA dtype 鉴别值，对齐 Java @DiscriminatorValue。"""
        if attr.get("booleanValue") is not None:
            return "InstanceBooleanAttribute"
        if attr.get("dateValue") is not None:
            return "InstanceDateAttribute"
        if attr.get("numberValue") is not None:
            return "InstanceNumberAttribute"
        if attr.get("urlValue") is not None:
            return "InstanceURLAttribute"
        if attr.get("indexValue") is not None:
            return "InstanceListOfValuesAttribute"
        if attr.get("longTextValue") is not None:
            return "InstanceLongTextAttribute"
        return "InstanceTextAttribute"

    def _sync_instance_attribute_templates(self, db: Session, iteration: PartIteration,
                                            templates: list) -> None:
        """同步 InstanceAttributeTemplate 列表（对齐 Java updatePartIteration 中的模板同步）。"""
        from sqlalchemy import text
        ws = iteration.workspace_id
        pn = iteration.partmaster_partnumber
        ver = iteration.partrevision_version
        it = iteration.iteration
        # 删除旧关联
        db.execute(text(
            "DELETE FROM partiteration_pathdata_attr "
            "WHERE workspace_id=:ws AND partmaster_partnumber=:pn "
            "AND partrevision_version=:ver AND iteration=:it"
        ), {"ws": ws, "pn": pn, "ver": ver, "it": it})
        # 插入新模板属性
        for tpl in (templates or []):
            result = db.execute(text(
                "INSERT INTO instanceattributetemplate "
                "(name, dtype, mandatory, locked, attributetype, lov_name, lov_workspace_id) "
                "VALUES (:name, :dtype, :mand, :locked, :atype, :lov_name, :lov_ws) RETURNING id"
            ), {
                "name": tpl.get("name", ""),
                "dtype": tpl.get("dtype", ""),
                "mand": tpl.get("mandatory", False),
                "locked": tpl.get("locked", False),
                "atype": tpl.get("attributeType", ""),
                "lov_name": tpl.get("lovName"),
                "lov_ws": tpl.get("lovWorkspaceId"),
            })
            attr_id = result.fetchone()[0]
            db.execute(text(
                "INSERT INTO partiteration_pathdata_attr "
                "(workspace_id, partmaster_partnumber, partrevision_version, iteration, "
                "instanceattributetemplate_id) "
                "VALUES (:ws, :pn, :ver, :it, :aid)"
            ), {"ws": ws, "pn": pn, "ver": ver, "it": it, "aid": attr_id})

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
                           user_login: str, description: str = None,
                           workflow_model_id: str = None,
                           acl_user_entries: dict = None,
                           acl_group_entries: dict = None,
                           role_mapping: dict = None) -> PartRevision:
        """创建零件的新版本（对照 Java ProductManagerBean.createPartRevision）。

        :param workflow_model_id: 工作流模型 ID（可选），传入时实例化 workflow 并挂到新版本。
        :param acl_user_entries:  ACL 用户条目 {login: permission_str}（可选）。
        :param acl_group_entries: ACL 用户组条目 {group_id: permission_str}（可选）。
        :param role_mapping:      角色映射 {role_name: {users:[...], groups:[...]}}（workflow 实例化时使用）。
        """
        from app.core.exceptions import NotAllowedException, EntityAlreadyExistsException, PartRevisionAlreadyExistsException
        pr = self.get_revision(db, ws, pn, ver)
        if pr.checkout_user_login:
            raise NotAllowedException("NotAllowedException40")
        if not pr.iterations:
            raise NotAllowedException("NotAllowedException41")
        now = datetime.utcnow()
        new_ver = self._next_version(ver)
        # 检查新版本是否已存在
        existing_new = (
            db.query(PartRevision)
            .filter(PartRevision.workspace_id == ws,
                    PartRevision.partmaster_partnumber == pn,
                    PartRevision.version == new_ver)
            .first()
        )
        if existing_new:
            raise PartRevisionAlreadyExistsException(
                "PartRevisionAlreadyExistsException", pn, new_ver)
        new_pr = PartRevision(
            workspace_id=ws, partmaster_partnumber=pn, version=new_ver,
            description=description if description else pr.description,
            status=0, creation_date=now,
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

        # --- 挂载 Workflow（对照 Java createPartRevision workflow 实例化逻辑）---
        if workflow_model_id:
            from app.services.workflow_manager import WorkflowService
            wf_result = WorkflowService().instantiate_workflow(
                db, ws, workflow_model_id, role_mapping or {}
            )
            wf_id = wf_result["workflowId"]
            # instantiate_workflow 内部已 commit，用 UPDATE 直接写回 workflow_id
            db.execute(
                __import__("sqlalchemy").text(
                    "UPDATE partrevision SET workflow_id = :wf_id "
                    "WHERE workspace_id = :ws AND partmaster_partnumber = :pn AND version = :ver"
                ),
                {"wf_id": wf_id, "ws": ws, "pn": pn, "ver": new_ver},
            )
            db.commit()
            db.refresh(new_pr)

        # --- 挂载 ACL（对照 Java createPartRevision setACL 逻辑）---
        if acl_user_entries or acl_group_entries:
            from app.services.factory.acl_factory import apply_acl
            acl_id = apply_acl(db, None,
                               acl_user_entries or {},
                               acl_group_entries or {},
                               workspace_id=ws)
            # apply_acl 内部已 commit，用 UPDATE 直接写回 acl_id
            db.execute(
                __import__("sqlalchemy").text(
                    "UPDATE partrevision SET acl_id = :acl_id "
                    "WHERE workspace_id = :ws AND partmaster_partnumber = :pn AND version = :ver"
                ),
                {"acl_id": acl_id, "ws": ws, "pn": pn, "ver": new_ver},
            )
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
                 labels: list, current_user_login: str = None) -> PartRevision:
        from app.models.part import part_revision_tags
        from app.services.factory.acl_factory import check_write_access
        pr = self.get_revision(db, ws, pn, ver,
                               current_user_login=current_user_login)
        if current_user_login and not check_write_access(db, pr.acl_id, current_user_login, False, workspace_id=ws):
            raise AccessRightException("AccessRightException", current_user_login or "")
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
        indexer_manager.index_part_revision(pr)  # 对标 saveTags:1433
        return pr

    def add_tag(self, db: Session, ws: str, pn: str, ver: str,
                label: str, current_user_login: str = None) -> PartRevision:
        from app.models.part import part_revision_tags
        from app.services.factory.acl_factory import check_write_access
        pr = self.get_revision(db, ws, pn, ver,
                               current_user_login=current_user_login)
        if current_user_login and not check_write_access(db, pr.acl_id, current_user_login, False, workspace_id=ws):
            raise AccessRightException("AccessRightException", current_user_login or "")
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
                   label: str, current_user_login: str = None) -> PartRevision:
        from app.models.part import part_revision_tags
        from app.services.factory.acl_factory import check_write_access
        pr = self.get_revision(db, ws, pn, ver,
                               current_user_login=current_user_login)
        if current_user_login and not check_write_access(db, pr.acl_id, current_user_login, False, workspace_id=ws):
            raise AccessRightException("AccessRightException", current_user_login or "")
        db.execute(part_revision_tags.delete().where(
            part_revision_tags.c.partmaster_workspace_id == ws,
            part_revision_tags.c.partmaster_partnumber == pn,
            part_revision_tags.c.partrevision_version == ver,
            part_revision_tags.c.tag_label == label,
        ))
        db.commit()
        db.refresh(pr)
        indexer_manager.index_part_revision(pr)  # 对标 removeTag:1460
        return pr

    def find_part_master_by_cad_filename(self, db: Session, workspace_id: str,
                                         cad_filename: str) -> Optional[PartMaster]:
        """通过 CAD 文件名查找 PartMaster。
        对齐 Java findPartMasterByCADFileName：
        1. 在 workspace 内查找 nativecad 文件名匹配的 BinaryResource
        2. 解析 full_name 提取零件号
        3. 加载对应的 PartMaster
        """
        br = (
            db.query(BinaryResource)
            .filter(
                BinaryResource.full_name.like(f"{workspace_id}/parts/%/nativecad/{cad_filename}"),
            )
            .first()
        )
        if br is None:
            return None
        # full_name 格式: {ws}/parts/{pn}/{ver}/{iter}/nativecad/{filename}
        parts = br.full_name.split("/")
        if len(parts) < 3:
            return None
        part_number = parts[2]  # parts[1] = "parts", parts[2] = part number
        return (
            db.query(PartMaster)
            .filter(
                PartMaster.workspace_id == workspace_id,
                PartMaster.number == part_number,
            )
            .first()
        )

    def update_usage_links_in_converted_iteration(
        self, db: Session, workspace_id: str, part_number: str,
        version: str, iteration_num: int,
        usage_links: list[PartUsageLink],
    ) -> None:
        """在 CAD 转换回调中更新零件迭代的组件列表。
        对齐 Java updateUsageLinksInConvertedIteration：
        不检查签出状态，因为转换是异步的。
        """
        iteration = (
            db.query(PartIteration)
            .filter(
                PartIteration.workspace_id == workspace_id,
                PartIteration.partmaster_partnumber == part_number,
                PartIteration.partrevision_version == version,
                PartIteration.iteration == iteration_num,
            )
            .first()
        )
        if iteration is None:
            return
        # 收集旧 link id，清理关联后删除孤儿 PartUsageLink
        old_link_ids = [
            row[0] for row in db.execute(
                part_iteration_usagelink.select().with_only_columns(
                    part_iteration_usagelink.c.component_id
                ).where(
                    part_iteration_usagelink.c.workspace_id == workspace_id,
                    part_iteration_usagelink.c.partmaster_partnumber == part_number,
                    part_iteration_usagelink.c.partrevision_version == version,
                    part_iteration_usagelink.c.iteration == iteration_num,
                )
            )
        ]
        db.execute(
            part_iteration_usagelink.delete().where(
                part_iteration_usagelink.c.workspace_id == workspace_id,
                part_iteration_usagelink.c.partmaster_partnumber == part_number,
                part_iteration_usagelink.c.partrevision_version == version,
                part_iteration_usagelink.c.iteration == iteration_num,
            )
        )
        if old_link_ids:
            db.query(PartUsageLink).filter(
                PartUsageLink.id.in_(old_link_ids)
            ).delete(synchronize_session=False)
        for order, link in enumerate(usage_links):
            db.add(link)
            db.flush()
            db.execute(
                part_iteration_usagelink.insert().values(
                    workspace_id=workspace_id,
                    partmaster_partnumber=part_number,
                    partrevision_version=version,
                    iteration=iteration_num,
                    component_id=link.id,
                    component_order=order,
                )
            )

    def search_parts(self, db: Session, ws: str, name=None,
                     number=None, type_=None, author=None,
                     created_after=None, created_before=None,
                     modified_after=None, modified_before=None,
                     tags: list | None = None, attributes: list | None = None,
                     content=None,
                     start: int = 0, length: int = 100) -> list:
        q = db.query(PartMaster).filter(PartMaster.workspace_id == ws)
        if name:
            q = q.filter(PartMaster.name.ilike(f"%{name}%"))
        if number:
            q = q.filter(PartMaster.number.ilike(f"%{number}%"))
        if type_:
            q = q.filter(PartMaster.type.ilike(f"%{type_}%"))
        if author:
            q = q.filter(PartMaster.author_login == author)
        if created_after:
            q = q.filter(PartMaster.creation_date >= created_after)
        if created_before:
            q = q.filter(PartMaster.creation_date <= created_before)
        if modified_after or modified_before:
            from sqlalchemy import func, select as sa_select
            q = q.join(PartRevision,
                       (PartMaster.workspace_id == PartRevision.workspace_id)
                       & (PartMaster.number == PartRevision.partmaster_partnumber))
            latest = (
                sa_select(func.max(PartIteration.iteration))
                .where(
                    (PartIteration.workspace_id == PartRevision.workspace_id)
                    & (PartIteration.partmaster_partnumber == PartRevision.partmaster_partnumber)
                    & (PartIteration.partrevision_version == PartRevision.version)
                ).correlate(PartRevision).scalar_subquery()
            )
            q = q.join(PartIteration,
                       (PartRevision.workspace_id == PartIteration.workspace_id)
                       & (PartRevision.partmaster_partnumber == PartIteration.partmaster_partnumber)
                       & (PartRevision.version == PartIteration.partrevision_version)
                       & (PartIteration.iteration == latest))
            if modified_after:
                q = q.filter(PartIteration.modification_date >= modified_after)
            if modified_before:
                q = q.filter(PartIteration.modification_date <= modified_before)
            q = q.distinct()
        if tags:
            from app.models.part import part_revision_tags
            tag_list = [t.strip() for t in tags if t.strip()]
            if tag_list:
                q = q.join(PartRevision,
                           (PartMaster.workspace_id == PartRevision.workspace_id)
                           & (PartMaster.number == PartRevision.partmaster_partnumber))
                q = q.join(part_revision_tags,
                           (PartRevision.workspace_id == part_revision_tags.c.partmaster_workspace_id)
                           & (PartRevision.partmaster_partnumber == part_revision_tags.c.partmaster_partnumber)
                           & (PartRevision.version == part_revision_tags.c.partrevision_version))
                q = q.filter(part_revision_tags.c.tag_label.in_(tag_list))
                q = q.distinct()
        if attributes:
            from sqlalchemy import text
            attr_list = [a.strip() for a in attributes if a.strip()]
            if attr_list:
                q = q.join(PartRevision,
                           (PartMaster.workspace_id == PartRevision.workspace_id)
                           & (PartMaster.number == PartRevision.partmaster_partnumber))
                q = q.join(PartIteration,
                           (PartRevision.workspace_id == PartIteration.workspace_id)
                           & (PartRevision.partmaster_partnumber == PartIteration.partmaster_partnumber)
                           & (PartRevision.version == PartIteration.partrevision_version))
                from app.models.part import part_iteration_attribute
                q = q.join(part_iteration_attribute,
                           (PartIteration.workspace_id == part_iteration_attribute.c.workspace_id)
                           & (PartIteration.partmaster_partnumber == part_iteration_attribute.c.partmaster_partnumber)
                           & (PartIteration.partrevision_version == part_iteration_attribute.c.partrevision_version)
                           & (PartIteration.iteration == part_iteration_attribute.c.iteration))
                # 查询匹配属性的 instanceattribute_id
                attr_ids = []
                for a in attr_list:
                    attr_rows = db.execute(text(
                        "SELECT id FROM instanceattribute WHERE name=:n OR "
                        "textvalue ILIKE :v OR longtextvalue ILIKE :vl"
                    ), {"n": a, "v": f"%{a}%", "vl": f"%{a}%"}).fetchall()
                    attr_ids.extend([r[0] for r in attr_rows])
                if attr_ids:
                    q = q.filter(part_iteration_attribute.c.instanceattribute_id.in_(attr_ids))
                else:
                    q = q.filter(PartMaster.number == None)
                q = q.distinct()
        if content:
            from sqlalchemy import or_
            q = q.filter(or_(
                PartMaster.name.ilike(f"%{content}%"),
                PartMaster.number.ilike(f"%{content}%"),
            ))
        masters = q.offset(start).limit(length).all()
        result = []
        for m in masters:
            result.extend(m.revisions)
        return result

    def _copy_iteration_files(self, db: Session, ws: str, pn: str, ver: str,
                               from_iter: int, to_iter: int) -> None:
        """将旧迭代的全部分类数据复制到新迭代（含 BinaryResource 深拷贝）。"""
        import shutil
        from pathlib import Path
        from app.core.config import settings
        from app.models.part import (
            BinaryResource,
            part_iteration_binres, part_iteration_geometry,
            part_iteration_usagelink, part_iteration_documentlink,
            part_iteration_attribute,
        )

        vault_root = Path(settings.VAULT_PATH)

        def _new_full(old_full: str) -> str:
            """将 full_name 中的 old_iter 替换为 to_iter。"""
            parts = old_full.split("/")
            if len(parts) >= 5:
                parts[4] = str(to_iter)
            return "/".join(parts)

        def _copy_br(old_full: str, dtype: str = "BinaryResource") -> str:
            """深拷贝 BinaryResource 行 + vault 物理文件，返回新 full_name。"""
            new_full = _new_full(old_full)
            old_br = db.query(BinaryResource).filter(
                BinaryResource.full_name == old_full).first()
            if old_br:
                existing = db.query(BinaryResource).filter(
                    BinaryResource.full_name == new_full).first()
                if existing is None:
                    db.add(BinaryResource(
                        full_name=new_full,
                        dtype=dtype,
                        content_length=old_br.content_length,
                        last_modified=datetime.utcnow(),
                        quality=old_br.quality,
                        x_min=old_br.x_min, x_max=old_br.x_max,
                        y_min=old_br.y_min, y_max=old_br.y_max,
                        z_min=old_br.z_min, z_max=old_br.z_max,
                    ))
                    db.flush()
                try:
                    old_path = vault_root / old_full
                    new_path = vault_root / new_full
                    if old_path.exists() and not new_path.exists():
                        new_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(str(old_path), str(new_path))
                except Exception:
                    pass
            return new_full

        # 复制附件：重建 BinaryResource，再建关联
        for row in db.execute(
            part_iteration_binres.select().where(
                part_iteration_binres.c.workspace_id == ws,
                part_iteration_binres.c.partmaster_partnumber == pn,
                part_iteration_binres.c.partrevision_version == ver,
                part_iteration_binres.c.iteration == from_iter,
            )
        ).fetchall():
            new_full = _copy_br(row.attachedfile_fullname)
            db.execute(part_iteration_binres.insert().values(
                workspace_id=ws, partmaster_partnumber=pn,
                partrevision_version=ver, iteration=to_iter,
                attachedfile_fullname=new_full,
            ))

        # 复制几何体：重建 BinaryResource，再建关联
        for row in db.execute(
            part_iteration_geometry.select().where(
                part_iteration_geometry.c.workspace_id == ws,
                part_iteration_geometry.c.partmaster_partnumber == pn,
                part_iteration_geometry.c.partrevision_version == ver,
                part_iteration_geometry.c.iteration == from_iter,
            )
        ).fetchall():
            new_full = _copy_br(row.geometry_fullname, "Geometry")
            db.execute(part_iteration_geometry.insert().values(
                workspace_id=ws, partmaster_partnumber=pn,
                partrevision_version=ver, iteration=to_iter,
                geometry_fullname=new_full,
            ))

        # 复制子件链接关联：深克隆 PartUsageLink + CADInstance，
        # 避免新迭代复用旧 component_id，后续更新 DELETE partusagelink 时 FK 违反
        from sqlalchemy import text
        for row in db.execute(
            part_iteration_usagelink.select().where(
                part_iteration_usagelink.c.workspace_id == ws,
                part_iteration_usagelink.c.partmaster_partnumber == pn,
                part_iteration_usagelink.c.partrevision_version == ver,
                part_iteration_usagelink.c.iteration == from_iter,
            )
        ).fetchall():
            old_pul_id = row.component_id
            # 深克隆 partusagelink 行
            new_pul = db.execute(text(
                "INSERT INTO partusagelink "
                "(amount, commentdata, optional, referencedescription, unit, "
                "component_partnumber, component_workspace_id) "
                "SELECT amount, commentdata, optional, referencedescription, unit, "
                "component_partnumber, component_workspace_id "
                "FROM partusagelink WHERE id = :old_id RETURNING id"
            ), {"old_id": old_pul_id}).fetchone()
            new_pul_id = new_pul[0]
            # 深克隆关联的 cadinstance 行，重建 partusagelink_cadinstance 关联
            for ci_row in db.execute(text(
                "SELECT cadinstance_id, cadinstance_order "
                "FROM partusagelink_cadinstance WHERE partusagelink_id = :pid "
                "ORDER BY cadinstance_order"
            ), {"pid": old_pul_id}).fetchall():
                new_cad = db.execute(text(
                    "INSERT INTO cadinstance "
                    "(rotationtype, rx, ry, rz, tx, ty, tz, "
                    "m00, m01, m02, m10, m11, m12, m20, m21, m22) "
                    "SELECT rotationtype, rx, ry, rz, tx, ty, tz, "
                    "m00, m01, m02, m10, m11, m12, m20, m21, m22 "
                    "FROM cadinstance WHERE id = :old_id RETURNING id"
                ), {"old_id": ci_row.cadinstance_id}).fetchone()
                new_cad_id = new_cad[0]
                db.execute(text(
                    "INSERT INTO partusagelink_cadinstance "
                    "(partusagelink_id, cadinstance_id, cadinstance_order) "
                    "VALUES (:pul_id, :cad_id, :ord)"
                ), {"pul_id": new_pul_id, "cad_id": new_cad_id,
                    "ord": ci_row.cadinstance_order})
            db.execute(part_iteration_usagelink.insert().values(
                workspace_id=ws, partmaster_partnumber=pn,
                partrevision_version=ver, iteration=to_iter,
                component_id=new_pul_id,
                component_order=row.component_order,
            ))

        # 复制关联文档（纯关系）
        for row in db.execute(
            part_iteration_documentlink.select().where(
                part_iteration_documentlink.c.workspace_id == ws,
                part_iteration_documentlink.c.partmaster_partnumber == pn,
                part_iteration_documentlink.c.partrevision_version == ver,
                part_iteration_documentlink.c.iteration == from_iter,
            )
        ).fetchall():
            db.execute(part_iteration_documentlink.insert().values(
                workspace_id=ws, partmaster_partnumber=pn,
                partrevision_version=ver, iteration=to_iter,
                documentlink_id=row.documentlink_id,
            ))

        # 复制实例属性：深克隆 instanceattribute 行（每个迭代独占其属性，
        # 对齐 Java checkOutPart 的 attr.clone()+instanceAttributeDAO.createAttribute()）
        from sqlalchemy import text as _clone_text
        for row in db.execute(
            part_iteration_attribute.select().where(
                part_iteration_attribute.c.workspace_id == ws,
                part_iteration_attribute.c.partmaster_partnumber == pn,
                part_iteration_attribute.c.partrevision_version == ver,
                part_iteration_attribute.c.iteration == from_iter,
            )
        ).fetchall():
            cloned = db.execute(_clone_text(
                "INSERT INTO instanceattribute "
                "(name, mandatory, locked, dtype, booleanvalue, datevalue, indexvalue, "
                "numbervalue, textvalue, longtextvalue, urlvalue, "
                "partmaster_workspace_id, partmaster_partnumber) "
                "SELECT name, mandatory, locked, dtype, booleanvalue, datevalue, indexvalue, "
                "numbervalue, textvalue, longtextvalue, urlvalue, "
                "partmaster_workspace_id, partmaster_partnumber "
                "FROM instanceattribute WHERE id = :old_id RETURNING id"
            ), {"old_id": row.instanceattribute_id}).fetchone()
            new_attr_id = cloned[0]
            db.execute(part_iteration_attribute.insert().values(
                workspace_id=ws, partmaster_partnumber=pn,
                partrevision_version=ver, iteration=to_iter,
                instanceattribute_id=new_attr_id,
                attribute_order=row.attribute_order,
            ))

        # 复制实例属性模板：克隆 instanceattributetemplate 行再建关联（对齐 Java checkOutPart clone 逻辑）
        from sqlalchemy import text
        old_tpls = db.execute(text(
            "SELECT iat.id, iat.dtype, iat.name, iat.mandatory, iat.locked, iat.attributetype "
            "FROM instanceattributetemplate iat "
            "JOIN partiteration_pathdata_attr ppa "
            "  ON ppa.instanceattribute_template_id = iat.id "
            "WHERE ppa.workspace_id = :ws AND ppa.partmaster_partnumber = :pn "
            "  AND ppa.partrevision_version = :ver AND ppa.iteration = :iter "
            "ORDER BY ppa.attribute_order"
        ), {"ws": ws, "pn": pn, "ver": ver, "iter": from_iter}).fetchall()
        for order, tpl in enumerate(old_tpls):
            result = db.execute(text(
                "INSERT INTO instanceattributetemplate "
                "(dtype, name, mandatory, locked, attributetype) "
                "VALUES (:dtype, :name, :mand, :locked, :attrtype) RETURNING id"
            ), {"dtype": tpl[1], "name": tpl[2], "mand": tpl[3],
                "locked": tpl[4], "attrtype": tpl[5]})
            new_id = result.fetchone()[0]
            db.execute(text(
                "INSERT INTO partiteration_pathdata_attr "
                "(workspace_id, partmaster_partnumber, partrevision_version, "
                "iteration, instanceattribute_template_id, attribute_order) "
                "VALUES (:ws, :pn, :ver, :iter, :tid, :order)"
            ), {"ws": ws, "pn": pn, "ver": ver, "iter": to_iter,
                "tid": new_id, "order": order})

        # 复制 nativeCADFile 引用（含 BinaryResource 深拷贝）
        old_iter = (
            db.query(PartIteration)
            .filter(
                PartIteration.workspace_id == ws,
                PartIteration.partmaster_partnumber == pn,
                PartIteration.partrevision_version == ver,
                PartIteration.iteration == from_iter,
            )
            .first()
        )
        if old_iter and old_iter.native_cad_file_fullname:
            new_full = _copy_br(old_iter.native_cad_file_fullname)
            new_iter = (
                db.query(PartIteration)
                .filter(
                    PartIteration.workspace_id == ws,
                    PartIteration.partmaster_partnumber == pn,
                    PartIteration.partrevision_version == ver,
                    PartIteration.iteration == to_iter,
                )
                .first()
            )
            if new_iter:
                new_iter.native_cad_file_fullname = new_full

    _ATTR_TYPE_MAP = {
        0: "InstanceTextAttribute",
        1: "InstanceNumberAttribute",
        2: "InstanceDateAttribute",
        3: "InstanceBooleanAttribute",
        4: "InstanceURLAttribute",
        5: "InstanceLongTextAttribute",
    }

    def _copy_template_instance_attrs_to_part(self, db: Session,
                                                workspace_id: str,
                                                template_id: str,
                                                part_number: str) -> None:
        """从 PartMasterTemplate 复制 instanceAttributes 到首版首次迭代。"""
        from sqlalchemy import text as sql_text
        rows = db.execute(sql_text(
            "SELECT iat.id, iat.name, iat.mandatory, iat.locked, iat.attributetype "
            "FROM instanceattributetemplate iat "
            "JOIN partmastertemplate_attr pta "
            "  ON pta.instanceattributetemplate_id = iat.id "
            "WHERE pta.workspace_id = :ws AND pta.partmastertemplate_id = :tid "
            "ORDER BY pta.attr_order"
        ), {"ws": workspace_id, "tid": template_id}).fetchall()
        for order, row in enumerate(rows):
            attr_type = row[4] if row[4] is not None else 0
            dtype = self._ATTR_TYPE_MAP.get(attr_type, "InstanceTextAttribute")
            result = db.execute(sql_text(
                "INSERT INTO instanceattribute (dtype, name, mandatory, locked) "
                "VALUES (:dtype, :name, :mand, :locked) RETURNING id"
            ), {"dtype": dtype, "name": row[1],
                "mand": row[2] or False, "locked": row[3] or False})
            attr_id = result.fetchone()[0]
            db.execute(sql_text(
                "INSERT INTO partiteration_attribute "
                "(workspace_id, partmaster_partnumber, partrevision_version, "
                "iteration, instanceattribute_id, attribute_order) "
                "VALUES (:ws, :pn, :ver, :iter, :aid, :order)"
            ), {"ws": workspace_id, "pn": part_number, "ver": "A",
                "iter": 1, "aid": attr_id, "order": order})

    def _copy_template_nativecad_to_part(self, db: Session,
                                           workspace_id: str,
                                           template_id: str,
                                           part_number: str,
                                           iteration: PartIteration) -> None:
        """从 PartMasterTemplate 复制 nativecad 文件到新零件的 vault。
        对齐 Java createPartMaster 第352-367行。"""
        import shutil
        from pathlib import Path
        from app.core.config import settings
        from sqlalchemy import text as sql_text

        tpl = db.execute(sql_text(
            "SELECT attachedfile_fullname FROM partmastertemplate "
            "WHERE workspace_id=:ws AND id=:tid"
        ), {"ws": workspace_id, "tid": template_id}).first()
        file_rows = [(tpl[0],)] if tpl and tpl[0] else []
        if not file_rows:
            return
        vault_root = Path(settings.VAULT_PATH)
        for frow in file_rows:
            old_full = frow[0]
            filename = old_full.rsplit("/", 1)[-1] if "/" in old_full else old_full
            new_full = f"{workspace_id}/parts/{part_number}/A/1/nativecad/{filename}"
            old_br = db.query(BinaryResource).filter(
                BinaryResource.full_name == old_full).first()
            if old_br:
                existing = db.query(BinaryResource).filter(
                    BinaryResource.full_name == new_full).first()
                if existing is None:
                    db.add(BinaryResource(
                        full_name=new_full, dtype="BinaryResource",
                        content_length=old_br.content_length,
                        last_modified=datetime.utcnow(),
                        quality=old_br.quality,
                        x_min=old_br.x_min, x_max=old_br.x_max,
                        y_min=old_br.y_min, y_max=old_br.y_max,
                        z_min=old_br.z_min, z_max=old_br.z_max,
                    ))
                    db.flush()
                try:
                    old_path = vault_root / old_full
                    new_path = vault_root / new_full
                    if old_path.exists() and not new_path.exists():
                        new_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(str(old_path), str(new_path))
                except Exception:
                    pass
            iteration.native_cad_file_fullname = new_full

    # ── publish / unpublish ─────────────────────────────────────

    def publish_revision(self, db: Session, workspace_id: str,
                         number: str, version: str, user_login: str) -> None:
        from app.services.factory.acl_factory import check_write_access
        pr = self.get_revision(db, workspace_id, number, version)
        if not check_write_access(db, pr.acl_id, user_login, False, workspace_id=workspace_id):
            raise AccessRightException("AccessRightException", user_login)
        pr.public_shared = True
        db.commit()

    def unpublish_revision(self, db: Session, workspace_id: str,
                           number: str, version: str, user_login: str) -> None:
        from app.services.factory.acl_factory import check_write_access
        pr = self.get_revision(db, workspace_id, number, version)
        if not check_write_access(db, pr.acl_id, user_login, False, workspace_id=workspace_id):
            raise AccessRightException("AccessRightException", user_login)
        pr.public_shared = False
        db.commit()

    # ── ACL ─────────────────────────────────────────────────────

    def update_part_acl(self, db: Session, workspace_id: str, number: str,
                        version: str, user_login: str, body: dict) -> None:
        from sqlalchemy import text
        from app.services.factory.acl_factory import apply_acl
        pr = self.get_revision(db, workspace_id, number, version)
        is_admin = db.execute(text(
            "SELECT 1 FROM workspace WHERE id=:w AND admin_login=:l"
        ), {"w": workspace_id, "l": user_login}).scalar()
        if pr.author_login != user_login and not is_admin:
            raise AccessRightException("AccessRightException", user_login)
        acl_id = getattr(pr, "acl_id", None)
        user_entries = body.get("userEntries", {})
        group_entries = body.get("groupEntries", {})
        new_acl_id = apply_acl(db, acl_id, user_entries, group_entries,
                               workspace_id=workspace_id)
        if pr.acl_id != new_acl_id:
            pr.acl_id = new_acl_id
            db.commit()

    # ── used-by 查询 ────────────────────────────────────────────

    def get_used_by_as_component(self, db: Session, workspace_id: str,
                                 number: str, version: str) -> list:
        from sqlalchemy import text
        rows = db.execute(text(
            "SELECT DISTINCT pr.workspace_id, pr.partmaster_partnumber, pr.version "
            "FROM partrevision pr "
            "JOIN partiteration pi ON pi.workspace_id = pr.workspace_id "
            "  AND pi.partmaster_partnumber = pr.partmaster_partnumber "
            "  AND pi.partrevision_version = pr.version "
            "JOIN partiteration_partusagelink piul "
            "  ON piul.workspace_id = pi.workspace_id "
            "  AND piul.partmaster_partnumber = pi.partmaster_partnumber "
            "  AND piul.partrevision_version = pi.partrevision_version "
            "  AND piul.iteration = pi.iteration "
            "JOIN partusagelink pul ON pul.id = piul.component_id "
            "WHERE pul.component_workspace_id = :ws AND pul.component_partnumber = :pn"
        ), {"ws": workspace_id, "pn": number}).fetchall()
        return [(row.workspace_id, row.partmaster_partnumber, row.version) for row in rows]

    def get_used_by_as_substitute(self, db: Session, workspace_id: str,
                                  number: str, version: str) -> list:
        from sqlalchemy import text
        rows = db.execute(text(
            "SELECT DISTINCT pr.workspace_id, pr.partmaster_partnumber, pr.version "
            "FROM partrevision pr "
            "JOIN partiteration pi ON pi.workspace_id = pr.workspace_id "
            "  AND pi.partmaster_partnumber = pr.partmaster_partnumber "
            "  AND pi.partrevision_version = pr.version "
            "JOIN partiteration_partusagelink piul "
            "  ON piul.workspace_id = pi.workspace_id "
            "  AND piul.partmaster_partnumber = pi.partmaster_partnumber "
            "  AND piul.partrevision_version = pi.partrevision_version "
            "  AND piul.iteration = pi.iteration "
            "JOIN pusagelink_psubstitutelink upl ON upl.partusagelink_id = piul.component_id "
            "JOIN partsubstitutelink psl ON psl.id = upl.partsubstitute_id "
            "WHERE psl.substitute_workspace_id = :ws AND psl.substitute_partnumber = :pn"
        ), {"ws": workspace_id, "pn": number}).fetchall()
        return [(row.workspace_id, row.partmaster_partnumber, row.version) for row in rows]

    # ── baseline 查询 ───────────────────────────────────────────

    def get_baselines_for_part(self, db: Session, workspace_id: str,
                               number: str, version: str) -> list:
        from app.models.configuration.baselined_part import BaselinedPart
        from app.models.configuration.product_baseline import ProductBaseline

        subq = (
            db.query(BaselinedPart.partcollection_id)
            .filter(
                BaselinedPart.target_workspace_id == workspace_id,
                BaselinedPart.target_partmaster_partnumber == number,
                BaselinedPart.target_partrevision_version == version,
            )
            .subquery()
        )

        baselines = (
            db.query(ProductBaseline)
            .filter(ProductBaseline.partcollection_id.in_(subq))
            .order_by(ProductBaseline.name)
            .all()
        )

        return [
            {
                "id": b.id,
                "name": b.name,
                "description": b.description,
                "type": b.type,
                "configurationItemId": b.configurationitem_id,
                "creationDate": b.creation_date.isoformat() if b.creation_date else None,
            }
            for b in baselines
        ]

    def get_used_by_product_instances(self, db: Session, workspace_id: str,
                                      number: str, version: str) -> list:
        from app.models.configuration.baselined_part import BaselinedPart
        from app.models.configuration.product_baseline import ProductBaseline
        from app.models.configuration.product_instance_master import ProductInstanceMaster
        from sqlalchemy import and_

        results = (
            db.query(ProductInstanceMaster)
            .distinct()
            .join(
                ProductBaseline,
                and_(
                    ProductBaseline.configurationitem_workspace_id == ProductInstanceMaster.workspace_id,
                    ProductBaseline.configurationitem_id == ProductInstanceMaster.configurationitem_id,
                ),
            )
            .join(
                BaselinedPart,
                BaselinedPart.partcollection_id == ProductBaseline.partcollection_id,
            )
            .filter(
                BaselinedPart.target_workspace_id == workspace_id,
                BaselinedPart.target_partmaster_partnumber == number,
                BaselinedPart.target_partrevision_version == version,
            )
            .order_by(ProductBaseline.configurationitem_id)
            .all()
        )

        return [
            {
                "serialNumber": pim.serialnumber,
                "configurationItemId": pim.configurationitem_id,
                "workspaceId": pim.workspace_id,
                "productInstanceIterations": None,
                "acl": None,
            }
            for pim in results
        ]

    def filter_by_baseline(self, db: Session, workspace_id: str, pn: str,
                           baseline_id: str) -> PartIteration:
        from app.models.configuration.baselined_part import BaselinedPart
        from app.models.configuration.product_baseline import ProductBaseline
        from app.core.exceptions import WrongInputException, BaselineNotFoundException

        try:
            bl_id = int(baseline_id)
        except ValueError:
            raise WrongInputException("WrongInputException")

        baseline = db.query(ProductBaseline).filter(ProductBaseline.id == bl_id).first()
        if baseline is None:
            raise BaselineNotFoundException("BaselineNotFoundException", baseline_id)
        if baseline.configurationitem_workspace_id != workspace_id:
            raise BaselineNotFoundException("BaselineNotFoundException", baseline_id)

        bp = (
            db.query(BaselinedPart)
            .filter(
                BaselinedPart.partcollection_id == baseline.partcollection_id,
                BaselinedPart.target_workspace_id == workspace_id,
                BaselinedPart.target_partmaster_partnumber == pn,
            )
            .first()
        )

        if bp is None:
            raise PartMasterNotFoundException("PartMasterNotFoundException", pn)

        pi = (
            db.query(PartIteration)
            .filter(
                PartIteration.workspace_id == workspace_id,
                PartIteration.partmaster_partnumber == pn,
                PartIteration.partrevision_version == bp.target_partrevision_version,
                PartIteration.iteration == bp.target_iteration,
            )
            .first()
        )

        if pi is None:
            raise PartIterationNotFoundException(
                "PartIterationNotFoundException", pn,
                bp.target_partrevision_version, bp.target_iteration)

        return pi

    # ── conversion ──────────────────────────────────────────────

    def retry_conversion(self, db: Session, workspace_id: str, number: str,
                         version: str, iteration: int) -> tuple:
        pi = db.query(PartIteration).filter(
            PartIteration.workspace_id == workspace_id,
            PartIteration.partmaster_partnumber == number,
            PartIteration.partrevision_version == version,
            PartIteration.iteration == iteration,
        ).first()
        if pi is None or pi.native_cad_file is None:
            raise WrongInputException("WrongInputException")
        br = pi.native_cad_file
        filename = br.full_name.split("/")[-1] if br.full_name else "unknown"
        conv = self.get_conversion(db, workspace_id, number, version, iteration)
        if conv is None:
            conv = self.create_conversion(db, workspace_id, number, version, iteration)
        else:
            conv.pending = True
            conv.succeed = False
            conv.start_date = None
            conv.end_date = None
        db.commit()
        return filename, pi

    # ── share ───────────────────────────────────────────────────

    def share_part(self, db: Session, workspace_id: str, number: str,
                   version: str, user_login: str, password: str = None,
                   expire_date_str: str = None) -> str:
        import uuid
        import hashlib
        from app.models.part import SharedEntity
        shared_uuid = str(uuid.uuid4())
        password_hash = hashlib.md5(password.encode()).hexdigest() if password else None
        expire_date = datetime.fromisoformat(expire_date_str) if expire_date_str else None
        entity = SharedEntity(
            uuid=shared_uuid,
            dtype="SharedPart",
            creation_date=datetime.utcnow(),
            expire_date=expire_date,
            password=password_hash,
            author_workspace_id=workspace_id,
            author_login=user_login,
            workspace_id=workspace_id,
            entity_workspace_id=workspace_id,
            partmaster_partnumber=number,
            partrevision_version=version,
        )
        db.add(entity)
        db.commit()
        return shared_uuid

    # ── file subresource ────────────────────────────────────────

    def delete_part_file_subresource(self, db: Session, workspace_id: str,
                                     number: str, version: str, iteration: int,
                                     sub_type: str, file_name: str,
                                     user_login: str) -> None:
        from pathlib import Path
        from app.core.config import settings
        from app.models.part import BinaryResource, part_iteration_binres, part_iteration_geometry

        pr = self.get_revision(db, workspace_id, number, version)
        if not pr or pr.checkout_user_login != user_login \
                or pr.last_iteration_number != iteration:
            raise NotAllowedException("NotAllowedException4")
        full_name = f"{workspace_id}/parts/{number}/{version}/{iteration}/{sub_type}/{file_name}"

        if sub_type == "nativecad":
            it = db.query(PartIteration).filter(
                PartIteration.workspace_id == workspace_id,
                PartIteration.partmaster_partnumber == number,
                PartIteration.partrevision_version == version,
                PartIteration.iteration == iteration,
            ).first()
            if it:
                it.native_cad_file_fullname = None
        elif sub_type == "attachedfiles":
            db.execute(part_iteration_binres.delete().where(
                part_iteration_binres.c.workspace_id == workspace_id,
                part_iteration_binres.c.partmaster_partnumber == number,
                part_iteration_binres.c.partrevision_version == version,
                part_iteration_binres.c.iteration == iteration,
                part_iteration_binres.c.attachedfile_fullname == full_name,
            ))
        else:
            db.execute(part_iteration_geometry.delete().where(
                part_iteration_geometry.c.workspace_id == workspace_id,
                part_iteration_geometry.c.partmaster_partnumber == number,
                part_iteration_geometry.c.partrevision_version == version,
                part_iteration_geometry.c.iteration == iteration,
                part_iteration_geometry.c.geometry_fullname == full_name,
            ))

        try:
            vault_path = Path(settings.VAULT_PATH) / full_name
            if vault_path.exists():
                vault_path.unlink()
        except OSError:
            pass

        db.commit()

    # ── new version description ─────────────────────────────────

    def set_new_version_description(self, db: Session, workspace_id: str,
                                    number: str, version: str,
                                    description: str) -> None:
        pr = self.get_revision(db, workspace_id, number, version)
        pr.description = description
        db.commit()

    # ── instances ───────────────────────────────────────────────

    def get_leaf_instances(self, db: Session, workspace_id: str,
                           part_key: str) -> list[dict]:
        from app.services.file_export.instance_body_writer_tools import (
            identity_matrix, collect_leaf_instances,
        )
        parts = part_key.rsplit("-", 1)
        if len(parts) != 2:
            raise WrongInputException("WrongInputException")
        part_number, version = parts

        pi = db.query(PartIteration).filter(
            PartIteration.workspace_id == workspace_id,
            PartIteration.partmaster_partnumber == part_number,
            PartIteration.partrevision_version == version,
        ).order_by(PartIteration.iteration.desc()).first()

        if not pi:
            raise PartIterationNotFoundException(
                "PartIterationNotFoundException", workspace_id, part_number, version)

        result: list[dict] = []
        collect_leaf_instances(db, pi, identity_matrix(), [-1], result)
        return result

    # ── template 管理（从 routers/part_templates.py 迁入）───────

    def _get_template_account(self, db: Session, login: str | None,
                               workspace_id: str) -> dict:
        if not login:
            return {"login": "", "name": "", "email": None, "language": None, "workspaceId": workspace_id}
        from app.models.auth import Account
        acc = db.query(Account).filter(Account.login == login).first()
        return {
            "login": login,
            "name": acc.name if (acc and acc.name) else login,
            "email": acc.email if acc else None,
            "language": acc.language if acc else None,
            "workspaceId": workspace_id,
        }

    def _list_template_files(self, db: Session, workspace_id: str,
                              template_id: str) -> str | None:
        from sqlalchemy import text
        row = db.execute(text(
            "SELECT attachedfile_fullname FROM partmastertemplate "
            "WHERE workspace_id = :ws AND id = :tid"
        ), {"ws": workspace_id, "tid": template_id}).first()
        if row and row[0]:
            from pathlib import Path
            return Path(row[0]).name
        return None

    def remove_template_file(self, db: Session, workspace_id: str,
                              template_id: str, file_name: str) -> None:
        """删除零件模板附件。对齐 Java ProductManagerBean.removeFileFromTemplate + BinaryResourceDAO.removeBinaryResource。"""
        from app.services.vault import template_attached_path, template_attached_fullname
        full_name = template_attached_fullname(workspace_id, template_id, file_name)
        db.execute(text(
            "UPDATE partmastertemplate SET attachedfile_fullname = NULL "
            "WHERE workspace_id = :ws AND id = :tid AND attachedfile_fullname = :fn"
        ), {"ws": workspace_id, "tid": template_id, "fn": full_name})
        br = db.query(BinaryResource).filter(
            BinaryResource.full_name == full_name).first()
        if br:
            db.delete(br)
        try:
            file_path = template_attached_path(workspace_id, template_id, file_name)
            if file_path.exists():
                file_path.unlink()
        except Exception:
            pass
        db.commit()

    def rename_template_file(self, db: Session, workspace_id: str,
                              template_id: str, old_name: str,
                              new_name: str) -> None:
        """重命名零件模板附件。对齐 Java ProductManagerBean.renameFileInTemplate。"""
        from app.services.vault import template_attached_path, template_attached_fullname
        old_full = template_attached_fullname(workspace_id, template_id, old_name)
        new_full = template_attached_fullname(workspace_id, template_id, new_name)
        br = db.query(BinaryResource).filter(
            BinaryResource.full_name == old_full).first()
        if br:
            br.full_name = new_full
        db.execute(text(
            "UPDATE partmastertemplate SET attachedfile_fullname = :new_fn "
            "WHERE workspace_id = :ws AND id = :tid AND attachedfile_fullname = :old_fn"
        ), {"ws": workspace_id, "tid": template_id, "old_fn": old_full, "new_fn": new_full})
        try:
            old_path = template_attached_path(workspace_id, template_id, old_name)
            new_path = template_attached_path(workspace_id, template_id, new_name)
            if old_path.exists():
                new_path.parent.mkdir(parents=True, exist_ok=True)
                old_path.rename(new_path)
        except Exception:
            pass
        db.commit()

    def upload_template_file(self, db: Session, workspace_id: str,
                              template_id: str, file_name: str,
                              data: bytes) -> str:
        """上传零件模板附件。对齐 Java PartTemplateBinaryResource.saveFileInTemplate。"""
        import unicodedata
        from datetime import datetime
        from app.services.vault import template_attached_path, template_attached_fullname, write_file
        file_name = unicodedata.normalize("NFC", file_name)
        full_name = template_attached_fullname(workspace_id, template_id, file_name)
        file_path = template_attached_path(workspace_id, template_id, file_name)
        write_file(file_path, data)
        br = db.query(BinaryResource).filter(
            BinaryResource.full_name == full_name).first()
        now = datetime.utcnow()
        if br is None:
            br = BinaryResource(full_name=full_name, content_length=len(data),
                                last_modified=now, dtype="BinaryResource")
            db.add(br)
            db.flush()
        db.execute(text(
            "UPDATE partmastertemplate SET attachedfile_fullname = :fn "
            "WHERE workspace_id = :ws AND id = :tid"
        ), {"fn": full_name, "ws": workspace_id, "tid": template_id})
        db.commit()
        return file_name

    def read_template_file(self, db: Session, workspace_id: str,
                            template_id: str, file_name: str) -> tuple[bytes, Path]:
        """读取零件模板附件（返回 (数据, 磁盘路径)）。对齐 Java PartTemplateBinaryResource.getPartTemplateFile。"""
        from app.services.vault import template_attached_path, read_file
        file_path = template_attached_path(workspace_id, template_id, file_name)
        data = read_file(file_path)
        return data, file_path

    def _build_template_attrs(self, db: Session, workspace_id: str,
                               template_id: str) -> list[dict]:
        from sqlalchemy import text
        rows = db.execute(text(
            "SELECT iat.id, iat.name, iat.dtype, iat.mandatory, iat.locked, "
            "iat.attributetype, iat.lov_name, iat.lov_workspace_id, "
            "pta.attr_order "
            "FROM partmastertemplate_attr pta "
            "JOIN instanceattributetemplate iat ON iat.id = pta.instanceattributetemplate_id "
            "WHERE pta.workspace_id = :ws AND pta.partmastertemplate_id = :tid "
            "ORDER BY pta.attr_order"
        ), {"ws": workspace_id, "tid": template_id}).fetchall()
        return [{
            "id": row.id,
            "name": row.name,
            "dtype": row.dtype,
            "mandatory": row.mandatory,
            "locked": row.locked,
            "attributeType": row.attributetype,
            "lovName": row.lov_name,
            "lovWorkspaceId": row.lov_workspace_id,
            "attrOrder": row.attr_order,
        } for row in rows]

    def _build_instance_attr_templates(self, db: Session, workspace_id: str,
                                        template_id: str) -> list[dict]:
        from sqlalchemy import text
        rows = db.execute(text(
            "SELECT iat.id, iat.name, iat.dtype, iat.mandatory, iat.locked, "
            "iat.attributetype, iat.lov_name, iat.lov_workspace_id, pta.attr_order "
            "FROM instanceattributetemplate iat "
            "JOIN partmastertemplate_attr pta ON pta.instanceattributetemplate_id = iat.id "
            "WHERE pta.workspace_id = :ws AND pta.partmastertemplate_id = :tid "
            "ORDER BY pta.attr_order"
        ), {"ws": workspace_id, "tid": template_id}).fetchall()
        return [{
            "id": row.id,
            "name": row.name,
            "dtype": row.dtype,
            "mandatory": row.mandatory,
            "locked": row.locked,
            "attributeType": row.attributetype,
            "lovName": row.lov_name,
            "lovWorkspaceId": row.lov_workspace_id,
            "attrOrder": row.attr_order,
        } for row in rows]

    def _build_template_dto(self, db: Session, t, workspace_id: str) -> dict:
        from app.services.factory.acl_factory import build_acl_dict
        return {
            "id": t.id,
            "workspaceId": t.workspace_id,
            "mask": t.mask,
            "idGenerated": t.id_generated,
            "partType": t.part_type,
            "attributesLocked": t.attributes_locked,
            "author": self._get_template_account(db, t.author_login, t.author_workspace_id or t.workspace_id),
            "creationDate": t.creation_date.isoformat() if t.creation_date else None,
            "modificationDate": t.modification_date.isoformat() if t.modification_date else None,
            "acl": build_acl_dict(db, t.acl_id) or {},
            "workflowModelId": t.workflowmodel_id,
            "attributeTemplates": self._build_template_attrs(db, workspace_id, t.id),
            "attributeInstanceTemplates": self._build_instance_attr_templates(db, workspace_id, t.id),
            "attachedFile": self._list_template_files(db, workspace_id, t.id),
        }

    def list_part_templates(self, db: Session, workspace_id: str) -> list:
        from app.models.product.part_master_template import PartMasterTemplate
        templates = (
            db.query(PartMasterTemplate)
            .filter(PartMasterTemplate.workspace_id == workspace_id)
            .all()
        )
        return [self._build_template_dto(db, t, workspace_id) for t in templates]

    def get_part_template(self, db: Session, workspace_id: str,
                          template_id: str) -> dict:
        from app.models.product.part_master_template import PartMasterTemplate
        from app.core.exceptions import PartMasterTemplateNotFoundException
        t = (
            db.query(PartMasterTemplate)
            .filter(PartMasterTemplate.workspace_id == workspace_id,
                    PartMasterTemplate.id == template_id)
            .first()
        )
        if t is None:
            raise PartMasterTemplateNotFoundException("PartMasterTemplateNotFoundException", template_id)
        return self._build_template_dto(db, t, workspace_id)

    def create_part_template(self, db: Session, workspace_id: str,
                              body: dict, user_login: str) -> dict:
        from app.models.product.part_master_template import PartMasterTemplate
        from app.core.exceptions import PartMasterTemplateAlreadyExistsException
        template_id = body.get("reference") or body.get("id") or ""
        existing = (
            db.query(PartMasterTemplate)
            .filter(PartMasterTemplate.workspace_id == workspace_id,
                    PartMasterTemplate.id == template_id)
            .first()
        )
        if existing:
            raise PartMasterTemplateAlreadyExistsException(
                "PartMasterTemplateAlreadyExistsException", template_id)
        t = PartMasterTemplate(
            id=template_id,
            workspace_id=workspace_id,
            mask=body.get("mask", ""),
            id_generated=body.get("idGenerated", False),
            part_type=body.get("partType", ""),
            attributes_locked=body.get("attributesLocked", False),
            author_login=user_login,
            author_workspace_id=workspace_id,
            creation_date=datetime.utcnow(),
            modification_date=datetime.utcnow(),
            acl_id=body.get("aclId"),
            workflowmodel_id=body.get("workflowModelId"),
        )
        db.add(t)
        db.commit()
        return self._build_template_dto(db, t, workspace_id)

    def update_part_template(self, db: Session, workspace_id: str,
                              template_id: str, body: dict) -> dict:
        from app.models.product.part_master_template import PartMasterTemplate
        from app.core.exceptions import PartMasterTemplateNotFoundException
        t = (
            db.query(PartMasterTemplate)
            .filter(PartMasterTemplate.workspace_id == workspace_id,
                    PartMasterTemplate.id == template_id)
            .first()
        )
        if t is None:
            raise PartMasterTemplateNotFoundException("PartMasterTemplateNotFoundException", template_id)
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
        return self._build_template_dto(db, t, workspace_id)

    def delete_part_template(self, db: Session, workspace_id: str,
                              template_id: str) -> None:
        from app.models.product.part_master_template import PartMasterTemplate
        from app.core.exceptions import PartMasterTemplateNotFoundException
        t = (
            db.query(PartMasterTemplate)
            .filter(PartMasterTemplate.workspace_id == workspace_id,
                    PartMasterTemplate.id == template_id)
            .first()
        )
        if t is None:
            raise PartMasterTemplateNotFoundException("PartMasterTemplateNotFoundException", template_id)
        db.delete(t)
        db.commit()

    def _mask_to_sql_like(self, mask: str) -> str:
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

    def _parse_id_with_mask(self, id_str: str, mask: str) -> str | None:
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

    def _increment_masked_value(self, value: str, mask: str) -> str | None:
        mask_vars = [(i, ch) for i, ch in enumerate(mask) if ch in ('#', '*')]
        if not mask_vars:
            return None
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
            return None
        return ''.join(result)

    def _first_id_from_mask(self, mask: str) -> str:
        result = []
        for ch in mask:
            if ch == '#':
                result.append('0')
            elif ch == '*':
                result.append('A')
            else:
                result.append(ch)
        return ''.join(result)

    def _generate_from_mask(self, db: Session, workspace_id: str, mask: str) -> str:
        like_pattern = self._mask_to_sql_like(mask)
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
            val = self._parse_id_with_mask(number, mask)
            if val is not None:
                last_valid = number
                break
        if last_valid is not None:
            new_id = self._increment_masked_value(last_valid, mask)
            if new_id is not None:
                return new_id
            return self._first_id_from_mask(mask)
        return self._first_id_from_mask(mask)

    def _generate_from_template_id(self, db: Session, workspace_id: str,
                                    template_id: str) -> str:
        import re
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

    def generate_part_template_id(self, db: Session, workspace_id: str,
                                   template_id: str) -> str:
        from app.models.product.part_master_template import PartMasterTemplate
        from app.core.exceptions import PartMasterTemplateNotFoundException
        t = (
            db.query(PartMasterTemplate)
            .filter(PartMasterTemplate.workspace_id == workspace_id,
                    PartMasterTemplate.id == template_id)
            .first()
        )
        if t is None:
            raise PartMasterTemplateNotFoundException("PartMasterTemplateNotFoundException", template_id)
        mask = t.mask
        if mask:
            return self._generate_from_mask(db, workspace_id, mask)
        return self._generate_from_template_id(db, workspace_id, template_id)

    def update_part_template_acl(self, db: Session, workspace_id: str,
                                  template_id: str, body: dict) -> int:
        from app.models.product.part_master_template import PartMasterTemplate
        from app.core.exceptions import PartMasterTemplateNotFoundException
        from app.services.factory.acl_factory import apply_acl
        t = (
            db.query(PartMasterTemplate)
            .filter(PartMasterTemplate.workspace_id == workspace_id,
                    PartMasterTemplate.id == template_id)
            .first()
        )
        if t is None:
            raise PartMasterTemplateNotFoundException("PartMasterTemplateNotFoundException", template_id)
        user_entries = body.get("userEntries", {})
        group_entries = body.get("groupEntries", {})
        new_acl_id = apply_acl(db, t.acl_id, user_entries, group_entries,
                               workspace_id=workspace_id)
        if t.acl_id != new_acl_id:
            t.acl_id = new_acl_id
            db.commit()
        return new_acl_id

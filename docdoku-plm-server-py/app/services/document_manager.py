from datetime import datetime
from sqlalchemy import text as sql_text
from app.models.document import (
    DocumentMaster, DocumentRevision, DocumentIteration,
    DocumentMasterTemplate, Folder, document_iteration_binres,
    document_revision_tags,
)
from app.core.exceptions import (
    AccessRightException,
    EntityAlreadyExistsException, EntityConstraintException,
    NotAllowedException, EntityNotFoundException,
    DocumentMasterTemplateNotFoundException,
    DocumentRevisionNotFoundException,
    FileAlreadyExistsException, FileNotFoundException,
    DocumentRevisionAlreadyExistsException, FolderNotFoundException,
)
from app.services.indexer_manager import indexer_manager
from app.models.auth import Account
from app.models.security import ACL, AclUserEntry, AclUserGroupEntry


class DocumentService:

    @staticmethod
    def _validate_mask(mask: str, value: str) -> bool:
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

    def get_revision(self, db, ws, doc_id, ver):
        pr = db.query(DocumentRevision).filter(
            DocumentRevision.workspace_id == ws,
            DocumentRevision.documentmaster_id == doc_id,
            DocumentRevision.version == ver,
        ).first()
        if pr is None:
            raise DocumentRevisionNotFoundException("DocumentRevisionNotFoundException", doc_id, ver)
        return pr

    def count_documents(self, db, ws):
        return db.query(DocumentRevision).filter(
            DocumentRevision.workspace_id == ws,
        ).count()

    def list_revisions(self, db, ws, start=0, length=50):
        return db.query(DocumentRevision).filter(
            DocumentRevision.workspace_id == ws,
        ).order_by(DocumentRevision.documentmaster_id,
                   DocumentRevision.version).offset(start).limit(length).all()

    def create_document(self, db, ws, doc_id, title, user_login,
                         folder_path=None, template_id=None, workflow_model_id=None,
                         role_mapping=None, description=None,
                         user_entries=None, user_group_entries=None):
        from app.services.factory.acl_factory import check_write_access
        if not check_write_access(db, None, user_login, False, workspace_id=ws):
            raise AccessRightException("AccessRightException", user_login)
        existing = db.query(DocumentMaster).filter(
            DocumentMaster.workspace_id == ws,
            DocumentMaster.id == doc_id,
        ).first()
        if existing:
            raise EntityAlreadyExistsException(
                "DocumentMasterAlreadyExistsException", doc_id)
        now = datetime.utcnow()
        location = folder_path or ws
        master = DocumentMaster(
            id=doc_id, workspace_id=ws, creation_date=now,
            author_workspace_id=ws, author_login=user_login)
        if template_id:
            tpl = self.get_template(db, ws, template_id)
            if not self._validate_mask(tpl.mask or "", doc_id):
                raise NotAllowedException("NotAllowedException42")
            if tpl.id_generated and tpl.mask:
                import re
                prefix = re.sub(r'\{[^}]*\}', '', tpl.mask)
                like_pattern = re.escape(prefix) + '%'
                rows = db.execute(sql_text(
                    "SELECT id FROM documentmaster WHERE workspace_id=:ws AND id LIKE :pat"
                ), {"ws": ws, "pat": like_pattern}).fetchall()
                max_seq = 0
                for r in rows:
                    try:
                        seq_num = int(r[0][len(prefix):])
                        max_seq = max(max_seq, seq_num)
                    except ValueError:
                        pass
                next_seq = max_seq + 1
                doc_id = re.sub(r'\{[^}]*\}', str(next_seq).zfill(3), tpl.mask)
                master.id = doc_id
            master.type = tpl.document_type
            master.attributes_locked = tpl.attributes_locked
        else:
            master.type = ""
        db.add(master); db.flush()
        rev = DocumentRevision(
            workspace_id=ws, documentmaster_id=doc_id, version="A",
            title=title, status=0, creation_date=now,
            location_completepath=location,
            author_workspace_id=ws, author_login=user_login,
            checkout_user_workspace_id=ws, checkout_user_login=user_login,
            check_out_date=now)
        if description:
            rev.description = description
        if workflow_model_id:
            from app.services.workflow_manager import workflow_service
            workflow = workflow_service.instantiate_workflow(
                db, ws, workflow_model_id, role_mapping=role_mapping or {}
            )
            rev.workflow_id = workflow["workflowId"]
        db.add(rev); db.flush()
        it = DocumentIteration(
            workspace_id=ws, documentmaster_id=doc_id,
            documentrevision_version="A", iteration=1,
            creation_date=now, author_workspace_id=ws,
            author_login=user_login)
        db.add(it); db.flush()

        if template_id:
            self._copy_template_instance_attrs(db, ws, template_id, doc_id)
            self._copy_template_files(db, ws, template_id, doc_id)

        if user_entries or user_group_entries:
            from app.services.factory.acl_factory import apply_acl
            acl_id = getattr(rev, "acl_id", None)
            new_acl_id = apply_acl(db, acl_id or None, user_entries or {}, user_group_entries or {})
            if getattr(rev, "acl_id", None) != new_acl_id:
                rev.acl_id = new_acl_id

        db.commit(); db.refresh(rev)
        return rev

    def delete_revision(self, db, ws, doc_id, ver, user_login):
        from app.services.factory.acl_factory import check_write_access
        pr = self.get_revision(db, ws, doc_id, ver)
        if not check_write_access(db, pr.acl_id, user_login, False, workspace_id=ws):
            raise AccessRightException("AccessRightException", user_login)

        # 管理员跳过 home 文件夹检查
        from sqlalchemy import text as _text
        is_admin = db.scalar(_text(
            "SELECT COUNT(*) FROM usergroupmapping WHERE login=:l AND groupname='admin'"
        ), {"l": user_login}) or 0
        if not is_admin and self._is_in_another_user_home(user_login, ws, pr.location_completepath):
            raise NotAllowedException("NotAllowedException22")

        from sqlalchemy import text

        # 1. baseline 约束检查
        in_baseline = db.execute(text(
            "SELECT COUNT(*) FROM baselineddocument "
            "WHERE target_workspace_id=:ws "
            "AND target_documentmaster_id=:did "
            "AND target_docrevision_version=:ver"),
            {"ws": ws, "did": doc_id, "ver": ver},
        ).scalar()
        if in_baseline:
            raise EntityConstraintException("EntityConstraintException6")

        # 循环检查所有 revision 上的逆链接（对齐 Java 外层 for）
        master = pr.document_master
        for rev in master.revisions:
            # 2. inverse document links: 其他文档迭代引用此 revision
            inv_doc = db.execute(text(
                "SELECT COUNT(*) FROM documentlink "
                "WHERE target_workspace_id=:ws "
                "AND target_documentmaster_id=:did "
                "AND target_docrevision_version=:ver"),
                {"ws": ws, "did": rev.documentmaster_id, "ver": rev.version},
            ).scalar()
            if inv_doc:
                raise EntityConstraintException("EntityConstraintException17")

            # 3. inverse part links
            inv_part = db.execute(text(
                "SELECT COUNT(*) FROM partiteration_documentlink pidl "
                "JOIN documentlink dl ON pidl.documentlink_id = dl.id "
                "WHERE dl.target_workspace_id=:ws "
                "AND dl.target_documentmaster_id=:did "
                "AND dl.target_docrevision_version=:ver"),
                {"ws": ws, "did": rev.documentmaster_id, "ver": rev.version},
            ).scalar()
            if inv_part:
                raise EntityConstraintException("EntityConstraintException18")

            # 4. inverse product instance links
            inv_pinst = db.execute(text(
                "SELECT COUNT(*) FROM prdinstiteration_documentlink pidl "
                "JOIN documentlink dl ON pidl.documentlink_id = dl.id "
                "WHERE dl.target_workspace_id=:ws "
                "AND dl.target_documentmaster_id=:did "
                "AND dl.target_docrevision_version=:ver"),
                {"ws": ws, "did": rev.documentmaster_id, "ver": rev.version},
            ).scalar()
            if inv_pinst:
                raise EntityConstraintException("EntityConstraintException19")

            # 5. inverse path data links
            inv_path = db.execute(text(
                "SELECT COUNT(*) FROM pathdataiteration_documentlink pdl "
                "JOIN documentlink dl ON pdl.documentlink_id = dl.id "
                "WHERE dl.target_workspace_id=:ws "
                "AND dl.target_documentmaster_id=:did "
                "AND dl.target_docrevision_version=:ver"),
                {"ws": ws, "did": rev.documentmaster_id, "ver": rev.version},
            ).scalar()
            if inv_path:
                raise EntityConstraintException("EntityConstraintException20")

        # 6. change items（仅检查被删除的 revision，对齐 Java pDocRPK）
        has_change = db.execute(text(
            "SELECT 1 FROM changeissue_affected_document "
            "WHERE documentmaster_workspace_id=:ws "
            "AND documentmaster_id=:did "
            "AND documentrevision_version=:ver "
            "UNION ALL SELECT 1 FROM changeorder_affected_document "
            "WHERE documentmaster_workspace_id=:ws "
            "AND documentmaster_id=:did "
            "AND documentrevision_version=:ver "
            "UNION ALL SELECT 1 FROM changereq_affected_document "
            "WHERE documentmaster_workspace_id=:ws "
            "AND documentmaster_id=:did "
            "AND documentrevision_version=:ver "
            "LIMIT 1"),
            {"ws": ws, "did": doc_id, "ver": ver},
        ).scalar()
        if has_change is not None:
            raise EntityConstraintException("EntityConstraintException7")

        # 清理 vault 物理文件（对齐 product_manager.delete_revision）
        try:
            import shutil
            from pathlib import Path
            from app.core.config import settings
            for it in pr.iterations:
                vault_dir = Path(settings.VAULT_PATH) / ws / "documents" / doc_id / ver / str(it.iteration)
                if vault_dir.exists():
                    shutil.rmtree(vault_dir)
        except Exception:
            pass

        indexer_manager.delete_document_revision(pr)  # 对标 deleteDocumentRevision:1231

        # 获取需清理的 ID（在删除 revision 前获取）
        _workflow_id = pr.workflow_id
        _acl_id = pr.acl_id

        # 清理共享实体（对齐 Java removeRevision → sharedEntityDAO.deleteSharesForDocument）
        db.execute(text(
            "DELETE FROM sharedentity "
            "WHERE entity_workspace_id=:ws "
            "AND documentmaster_id=:did "
            "AND documentrevision_version=:ver"),
            {"ws": ws, "did": doc_id, "ver": ver})

        # 清理订阅（对齐 Java removeRevision → subscriptionDAO.removeAllSubscriptions）
        db.execute(text(
            "DELETE FROM statechangesubscription "
            "WHERE documentmaster_workspace_id=:ws "
            "AND documentmaster_id=:did "
            "AND documentrevision_version=:ver"),
            {"ws": ws, "did": doc_id, "ver": ver})
        db.execute(text(
            "DELETE FROM iterationchangesubscription "
            "WHERE documentmaster_workspace_id=:ws "
            "AND documentmaster_id=:did "
            "AND documentrevision_version=:ver"),
            {"ws": ws, "did": doc_id, "ver": ver})

        # 清理终止工作流关联（对齐 Java removeRevision → workflowDAO.removeWorkflowConstraints）
        db.execute(text(
            "DELETE FROM document_aborted_workflow "
            "WHERE documentmaster_workspace_id=:ws "
            "AND documentmaster_id=:did "
            "AND documentrevision_version=:ver"),
            {"ws": ws, "did": doc_id, "ver": ver})

        # 清理文档迭代的文档链接（对齐 Java removeRevision → documentDAO.removeDoc 的
        # DocumentIteration.linkedDocuments orphanRemoval 级联：仅删本 revision 迭代拥有的
        # documentlink，逐个 id 精确删除，不做全局清理——documentlink.id 被 4 张迭代表引用
        # 全部 NO ACTION，全局 NOT IN 会误删其它实体的链接）
        old_dl_ids = [r[0] for r in db.execute(text(
            "SELECT documentlink_id FROM documentiteration_documentlink "
            "WHERE workspace_id=:ws AND documentmaster_id=:did "
            "AND documentrevision_version=:ver"),
            {"ws": ws, "did": doc_id, "ver": ver}).fetchall()]
        db.execute(text(
            "DELETE FROM documentiteration_documentlink "
            "WHERE workspace_id=:ws "
            "AND documentmaster_id=:did "
            "AND documentrevision_version=:ver"),
            {"ws": ws, "did": doc_id, "ver": ver})
        for dl_id in old_dl_ids:
            still = db.execute(text(
                "SELECT 1 FROM documentiteration_documentlink WHERE documentlink_id=:id LIMIT 1"
            ), {"id": dl_id}).first()
            if not still:
                db.execute(text("DELETE FROM documentlink WHERE id=:id"), {"id": dl_id})

        # 清理文档迭代的属性（对齐 Java DocumentIteration.instanceAttributes 的
        # orphanRemoval+CascadeType.ALL 级联：仅删本 revision 迭代拥有的 instanceattribute，
        # 逐个 id 精确删除——instanceattribute.id 被 5 张表引用全部 NO ACTION，全局 NOT IN
        # 会漏 prdinstiteration_attribute/pathdataiteration_attribute 导致 FK 500，
        # 且需先删 LOV 子值 attribute_namevalue）
        old_attr_ids = [r[0] for r in db.execute(text(
            "SELECT instanceattribute_id FROM documentiteration_attribute "
            "WHERE workspace_id=:ws AND documentmaster_id=:did "
            "AND documentrevision_version=:ver"),
            {"ws": ws, "did": doc_id, "ver": ver}).fetchall()]
        db.execute(text(
            "DELETE FROM documentiteration_attribute "
            "WHERE workspace_id=:ws "
            "AND documentmaster_id=:did "
            "AND documentrevision_version=:ver"),
            {"ws": ws, "did": doc_id, "ver": ver})
        for attr_id in old_attr_ids:
            still = db.execute(text(
                "SELECT 1 FROM documentiteration_attribute WHERE instanceattribute_id=:id LIMIT 1"
            ), {"id": attr_id}).first()
            if not still:
                # 先删 LOV 子值（InstanceListOfValuesAttribute.items → attribute_namevalue）
                db.execute(text("DELETE FROM attribute_namevalue WHERE attribute_id=:id"), {"id": attr_id})
                db.execute(text("DELETE FROM instanceattribute WHERE id=:id"), {"id": attr_id})

        # 清理关联表
        db.execute(text(
            "DELETE FROM documentrevision_tag "
            "WHERE documentmaster_workspace_id=:ws "
            "AND documentmaster_id=:did "
            "AND documentrevision_version=:ver"),
            {"ws": ws, "did": doc_id, "ver": ver})
        db.execute(text(
            "DELETE FROM documentiteration_binres "
            "WHERE workspace_id=:ws "
            "AND documentmaster_id=:did "
            "AND documentrevision_version=:ver"),
            {"ws": ws, "did": doc_id, "ver": ver})
        db.execute(text(
            "DELETE FROM documentiteration "
            "WHERE workspace_id=:ws "
            "AND documentmaster_id=:did "
            "AND documentrevision_version=:ver"),
            {"ws": ws, "did": doc_id, "ver": ver})

        # 删除 revision，如为最后一个 revision 则连 master 一起删
        is_last_revision = len(master.revisions) == 1
        db.execute(text(
            "DELETE FROM documentrevision "
            "WHERE workspace_id=:ws "
            "AND documentmaster_id=:did "
            "AND version=:ver"),
            {"ws": ws, "did": doc_id, "ver": ver})
        if is_last_revision:
            db.execute(text(
                "DELETE FROM documentmaster "
                "WHERE workspace_id=:ws AND id=:did"),
                {"ws": ws, "did": doc_id})

        # 删除 ACL（在 revision 已删除后，对齐 Java deleteDocumentRevision → JPA cascade）
        if _acl_id is not None:
            db.execute(text(
                "DELETE FROM acluserentry WHERE acl_id=:aid"), {"aid": _acl_id})
            db.execute(text(
                "DELETE FROM aclusergroupentry WHERE acl_id=:aid"), {"aid": _acl_id})
            ref_count = db.execute(text("""
                SELECT COUNT(*) FROM (
                    SELECT 1 FROM partrevision       WHERE acl_id=:aid
                    UNION ALL SELECT 1 FROM workflowmodel        WHERE acl_id=:aid
                    UNION ALL SELECT 1 FROM changeissue          WHERE acl_id=:aid
                    UNION ALL SELECT 1 FROM changeorder          WHERE acl_id=:aid
                    UNION ALL SELECT 1 FROM changerequest         WHERE acl_id=:aid
                    UNION ALL SELECT 1 FROM milestone            WHERE acl_id=:aid
                    UNION ALL SELECT 1 FROM productconfiguration  WHERE acl_id=:aid
                    UNION ALL SELECT 1 FROM productinstancemaster WHERE acl_id=:aid
                    UNION ALL SELECT 1 FROM documentmastertemplate WHERE acl_id=:aid
                    UNION ALL SELECT 1 FROM partmastertemplate    WHERE acl_id=:aid
                ) t
            """), {"aid": _acl_id}).scalar()
            if not ref_count:
                db.execute(text("DELETE FROM acl WHERE id=:aid"), {"aid": _acl_id})
        db.commit()

    def _is_in_another_user_home(self, user_login, ws, location_path):
        """判断文档是否在其他用户的 home 文件夹中。"""
        if not location_path:
            return False
        user_prefix = f"{ws}/users/"
        if not location_path.startswith(user_prefix):
            return False
        # 提取 home 文件夹的 owner 用户名
        rest = location_path[len(user_prefix):]
        owner = rest.split("/")[0] if "/" in rest else rest
        return owner != user_login

    def checkout(self, db, ws, doc_id, ver, user_login):
        from app.services.factory.acl_factory import check_write_access
        pr = self.get_revision(db, ws, doc_id, ver)
        if not check_write_access(db, pr.acl_id, user_login, False, workspace_id=ws):
            raise AccessRightException("AccessRightException", user_login)
        if pr.checkout_user_login and pr.checkout_user_login != user_login:
            raise NotAllowedException("NotAllowedException37")
        if pr.status != 0:
            raise NotAllowedException("NotAllowedException47")
        now = datetime.utcnow()
        previous_iteration = pr.last_iteration
        last = pr.last_iteration_number + 1
        new_it = DocumentIteration(
            workspace_id=ws, documentmaster_id=doc_id,
            documentrevision_version=ver, iteration=last,
            creation_date=now, author_workspace_id=ws,
            author_login=user_login)
        db.add(new_it)
        # 先 flush 新迭代行，确保后续 _copy_* 的裸 SQL INSERT 能满足外键（session autoflush=False）
        db.flush()
        pr.checkout_user_login = user_login
        pr.checkout_user_workspace_id = ws
        pr.check_out_date = now
        # 复制上一迭代的 attached_files / linkedDocuments / instanceAttributes 到新迭代（深拷贝，对齐 Java checkOutDocument:942-956）
        if previous_iteration:
            self._copy_attached_files(db, ws, doc_id, ver,
                                      previous_iteration.iteration,
                                      new_it.iteration)
            self._copy_linked_documents(db, ws, doc_id, ver,
                                        previous_iteration.iteration,
                                        ver, new_it.iteration)
            self._copy_instance_attributes(db, ws, doc_id, ver,
                                           previous_iteration.iteration,
                                           ver, new_it.iteration)
        db.commit(); db.refresh(pr)
        return pr

    def _copy_attached_files(self, db, ws, doc_id, ver, src_iter, dst_iter):
        """将 src_iter 的 attached_files 深拷贝到 dst_iter（含 BinaryResource + vault）。"""
        import shutil
        from pathlib import Path
        from app.core.config import settings
        from app.models.part import BinaryResource
        from sqlalchemy import text

        rows = db.execute(text(
            "SELECT attachedfile_fullname FROM documentiteration_binres "
            "WHERE workspace_id=:ws AND documentmaster_id=:did "
            "AND documentrevision_version=:ver AND iteration=:iter"),
            {"ws": ws, "did": doc_id, "ver": ver, "iter": src_iter},
        ).fetchall()

        vault_root = Path(settings.VAULT_PATH)

        for row in rows:
            old_full = row[0]
            parts = old_full.split("/")
            if len(parts) >= 5:
                parts[4] = str(dst_iter)
            new_full = "/".join(parts)

            old_br = db.query(BinaryResource).filter(
                BinaryResource.full_name == old_full).first()
            if old_br:
                existing = db.query(BinaryResource).filter(
                    BinaryResource.full_name == new_full).first()
                if existing is None:
                    db.add(BinaryResource(
                        full_name=new_full,
                        dtype="BinaryResource",
                        content_length=old_br.content_length,
                        last_modified=datetime.utcnow(),
                        quality=old_br.quality,
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

            db.execute(document_iteration_binres.insert().values(
                workspace_id=ws, documentmaster_id=doc_id,
                documentrevision_version=ver, iteration=dst_iter,
                attachedfile_fullname=new_full))

    _ATTR_TYPE_MAP = {
        0: "InstanceTextAttribute",
        1: "InstanceNumberAttribute",
        2: "InstanceDateAttribute",
        3: "InstanceBooleanAttribute",
        4: "InstanceURLAttribute",
        5: "InstanceLongTextAttribute",
    }

    def _copy_template_instance_attrs(self, db, ws, template_id, doc_id):
        rows = db.execute(sql_text(
            "SELECT iat.id, iat.name, iat.mandatory, iat.locked, iat.attributetype "
            "FROM instanceattributetemplate iat "
            "JOIN documentmastertemplate_attr dta "
            "  ON dta.instanceattributetemplate_id = iat.id "
            "WHERE dta.workspace_id=:ws AND dta.documentmastertemplate_id=:tid "
            "ORDER BY dta.attr_order"
        ), {"ws": ws, "tid": template_id}).fetchall()
        for order, row in enumerate(rows):
            attr_type = row[4] if row[4] is not None else 0
            dtype = self._ATTR_TYPE_MAP.get(attr_type, "InstanceTextAttribute")
            result = db.execute(sql_text(
                "INSERT INTO instanceattribute "
                "(dtype, name, mandatory, locked) "
                "VALUES (:dtype, :name, :mand, :locked) RETURNING id"
            ), {"dtype": dtype, "name": row[1],
                "mand": row[2] or False, "locked": row[3] or False})
            attr_id = result.fetchone()[0]
            db.execute(sql_text(
                "INSERT INTO documentiteration_attribute "
                "(workspace_id, documentmaster_id, documentrevision_version, "
                "iteration, instanceattribute_id, attribute_order) "
                "VALUES (:ws, :did, :ver, :iter, :aid, :order)"
            ), {"ws": ws, "did": doc_id, "ver": "A", "iter": 1,
                "aid": attr_id, "order": order})

    def _copy_template_files(self, db, ws, template_id, doc_id):
        import shutil
        from pathlib import Path
        from app.core.config import settings
        from app.models.part import BinaryResource
        rows = db.execute(sql_text(
            "SELECT attachedfile_fullname FROM documentmastertemplate_binres "
            "WHERE workspace_id=:ws AND documentmastertemplate_id=:tid"
        ), {"ws": ws, "tid": template_id}).fetchall()
        vault_root = Path(settings.VAULT_PATH)
        for row in rows:
            old_full = row[0]
            filename = old_full.rsplit("/", 1)[-1] if "/" in old_full else old_full
            new_full = f"{ws}/documents/{doc_id}/A/1/{filename}"
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
            db.execute(document_iteration_binres.insert().values(
                workspace_id=ws, documentmaster_id=doc_id,
                documentrevision_version="A", iteration=1,
                attachedfile_fullname=new_full))

    def _copy_linked_documents(self, db, ws, doc_id, src_ver, src_iter,
                               dst_ver, dst_iter):
        rows = db.execute(sql_text(
            "SELECT dl.id, dl.commentdata, dl.target_documentmaster_id, "
            "dl.target_docrevision_version, dl.target_workspace_id "
            "FROM documentlink dl "
            "JOIN documentiteration_documentlink didl ON didl.documentlink_id = dl.id "
            "WHERE didl.workspace_id=:ws AND didl.documentmaster_id=:did "
            "AND didl.documentrevision_version=:ver AND didl.iteration=:iter"
        ), {"ws": ws, "did": doc_id, "ver": src_ver, "iter": src_iter}).fetchall()
        for row in rows:
            existing = db.execute(sql_text(
                "SELECT id FROM documentlink "
                "WHERE target_workspace_id=:tws AND target_documentmaster_id=:tdm "
                "AND target_docrevision_version=:tdv AND commentdata=:cmt "
                "LIMIT 1"
            ), {"tws": row[4], "tdm": row[2], "tdv": row[3],
                "cmt": row[1] or ""}).first()
            if existing:
                link_id = existing[0]
            else:
                result = db.execute(sql_text(
                    "INSERT INTO documentlink "
                    "(commentdata, target_documentmaster_id, "
                    "target_docrevision_version, target_workspace_id) "
                    "VALUES (:cmt, :tdm, :tdv, :tws) RETURNING id"
                ), {"cmt": row[1] or "", "tdm": row[2],
                    "tdv": row[3], "tws": row[4]})
                link_id = result.fetchone()[0]
            # 检查目标迭代是否已存在同 link 引用，避免重复插入
            dup = db.execute(sql_text(
                "SELECT 1 FROM documentiteration_documentlink "
                "WHERE workspace_id=:ws AND documentmaster_id=:did "
                "AND documentrevision_version=:ver AND iteration=:iter "
                "AND documentlink_id=:lid LIMIT 1"
            ), {"ws": ws, "did": doc_id, "ver": dst_ver,
                "iter": dst_iter, "lid": link_id}).first()
            if not dup:
                db.execute(sql_text(
                    "INSERT INTO documentiteration_documentlink "
                    "(workspace_id, documentmaster_id, documentrevision_version, "
                    "iteration, documentlink_id) "
                    "VALUES (:ws, :did, :ver, :iter, :lid)"
                ), {"ws": ws, "did": doc_id, "ver": dst_ver,
                    "iter": dst_iter, "lid": link_id})

    def _copy_instance_attributes(self, db, ws, doc_id, src_ver, src_iter,
                                  dst_ver, dst_iter):
        rows = db.execute(sql_text(
            "SELECT ia.id, ia.dtype, ia.name, ia.mandatory, ia.locked, "
            "ia.booleanvalue, ia.datevalue, ia.indexvalue, ia.numbervalue, "
            "ia.textvalue, ia.longtextvalue, ia.urlvalue, "
            "dia.attribute_order "
            "FROM instanceattribute ia "
            "JOIN documentiteration_attribute dia "
            "  ON dia.instanceattribute_id = ia.id "
            "WHERE dia.workspace_id=:ws AND dia.documentmaster_id=:did "
            "AND dia.documentrevision_version=:ver AND dia.iteration=:iter "
            "ORDER BY dia.attribute_order"
        ), {"ws": ws, "did": doc_id, "ver": src_ver, "iter": src_iter}).fetchall()
        for row in rows:
            result = db.execute(sql_text(
                "INSERT INTO instanceattribute "
                "(dtype, name, mandatory, locked, "
                "booleanvalue, datevalue, indexvalue, numbervalue, "
                "textvalue, longtextvalue, urlvalue) "
                "VALUES (:dtype, :name, :mand, :locked, "
                ":bv, :dv, :iv, :nv, :tv, :ltv, :uv) RETURNING id"
            ), {
                "dtype": row[1] or "InstanceTextAttribute",
                "name": row[2], "mand": row[3] or False, "locked": row[4] or False,
                "bv": row[5], "dv": row[6], "iv": row[7], "nv": row[8],
                "tv": row[9], "ltv": row[10], "uv": row[11],
            })
            attr_id = result.fetchone()[0]
            db.execute(sql_text(
                "INSERT INTO documentiteration_attribute "
                "(workspace_id, documentmaster_id, documentrevision_version, "
                "iteration, instanceattribute_id, attribute_order) "
                "VALUES (:ws, :did, :ver, :iter, :aid, :order)"
            ), {"ws": ws, "did": doc_id, "ver": dst_ver,
                "iter": dst_iter, "aid": attr_id, "order": row[12] or 0})

    def _infer_doc_attr_dtype(self, attr: dict) -> str:
        """根据属性值字段推断 instanceattribute 的 JPA dtype 鉴别值。"""
        if attr.get("typeName"):
            return attr["typeName"]
        if attr.get("dtype"):
            return attr["dtype"]
        if attr.get("booleanValue") is not None:
            return "InstanceBooleanAttribute"
        if attr.get("dateValue") is not None:
            return "InstanceDateAttribute"
        if attr.get("numberValue") is not None:
            return "InstanceNumberAttribute"
        if attr.get("urlValue") is not None:
            return "InstanceURLAttribute"
        if attr.get("longTextValue") is not None:
            return "InstanceLongTextAttribute"
        return "InstanceTextAttribute"

    def checkin(self, db, ws, doc_id, ver, user_login):
        from app.services.factory.acl_factory import check_write_access
        pr = self.get_revision(db, ws, doc_id, ver)
        if not check_write_access(db, pr.acl_id, user_login, False, workspace_id=ws):
            raise AccessRightException("AccessRightException", user_login)
        if pr.checkout_user_login != user_login:
            raise NotAllowedException("NotAllowedException20")
        now = datetime.utcnow()
        last = pr.last_iteration
        if last:
            last.check_in_date = now
        pr.checkout_user_login = None
        pr.checkout_user_workspace_id = None
        pr.check_out_date = None
        db.commit(); db.refresh(pr)
        indexer_manager.index_document_revision(pr)  # 对标 checkInDocument:1094
        return pr

    def undo_checkout(self, db, ws, doc_id, ver, user_login):
        from app.services.factory.acl_factory import check_write_access
        pr = self.get_revision(db, ws, doc_id, ver)
        if not check_write_access(db, pr.acl_id, user_login, False, workspace_id=ws):
            raise AccessRightException("AccessRightException", user_login)
        if pr.checkout_user_login != user_login:
            # admin 可强制撤销他人签出（对齐 Java admin 可代操作）
            is_admin = db.scalar(sql_text(
                "SELECT COUNT(*) FROM usergroupmapping WHERE login=:l AND groupname='admin'"
            ), {"l": user_login}) or 0
            if not is_admin:
                raise NotAllowedException("NotAllowedException19")
        if len(pr.iterations) <= 1:
            raise NotAllowedException("NotAllowedException27")
        last = pr.last_iteration
        if last and last.check_in_date is None:
            last_iter_num = last.iteration
            # 清理 join 表 + 孤儿行，避免 db.delete(last) 时 FK 约束冲突
            # （Java 靠 JPA orphanRemoval 级联，Python 需手动清理裸 SQL 层的 join 表）
            did, rev, it = doc_id, ver, last_iter_num

            # 1. documentiteration_attribute + 孤儿 instanceattribute
            old_attr_ids = [r[0] for r in db.execute(sql_text(
                "SELECT instanceattribute_id FROM documentiteration_attribute "
                "WHERE workspace_id=:ws AND documentmaster_id=:did "
                "AND documentrevision_version=:ver AND iteration=:it"
            ), {"ws": ws, "did": did, "ver": rev, "it": it}).fetchall()]
            db.execute(sql_text(
                "DELETE FROM documentiteration_attribute "
                "WHERE workspace_id=:ws AND documentmaster_id=:did "
                "AND documentrevision_version=:ver AND iteration=:it"
            ), {"ws": ws, "did": did, "ver": rev, "it": it})
            for oid in old_attr_ids:
                still = db.execute(sql_text(
                    "SELECT 1 FROM documentiteration_attribute WHERE instanceattribute_id=:id LIMIT 1"
                ), {"id": oid}).first()
                if not still:
                    db.execute(sql_text("DELETE FROM instanceattribute WHERE id=:id"), {"id": oid})

            # 2. documentiteration_documentlink + 孤儿 documentlink
            old_dl_ids = [r[0] for r in db.execute(sql_text(
                "SELECT documentlink_id FROM documentiteration_documentlink "
                "WHERE workspace_id=:ws AND documentmaster_id=:did "
                "AND documentrevision_version=:ver AND iteration=:it"
            ), {"ws": ws, "did": did, "ver": rev, "it": it}).fetchall()]
            db.execute(sql_text(
                "DELETE FROM documentiteration_documentlink "
                "WHERE workspace_id=:ws AND documentmaster_id=:did "
                "AND documentrevision_version=:ver AND iteration=:it"
            ), {"ws": ws, "did": did, "ver": rev, "it": it})
            for dl_id in old_dl_ids:
                still = db.execute(sql_text(
                    "SELECT 1 FROM documentiteration_documentlink WHERE documentlink_id=:id LIMIT 1"
                ), {"id": dl_id}).first()
                if not still:
                    db.execute(sql_text("DELETE FROM documentlink WHERE id=:id"), {"id": dl_id})

            # 3. documentiteration_binres（join 表先行，BinaryResource 由后续 LIKE 删除覆盖）
            db.execute(sql_text(
                "DELETE FROM documentiteration_binres "
                "WHERE workspace_id=:ws AND documentmaster_id=:did "
                "AND documentrevision_version=:ver AND iteration=:it"
            ), {"ws": ws, "did": did, "ver": rev, "it": it})

            db.delete(last)
            db.flush()
            # 删除 BinaryResource 行（属于已删除迭代）
            from app.models.part import BinaryResource
            db.query(BinaryResource).filter(
                BinaryResource.full_name.like(
                    f"{ws}/documents/{doc_id}/{ver}/{last_iter_num}/%")
            ).delete(synchronize_session=False)
        pr.checkout_user_login = None
        pr.checkout_user_workspace_id = None
        pr.check_out_date = None
        db.commit(); db.refresh(pr)
        # 清理 vault 物理文件
        try:
            import shutil
            from pathlib import Path
            from app.core.config import settings
            vault_dir = Path(settings.VAULT_PATH) / ws / "documents" / doc_id / ver / str(last_iter_num)
            if vault_dir.exists():
                shutil.rmtree(vault_dir)
        except Exception:
            pass
        return pr

    def release(self, db, ws, doc_id, ver, user_login):
        from app.services.factory.acl_factory import check_write_access
        pr = self.get_revision(db, ws, doc_id, ver)
        if not check_write_access(db, pr.acl_id, user_login, False, workspace_id=ws):
            raise AccessRightException("AccessRightException", user_login)
        if pr.checkout_user_login:
            raise NotAllowedException("NotAllowedException63")
        if not pr.iterations:
            raise NotAllowedException("NotAllowedException27")
        if pr.status == 2:
            raise NotAllowedException("NotAllowedException64")
        pr.status = 1
        pr.release_date = datetime.utcnow()
        pr.release_user_login = user_login
        pr.release_user_workspace = ws
        db.commit(); db.refresh(pr)
        return pr

    def update_iteration(self, db, ws, doc_id, ver, iteration, data, user_login=None):
        """更新文档迭代的 revisionNote、linkedDocuments 等字段。"""
        di = db.query(DocumentIteration).filter(
            DocumentIteration.workspace_id == ws,
            DocumentIteration.documentmaster_id == doc_id,
            DocumentIteration.documentrevision_version == ver,
            DocumentIteration.iteration == iteration,
        ).first()
        if not di:
            raise EntityNotFoundException("DocumentIterationNotFoundException",
                                          doc_id, ver, str(iteration))
        if user_login is not None:
            pr = self.get_revision(db, ws, doc_id, ver)
            if pr.checkout_user_login != user_login:
                raise NotAllowedException("NotAllowedException25")
            if iteration != pr.last_iteration_number:
                raise NotAllowedException("NotAllowedException25")
        if data.get("revisionNote"):
            di.revisionnote = data["revisionNote"]
        linked_docs = data.get("linkedDocuments")
        if linked_docs is not None:
            di_modification_date = datetime.utcnow()
            # 清除现有链接文档
            db.execute(sql_text(
                "DELETE FROM documentiteration_documentlink "
                "WHERE workspace_id=:ws AND documentmaster_id=:did "
                "AND documentrevision_version=:ver AND iteration=:iter"
            ), {"ws": ws, "did": doc_id, "ver": ver, "iter": iteration})
            # 插入新链接文档
            for ld in linked_docs:
                result = db.execute(sql_text(
                    "INSERT INTO documentlink (commentdata, target_documentmaster_id, "
                    "target_docrevision_version, target_workspace_id) "
                    "VALUES (:comment, :dm, :drv, :tws) RETURNING id"
                ), {
                    "comment": ld.get("commentLink", ""),
                    "dm": ld.get("documentMasterId", ""),
                    "drv": ld.get("version", "A"),
                    "tws": ld.get("workspaceId", ws),
                })
                link_id = result.fetchone()[0]
                db.execute(sql_text(
                    "INSERT INTO documentiteration_documentlink "
                    "(workspace_id, documentmaster_id, documentrevision_version, "
                    "iteration, documentlink_id) "
                    "VALUES (:ws, :did, :ver, :iter, :lid)"
                ), {"ws": ws, "did": doc_id, "ver": ver, "iter": iteration, "lid": link_id})
            di.modification_date = di_modification_date
        instance_attrs = data.get("instanceAttributes")
        if instance_attrs is not None:
            # 查旧属性 id
            old_attr_ids = [r[0] for r in db.execute(sql_text(
                "SELECT instanceattribute_id FROM documentiteration_attribute "
                "WHERE workspace_id=:ws AND documentmaster_id=:did "
                "AND documentrevision_version=:ver AND iteration=:iter"
            ), {"ws": ws, "did": doc_id, "ver": ver, "iter": iteration}).fetchall()]
            # 删旧关联
            db.execute(sql_text(
                "DELETE FROM documentiteration_attribute "
                "WHERE workspace_id=:ws AND documentmaster_id=:did "
                "AND documentrevision_version=:ver AND iteration=:iter"
            ), {"ws": ws, "did": doc_id, "ver": ver, "iter": iteration})
            # 删孤儿 instanceattribute
            for oid in old_attr_ids:
                still = db.execute(sql_text(
                    "SELECT 1 FROM documentiteration_attribute WHERE instanceattribute_id=:id LIMIT 1"
                ), {"id": oid}).first()
                if not still:
                    db.execute(sql_text("DELETE FROM instanceattribute WHERE id=:id"), {"id": oid})
            # 插入新属性
            for order, attr in enumerate(instance_attrs):
                dtype = self._infer_doc_attr_dtype(attr)
                result = db.execute(sql_text(
                    "INSERT INTO instanceattribute "
                    "(dtype, name, mandatory, locked, "
                    "booleanvalue, datevalue, indexvalue, numbervalue, "
                    "textvalue, longtextvalue, urlvalue) "
                    "VALUES (:dtype, :name, :mand, :locked, "
                    ":bv, :dv, :iv, :nv, :tv, :ltv, :uv) RETURNING id"
                ), {
                    "dtype": dtype, "name": attr.get("name", ""),
                    "mand": attr.get("mandatory", False), "locked": attr.get("locked", False),
                    "bv": attr.get("booleanValue"), "dv": attr.get("dateValue"),
                    "iv": attr.get("indexValue"), "nv": attr.get("numberValue"),
                    "tv": attr.get("textValue"), "ltv": attr.get("longTextValue"),
                    "uv": attr.get("urlValue"),
                })
                new_id = result.fetchone()[0]
                db.execute(sql_text(
                    "INSERT INTO documentiteration_attribute "
                    "(workspace_id, documentmaster_id, documentrevision_version, "
                    "iteration, instanceattribute_id, attribute_order) "
                    "VALUES (:ws, :did, :ver, :iter, :aid, :order)"
                ), {"ws": ws, "did": doc_id, "ver": ver, "iter": iteration,
                    "aid": new_id, "order": order})
        db.commit()
        return di.revision

    def _ensure_last_revision(self, db, ws, doc_id, ver):
        """检查是否为文档的最新版本，否则抛出 NotAllowedException(72)。"""
        # 同名文档下版本号最大的即为最新版本
        last = db.query(DocumentRevision).filter(
            DocumentRevision.workspace_id == ws,
            DocumentRevision.documentmaster_id == doc_id,
        ).order_by(DocumentRevision.version.desc()).first()
        if last is None or last.version != ver:
            raise NotAllowedException("NotAllowedException72")

    def mark_obsolete(self, db, ws, doc_id, ver, user_login):
        pr = self.get_revision(db, ws, doc_id, ver)
        from app.services.factory.acl_factory import check_write_access
        if not check_write_access(db, pr.acl_id, user_login, False, workspace_id=ws):
            raise AccessRightException("AccessRightException", user_login)
        if pr.status != 1:
            raise NotAllowedException("NotAllowedException65")
        pr.status = 2
        pr.obsolete_date = datetime.utcnow()
        pr.obsolete_user_login = user_login
        pr.obsolete_user_workspace = ws
        db.commit(); db.refresh(pr)
        return pr

    def create_new_version(self, db, ws, doc_id, ver, user_login,
                            title=None, description=None, workflow_model_id=None,
                            user_entries=None, user_group_entries=None,
                            user_role_mapping=None, group_role_mapping=None):
        pr = self.get_revision(db, ws, doc_id, ver)
        if pr.checkout_user_login:
            raise NotAllowedException("NotAllowedException40")
        if not pr.iterations:
            raise NotAllowedException("NotAllowedException27")
        now = datetime.utcnow()
        new_ver = self._next_version(ver)
        existing_new = db.query(DocumentRevision).filter(
            DocumentRevision.workspace_id == ws,
            DocumentRevision.documentmaster_id == doc_id,
            DocumentRevision.version == new_ver,
        ).first()
        if existing_new is not None:
            raise DocumentRevisionAlreadyExistsException(
                "DocumentRevisionAlreadyExistsException", doc_id)
        new_title = title or pr.title
        new_description = description if description is not None else pr.description
        new_pr = DocumentRevision(
            workspace_id=ws, documentmaster_id=doc_id, version=new_ver,
            title=new_title, description=new_description, status=0,
            creation_date=now,
            location_completepath=pr.location_completepath,
            author_workspace_id=ws, author_login=user_login,
            checkout_user_workspace_id=ws, checkout_user_login=user_login,
            check_out_date=now)
        if user_entries or user_group_entries:
            from app.services.factory.acl_factory import apply_acl
            new_acl_id = apply_acl(db, None, user_entries, user_group_entries)
            new_pr.acl_id = new_acl_id
        db.add(new_pr); db.flush()
        new_it = DocumentIteration(
            workspace_id=ws, documentmaster_id=doc_id,
            documentrevision_version=new_ver, iteration=1,
            creation_date=now, author_workspace_id=ws,
            author_login=user_login)
        db.add(new_it); db.flush()

        last_iter = pr.last_iteration
        if last_iter:
            self._copy_attached_files(db, ws, doc_id, new_ver,
                                      last_iter.iteration, 1)
            self._copy_linked_documents(db, ws, doc_id, ver, last_iter.iteration,
                                        new_ver, 1)
            self._copy_instance_attributes(db, ws, doc_id, ver, last_iter.iteration,
                                           new_ver, 1)

        db.commit(); db.refresh(new_pr)
        return new_pr

    def _ensure_tag(self, db, ws, label):
        from app.models.part import Tag
        t = db.query(Tag).filter(Tag.workspace_id == ws,
                                 Tag.label == label).first()
        if t is None:
            db.add(Tag(workspace_id=ws, label=label)); db.flush()

    def set_tags(self, db, ws, doc_id, ver, labels, user_login):
        pr = self.get_revision(db, ws, doc_id, ver)
        from app.services.factory.acl_factory import check_write_access
        if not check_write_access(db, pr.acl_id, user_login, False, workspace_id=ws):
            raise AccessRightException("AccessRightException", user_login)
        db.execute(document_revision_tags.delete().where(
            document_revision_tags.c.documentmaster_workspace_id == ws,
            document_revision_tags.c.documentmaster_id == doc_id,
            document_revision_tags.c.documentrevision_version == ver,
        ))
        for label in labels:
            self._ensure_tag(db, ws, label)
            db.execute(document_revision_tags.insert().values(
                documentmaster_workspace_id=ws, documentmaster_id=doc_id,
                documentrevision_version=ver, tag_workspace_id=ws,
                tag_label=label))
        db.commit(); db.refresh(pr)
        indexer_manager.index_document_revision(pr)  # 对标 saveTags:1007
        return pr

    def add_tag(self, db, ws, doc_id, ver, label, user_login):
        pr = self.get_revision(db, ws, doc_id, ver)
        from app.services.factory.acl_factory import check_write_access
        if not check_write_access(db, pr.acl_id, user_login, False, workspace_id=ws):
            raise AccessRightException("AccessRightException", user_login)
        self._ensure_tag(db, ws, label)
        exists = db.execute(document_revision_tags.select().where(
            document_revision_tags.c.documentmaster_workspace_id == ws,
            document_revision_tags.c.documentmaster_id == doc_id,
            document_revision_tags.c.documentrevision_version == ver,
            document_revision_tags.c.tag_label == label,
        )).first()
        if exists is None:
            db.execute(document_revision_tags.insert().values(
                documentmaster_workspace_id=ws, documentmaster_id=doc_id,
                documentrevision_version=ver, tag_workspace_id=ws,
                tag_label=label))
        db.commit(); db.refresh(pr)
        return pr

    def remove_tag(self, db, ws, doc_id, ver, label, user_login):
        pr = self.get_revision(db, ws, doc_id, ver)
        from app.services.factory.acl_factory import check_write_access
        if not check_write_access(db, pr.acl_id, user_login, False, workspace_id=ws):
            raise AccessRightException("AccessRightException", user_login)
        db.execute(document_revision_tags.delete().where(
            document_revision_tags.c.documentmaster_workspace_id == ws,
            document_revision_tags.c.documentmaster_id == doc_id,
            document_revision_tags.c.documentrevision_version == ver,
            document_revision_tags.c.tag_label == label,
        ))
        db.commit(); db.refresh(pr)
        indexer_manager.index_document_revision(pr)  # 对标 removeTag:1033
        return pr

    def search(self, db, ws, title=None, doc_id=None):
        q = db.query(DocumentMaster).filter(
            DocumentMaster.workspace_id == ws)
        if title:
            q = q.filter(DocumentMaster.revisions.any(
                DocumentRevision.title.ilike(f"%{title}%")))
        if doc_id:
            q = q.filter(DocumentMaster.id.ilike(f"%{doc_id}%"))
        masters = q.limit(100).all()
        result = []
        for m in masters:
            result.extend(m.revisions)
        return result

    def resolve_es_document_keys(self, db, ws, keys: list):
        """解析 ES 返回的迭代级 key: '{docMId}-{version}-{iteration}' → DocumentRevision 列表（按 revision 去重）。"""
        from sqlalchemy.orm import joinedload
        from sqlalchemy import or_, and_
        seen = set()
        rev_keys = []
        for k in keys:
            parts = k.rsplit("-", 2)
            if len(parts) >= 2:
                dv = (parts[0], parts[1])
                if dv not in seen:
                    seen.add(dv)
                    rev_keys.append(dv)
        if not rev_keys:
            return []
        conditions = [
            (DocumentRevision.workspace_id == ws) &
            (DocumentRevision.documentmaster_id == dv[0]) &
            (DocumentRevision.version == dv[1])
            for dv in rev_keys
        ]
        revisions = db.query(DocumentRevision).options(
            joinedload(DocumentRevision.iterations),
        ).filter(or_(*conditions)).all()
        rev_map = {(dr.documentmaster_id, dr.version): dr for dr in revisions}
        return [rev_map[k] for k in rev_keys if k in rev_map]

    def search_documents_sql(self, db, ws, q=None, doc_id=None, title=None,
                               version=None, author=None, tags=None, content=None,
                               createdFrom=None, createdTo=None,
                               modifiedFrom=None, modifiedTo=None,
                               start=0, size=20):
        """SQL LIKE 回退搜索（ES 失败时使用），从 router 内联 DB 迁入。"""
        from sqlalchemy import or_, text as sql_text
        from datetime import datetime

        query = db.query(DocumentRevision).join(
            DocumentMaster,
            (DocumentRevision.workspace_id == DocumentMaster.workspace_id) &
            (DocumentRevision.documentmaster_id == DocumentMaster.id)
        ).filter(DocumentMaster.workspace_id == ws)
        if q:
            q_pattern = f"%{q}%"
            query = query.filter(or_(
                DocumentMaster.id.ilike(q_pattern),
                DocumentRevision.title.ilike(q_pattern),
            ))
        if doc_id:
            query = query.filter(DocumentMaster.id.ilike(f"%{doc_id}%"))
        if title:
            query = query.filter(DocumentRevision.title.ilike(f"%{title}%"))
        if version:
            query = query.filter(DocumentRevision.version == version)
        if author:
            query = query.filter(DocumentRevision.author_login == author)
        if tags:
            matched_ids = [row[0] for row in db.execute(sql_text(
                "SELECT dr.documentmaster_id FROM documentrevision dr "
                "JOIN documentrevision_tag t ON dr.documentmaster_id=t.documentmaster_id "
                "AND dr.version=t.documentrevision_version "
                "WHERE t.tag_label ILIKE :t AND dr.workspace_id=:w"
            ), {"t": f"%{tags}%", "w": ws}).fetchall()]
            query = query.filter(DocumentRevision.documentmaster_id.in_(matched_ids))
        if content:
            matched_ids = [row[0] for row in db.execute(sql_text(
                "SELECT DISTINCT di.documentmaster_id FROM documentiteration di "
                "WHERE di.workspace_id = :w AND di.revisionnote ILIKE :c"
            ), {"w": ws, "c": f"%{content}%"}).fetchall()]
            if matched_ids:
                query = query.filter(DocumentRevision.documentmaster_id.in_(matched_ids))
            else:
                query = query.filter(DocumentRevision.documentmaster_id == None)
        if createdFrom:
            cf = datetime.fromisoformat(createdFrom)
            query = query.filter(DocumentRevision.creation_date >= cf)
        if createdTo:
            ct = datetime.fromisoformat(createdTo)
            query = query.filter(DocumentRevision.creation_date <= ct)
        if modifiedFrom:
            mf = datetime.fromisoformat(modifiedFrom)
            matched_ids = [row[0] for row in db.execute(sql_text(
                "SELECT DISTINCT di.documentmaster_id FROM documentiteration di "
                "WHERE di.workspace_id = :w AND di.modificationdate >= :d"
            ), {"w": ws, "d": mf}).fetchall()]
            if matched_ids:
                query = query.filter(DocumentRevision.documentmaster_id.in_(matched_ids))
            else:
                query = query.filter(DocumentRevision.documentmaster_id == None)
        if modifiedTo:
            mt = datetime.fromisoformat(modifiedTo)
            matched_ids = [row[0] for row in db.execute(sql_text(
                "SELECT DISTINCT di.documentmaster_id FROM documentiteration di "
                "WHERE di.workspace_id = :w AND di.modificationdate <= :d"
            ), {"w": ws, "d": mt}).fetchall()]
            if matched_ids:
                query = query.filter(DocumentRevision.documentmaster_id.in_(matched_ids))
            else:
                query = query.filter(DocumentRevision.documentmaster_id == None)
        return query.order_by(DocumentMaster.id).offset(start).limit(size).all()

    def list_checked_out(self, db, ws):
        return db.query(DocumentRevision).filter(
            DocumentRevision.workspace_id == ws,
            DocumentRevision.checkout_user_login.isnot(None),
        ).all()

    def count_checked_out_documents(self, db, ws):
        return db.query(DocumentRevision).filter(
            DocumentRevision.workspace_id == ws,
            DocumentRevision.checkout_user_login.isnot(None),
        ).count()

    def move_document(self, db, ws, doc_id, ver, folder_path, user_login=None):
        """移动文档到指定文件夹（更新 location_completepath）。"""
        from app.services.factory.acl_factory import check_write_access
        pr = self.get_revision(db, ws, doc_id, ver)
        if user_login and not check_write_access(db, pr.acl_id, user_login, False, workspace_id=ws):
            raise AccessRightException("AccessRightException", user_login)
        pr.location_completepath = folder_path
        db.commit()
        db.refresh(pr)
        indexer_manager.index_document_revision(pr)  # 对标 moveDocumentRevision:880
        return pr

    def list_documents_in_folder(self, db, ws, folder_path):
        return db.query(DocumentRevision).filter(
            DocumentRevision.workspace_id == ws,
            DocumentRevision.location_completepath == folder_path,
        ).all()

    def create_folder(self, db, parent_path, name):
        completepath = f"{parent_path}/{name}" if parent_path else name
        existing = db.query(Folder).filter(
            Folder.completepath == completepath).first()
        if existing:
            raise EntityAlreadyExistsException(
                "FolderAlreadyExistsException", completepath)
        folder = Folder(completepath=completepath,
                        parentfolder_completepath=parent_path or None)
        db.add(folder); db.commit()
        return folder

    def list_folders(self, db, ws, parent_path=None):
        if parent_path:
            return db.query(Folder).filter(
                Folder.parentfolder_completepath == parent_path).all()
        # 只返回工作区根的直接子文件夹（对齐 Java getRootFolders）
        return db.query(Folder).filter(
            Folder.parentfolder_completepath == ws,
        ).order_by(Folder.completepath).all()

    def rename_folder(self, db, completepath, new_name):
        folder = db.query(Folder).filter(
            Folder.completepath == completepath).first()
        if folder is None:
            raise FolderNotFoundException("FolderNotFoundException", completepath)
        parent = folder.parentfolder_completepath or ""
        new_path = f"{parent}/{new_name}" if parent else new_name
        existing = db.query(Folder).filter(
            Folder.completepath == new_path).first()
        if existing:
            raise EntityAlreadyExistsException(
                "FolderAlreadyExistsException", new_path)
        # 更新自身和所有子文件夹路径
        old_prefix = folder.completepath
        rows = db.query(Folder).filter(
            Folder.completepath.like(f"{old_prefix}%")).all()
        for f in rows:
            f.completepath = f.completepath.replace(old_prefix, new_path, 1)
            if f.parentfolder_completepath:
                f.parentfolder_completepath = f.parentfolder_completepath.replace(
                    old_prefix, new_path, 1)
        db.commit()
        return folder

    def delete_folder(self, db, completepath, current_user_login=None):
        folder = db.query(Folder).filter(
            Folder.completepath == completepath).first()
        if folder is None:
            raise FolderNotFoundException("FolderNotFoundException", completepath)
        # 对齐 Java deleteFolder: isAnotherUserHomeFolder / isRoot / isHome 保护
        if current_user_login:
            if self._is_root_folder(completepath):
                raise NotAllowedException("NotAllowedException21")
            if self._is_home_folder(completepath):
                raise NotAllowedException("NotAllowedException21")
            if self._is_another_user_home_folder(current_user_login, completepath):
                raise NotAllowedException("NotAllowedException21")
        # 级联删除文件夹内所有文档
        docs = db.query(DocumentRevision).filter(
            DocumentRevision.location_completepath.like(f"{completepath}%")
        ).all()
        for doc in docs:
            self.delete_revision(db, doc.workspace_id, doc.documentmaster_id,
                                 doc.version, current_user_login or "")
        # 删除子文件夹及自身
        db.execute(sql_text("DELETE FROM folder WHERE completepath LIKE :path"),
                   {"path": f"{completepath}%"})
        db.commit()

    def list_templates(self, db, ws):
        return db.query(DocumentMasterTemplate).filter(
            DocumentMasterTemplate.workspace_id == ws).all()

    def get_template(self, db, ws, template_id):
        t = db.query(DocumentMasterTemplate).filter(
            DocumentMasterTemplate.workspace_id == ws,
            DocumentMasterTemplate.id == template_id).first()
        if t is None:
            raise DocumentMasterTemplateNotFoundException("DocumentMasterTemplateNotFoundException", template_id)
        return t

    def create_template(self, db, ws, template_id, document_type, mask,
                        id_generated, user_login, workflow_model_id=None,
                        attribute_templates=None, attributes_locked=False):
        existing = db.query(DocumentMasterTemplate).filter(
            DocumentMasterTemplate.workspace_id == ws,
            DocumentMasterTemplate.id == template_id).first()
        if existing:
            raise EntityAlreadyExistsException(
                "DocumentMasterTemplateAlreadyExistsException", template_id)
        now = datetime.utcnow()
        t = DocumentMasterTemplate(
            workspace_id=ws, id=template_id,
            document_type=document_type, mask=mask,
            id_generated=id_generated, creation_date=now,
            author_workspace_id=ws, author_login=user_login,
            workflowmodel_id=workflow_model_id,
            attributes_locked=attributes_locked)
        db.add(t); db.commit(); db.refresh(t)
        return t

    def delete_template(self, db, ws, template_id):
        from pathlib import Path
        from app.core.config import settings

        t = self.get_template(db, ws, template_id)

        br_rows = db.execute(sql_text(
            "SELECT attachedfile_fullname FROM documentmastertemplate_binres "
            "WHERE workspace_id=:ws AND documentmastertemplate_id=:tid"
        ), {"ws": ws, "tid": template_id}).fetchall()
        for (fullname,) in br_rows:
            db.execute(sql_text("DELETE FROM binaryresource WHERE fullname=:fn"),
                       {"fn": fullname})
            file_path = Path(settings.VAULT_PATH) / fullname
            if file_path.exists():
                try:
                    file_path.unlink()
                except OSError:
                    pass

        db.execute(sql_text(
            "DELETE FROM documentmastertemplate_binres "
            "WHERE workspace_id=:ws AND documentmastertemplate_id=:tid"
        ), {"ws": ws, "tid": template_id})

        iat_rows = db.execute(sql_text(
            "SELECT instanceattributetemplate_id FROM documentmastertemplate_attr "
            "WHERE workspace_id=:ws AND documentmastertemplate_id=:tid"
        ), {"ws": ws, "tid": template_id}).fetchall()

        db.execute(sql_text(
            "DELETE FROM documentmastertemplate_attr "
            "WHERE workspace_id=:ws AND documentmastertemplate_id=:tid"
        ), {"ws": ws, "tid": template_id})

        for (iat_id,) in iat_rows:
            db.execute(sql_text("DELETE FROM instanceattributetemplate WHERE id=:id"),
                       {"id": iat_id})

        if t.acl_id is not None:
            # 先删子表，两个 FK 均无 CASCADE
            db.execute(sql_text("DELETE FROM acluserentry WHERE acl_id=:acl_id"),
                       {"acl_id": t.acl_id})
            db.execute(sql_text("DELETE FROM aclusergroupentry WHERE acl_id=:acl_id"),
                       {"acl_id": t.acl_id})
            db.execute(sql_text("DELETE FROM acl WHERE id=:acl_id"),
                       {"acl_id": t.acl_id})

        db.delete(t)
        db.commit()

    def save_file(self, db, ws, doc_id, ver, iteration, filename, data,
                  user_login=None):
        if user_login:
            dr = db.query(DocumentRevision).filter(
                DocumentRevision.workspace_id == ws,
                DocumentRevision.documentmaster_id == doc_id,
                DocumentRevision.version == ver,
            ).first()
            if dr is None:
                raise NotAllowedException("NotAllowedException4")
            if dr.checkout_user_login != user_login:
                raise NotAllowedException("NotAllowedException4")
            if dr.last_iteration_number != iteration:
                raise NotAllowedException("NotAllowedException4")
        from app.services import vault as vault_svc
        from app.models.part import BinaryResource
        path = (vault_svc._vault_root() / ws / "documents" / doc_id
                / ver / str(iteration) / filename)
        vault_svc.write_file(path, data)
        full_name = f"{ws}/documents/{doc_id}/{ver}/{iteration}/{filename}"
        br = db.query(BinaryResource).filter(
            BinaryResource.full_name == full_name).first()
        now = datetime.utcnow()
        if br is not None:
            raise FileAlreadyExistsException("FileAlreadyExistsException", full_name)
        br = BinaryResource(full_name=full_name, content_length=len(data),
                            last_modified=now, dtype="BinaryResource")
        db.add(br)
        db.flush()
        exists = db.execute(document_iteration_binres.select().where(
            document_iteration_binres.c.workspace_id == ws,
            document_iteration_binres.c.documentmaster_id == doc_id,
            document_iteration_binres.c.documentrevision_version == ver,
            document_iteration_binres.c.iteration == iteration,
            document_iteration_binres.c.attachedfile_fullname == full_name,
        )).first()
        if exists is None:
            db.execute(document_iteration_binres.insert().values(
                workspace_id=ws, documentmaster_id=doc_id,
                documentrevision_version=ver, iteration=iteration,
                attachedfile_fullname=full_name))
        db.flush()  # caller 统一 commit，避免循环内逐文件提交
        return br

    def get_file_bytes(self, ws, doc_id, ver, iteration, filename):
        from app.services import vault as vault_svc
        full_name = f"{ws}/documents/{doc_id}/{ver}/{iteration}/{filename}"
        path = (vault_svc._vault_root() / ws / "documents" / doc_id
                / ver / str(iteration) / filename)
        try:
            return vault_svc.read_file(path)
        except FileNotFoundError:
            raise FileNotFoundException("FileNotFoundException", full_name)

    def _next_version(self, current):
        if not current: return "A"
        last_char = current[-1]
        if last_char == "Z": return current + "A"
        return current[:-1] + chr(ord(last_char) + 1)

    @staticmethod
    def _is_root_folder(completepath: str) -> bool:
        """对齐 Java Folder.isRoot(): completePath 不含 '/'。"""
        return "/" not in completepath

    @staticmethod
    def _is_home_folder(completepath: str) -> bool:
        """对齐 Java Folder.isHome(): 最后一个 '/' 后首字符是 '~'。"""
        try:
            idx = completepath.rindex("/")
            return completepath[idx + 1] == "~"
        except (ValueError, IndexError):
            return False

    @staticmethod
    def _is_another_user_home_folder(user_login: str, completepath: str) -> bool:
        """对齐 Java isAnotherUserHomeFolder: 是 private 文件夹且 owner != user。
        isPrivate: 第一个 '/' 后的字符是 '~'。
        getOwner: 在 firstSlash+2 到 nextSlash(或末尾) 间提取 owner login。"""
        if not user_login:
            return False
        try:
            idx = completepath.index("/")
            if completepath[idx + 1] != "~":
                return False
            owner_start = idx + 2
            owner_end = completepath.find("/", owner_start)
            if owner_end == -1:
                owner_end = len(completepath)
            owner = completepath[owner_start:owner_end]
            return owner != user_login
        except (ValueError, IndexError):
            return False

    # ========== DTO 构建 & 路由辅助方法 ==========

    @staticmethod
    def get_account_dto(db, login, ws):
        """查 Account 表取真实 name/email/language。"""
        if not login:
            return {"login": "", "name": "", "email": None, "language": None, "workspaceId": ws or ""}
        acc = db.query(Account).filter(Account.login == login).first()
        return {
            "login": login,
            "name": acc.name if acc and acc.name else login,
            "email": acc.email if acc else None,
            "language": acc.language if acc else None,
            "workspaceId": ws or "",
        }

    @staticmethod
    def build_route_path(db, workspace_id, complete_path):
        """根据 location_completepath 查询 pathdatamaster 表构建 routePath 列表。"""
        if not complete_path:
            return []
        components = complete_path.strip("/").split("/")
        if not components or components == [""]:
            return []
        result = []
        accumulated = ""
        for seg in components:
            accumulated += "/" + seg
            row = db.execute(sql_text(
                "SELECT id, path FROM pathdatamaster WHERE path=:p LIMIT 1"
            ), {"p": accumulated}).first()
            if row:
                result.append({"id": row[0], "path": row[1]})
            else:
                result.append({"path": accumulated})
        return result

    def _query_instance_attributes(self, db, ws, did, ver, it):
        """查询指定迭代的 instanceAttributes（含值字段）。"""
        attr_rows = db.execute(sql_text(
            "SELECT ia.name, ia.mandatory, ia.locked, "
            "ia.booleanvalue, ia.datevalue, ia.indexvalue, "
            "ia.numbervalue, ia.textvalue, ia.longtextvalue, ia.urlvalue "
            "FROM documentiteration_attribute dia "
            "JOIN instanceattribute ia ON ia.id = dia.instanceattribute_id "
            "WHERE dia.workspace_id=:ws AND dia.documentmaster_id=:did "
            "AND dia.documentrevision_version=:ver AND dia.iteration=:it "
            "ORDER BY dia.attribute_order"
        ), {"ws": ws, "did": did, "ver": ver, "it": it}).fetchall()
        return [dict(row._mapping) for row in attr_rows]

    def _query_linked_documents(self, db, ws, did, ver, it):
        """查询指定迭代的 linkedDocuments（扁平引用列表）。"""
        doc_rows = db.execute(sql_text(
            "SELECT dl.id, dl.target_workspace_id, dl.target_documentmaster_id, "
            "dl.target_docrevision_version, dl.commentdata "
            "FROM documentiteration_documentlink didl "
            "JOIN documentlink dl ON dl.id = didl.documentlink_id "
            "WHERE didl.workspace_id=:ws AND didl.documentmaster_id=:did "
            "AND didl.documentrevision_version=:ver AND didl.iteration=:it"
        ), {"ws": ws, "did": did, "ver": ver, "it": it}).fetchall()
        return [{
            "id": row.id,
            "workspaceId": row.target_workspace_id,
            "documentMasterId": row.target_documentmaster_id,
            "documentMasterVersion": row.target_docrevision_version,
            "commentLink": row.commentdata,
        } for row in doc_rows]

    def _query_attached_files(self, db, ws, did, ver, it):
        """查询指定迭代的 attachedFiles（含 BinaryResource 信息）。"""
        from app.models.part import BinaryResource
        attached_rows = db.execute(sql_text(
            "SELECT attachedfile_fullname FROM documentiteration_binres "
            "WHERE workspace_id=:ws AND documentmaster_id=:did "
            "AND documentrevision_version=:ver AND iteration=:iter"
        ), {"ws": ws, "did": did, "ver": ver, "iter": it}).fetchall()
        attached_files = []
        for ar in attached_rows:
            br = db.query(BinaryResource).filter(
                BinaryResource.full_name == ar[0]).first()
            if br:
                attached_files.append({
                    "fullName": br.full_name,
                    "contentLength": br.content_length or 0,
                    "lastModified": str(br.last_modified) if br.last_modified else None,
                })
            else:
                attached_files.append({"fullName": ar[0]})
        return attached_files

    def _build_iteration_dict(self, db, rev, it, acl_data):
        """构建单个 iteration 的 dict。"""
        ws = it.workspace_id
        did = it.documentmaster_id
        ver = it.documentrevision_version
        its = it.iteration
        return {
            "id": f"{did}-{ver}-{its}",
            "iteration": its,
            "workspaceId": ws,
            "documentMasterId": did,
            "documentRevisionVersion": ver,
            "version": rev.version,
            "title": rev.title,
            "revisionNote": it.revision_note,
            "creationDate": str(it.creation_date) if it.creation_date else None,
            "modificationDate": str(it.modification_date) if it.modification_date else None,
            "checkInDate": str(it.check_in_date) if it.check_in_date else None,
            "instanceAttributes": self._query_instance_attributes(db, ws, did, ver, its),
            "attachedFiles": self._query_attached_files(db, ws, did, ver, its),
            "linkedDocuments": self._query_linked_documents(db, ws, did, ver, its),
            "author": self.get_account_dto(db, it.author_login, ws),
            "documentRevision": {
                "id": f"{rev.documentmaster_id}-{rev.version}-{rev.version}",
                "workspaceId": rev.workspace_id,
                "version": rev.version,
                "documentMasterId": f"{rev.documentmaster_id}-{rev.version}",
                "status": None,
                "publicShared": False,
                "acl": acl_data or {},
                "attributesLocked": False,
                "checkOutUser": None,
                "checkOutDate": None,
                "releaseAuthor": None,
                "releaseDate": None,
                "iterationSubscription": False,
                "stateSubscription": False,
                "commentLink": None,
            },
        }

    def build_revision_dto(self, db, rev, current_user_login=None):
        """构建完整的 DocumentRevision DTO dict（对标原 router 层的 _doc_to_dict）。"""
        _PERM_MAP = {0: "FORBIDDEN", 1: "READ_ONLY", 2: "FULL_ACCESS"}
        acl_id = getattr(rev, "acl_id", None)
        acl_data = None
        if acl_id and db:
            acl = db.query(ACL).filter(ACL.id == acl_id).first()
            if acl:
                user_entries = db.query(AclUserEntry).filter(AclUserEntry.acl_id == acl_id).all()
                group_entries = db.query(AclUserGroupEntry).filter(AclUserGroupEntry.acl_id == acl_id).all()
                acl_data = {
                    "userEntries": [{"key": e.principal_login, "value": _PERM_MAP.get(e.permission, "FORBIDDEN")} for e in user_entries],
                    "groupEntries": [{"key": e.principal_id, "value": _PERM_MAP.get(e.permission, "FORBIDDEN")} for e in group_entries],
                    "userEntriesMap": {e.principal_login: _PERM_MAP.get(e.permission, "FORBIDDEN") for e in user_entries},
                    "userGroupEntriesMap": {e.principal_id: _PERM_MAP.get(e.permission, "FORBIDDEN") for e in group_entries},
                }

        iterations = []
        for it in (rev.iterations or []):
            iterations.append(self._build_iteration_dict(db, rev, it, acl_data))

        iter_sub = None
        state_sub = None
        if db and current_user_login:
            iter_sub = db.execute(sql_text(
                "SELECT 1 FROM iterationchangesubscription WHERE documentmaster_id=:did "
                "AND documentmaster_workspace_id=:ws AND documentrevision_version=:ver "
                "AND subscriber_login=:login AND subscriber_workspace_id=:sws LIMIT 1"
            ), {"did": rev.documentmaster_id, "ws": rev.workspace_id, "ver": rev.version,
                "login": current_user_login, "sws": rev.workspace_id}).scalar()
            state_sub = db.execute(sql_text(
                "SELECT 1 FROM statechangesubscription WHERE documentmaster_id=:did "
                "AND documentmaster_workspace_id=:ws AND documentrevision_version=:ver "
                "AND subscriber_login=:login AND subscriber_workspace_id=:sws LIMIT 1"
            ), {"did": rev.documentmaster_id, "ws": rev.workspace_id, "ver": rev.version,
                "login": current_user_login, "sws": rev.workspace_id}).scalar()

        dict_fields = {
            "id": f"{rev.documentmaster_id}-{rev.version}",
            "version": rev.version,
            "workspaceId": rev.workspace_id,
            "documentMasterId": rev.documentmaster_id,
            "title": rev.title,
            "description": rev.description,
            "status": {0: "WIP", 1: "RELEASED", 2: "OBSOLETE"}.get(rev.status, "WIP"),
            "creationDate": str(rev.creation_date) if rev.creation_date else None,
            "checkOutDate": str(rev.check_out_date) if rev.check_out_date else None,
            "releaseDate": str(rev.release_date) if rev.release_date else None,
            "obsoleteDate": str(rev.obsolete_date) if rev.obsolete_date else None,
            "lastIteration": rev.last_iteration_number,
            "lastIterationNumber": rev.last_iteration_number,
            "documentIterations": iterations,
            "tags": [],
            "path": rev.location_completepath,
            "routePath": rev.location_completepath,
            "acl": acl_data or {},
            "publicShared": bool(getattr(rev, "public_shared", False)),
            "attributesLocked": False,
            "commentLink": None,
            "iterationSubscription": iter_sub is not None,
            "stateSubscription": state_sub is not None,
            "releaseAuthor": None,
            "obsoleteAuthor": None,
            "type": rev.document_master.type if rev.document_master else None,
            "author": self.get_account_dto(db, rev.author_login, rev.workspace_id),
        }
        if rev.checkout_user_login:
            dict_fields["checkOutUser"] = self.get_account_dto(
                db, rev.checkout_user_login,
                rev.checkout_user_workspace_id or rev.workspace_id,
            )
        if rev.release_user_login:
            dict_fields["releaseAuthor"] = self.get_account_dto(
                db, rev.release_user_login, rev.workspace_id,
            )
        if rev.obsolete_user_login:
            dict_fields["obsoleteAuthor"] = self.get_account_dto(
                db, rev.obsolete_user_login, rev.workspace_id,
            )
        for k in ("description",):
            dict_fields.setdefault(k, "")

        wf_id = getattr(rev, "workflow_id", None)
        dict_fields["workflowId"] = wf_id
        if wf_id and db:
            wf_row = db.execute(sql_text(
                "SELECT id, finallifecyclestate, aborteddate FROM workflow WHERE id=:wid"
            ), {"wid": wf_id}).first()
            if wf_row:
                act = db.execute(sql_text(
                    "SELECT lifecyclestate FROM activity "
                    "WHERE workflow_id=:wid AND dtype!='org.docdoku.plm.server.core.workflow.ParallelActivity' "
                    "ORDER BY step ASC"
                ), {"wid": wf_id}).first()
                lcs = act[0] if act else wf_row[1]
                dict_fields["lifeCycleState"] = lcs
                wf_dict = {
                    "id": wf_id,
                    "finalLifeCycleState": wf_row[1],
                    "abortedDate": str(wf_row[2]) if wf_row[2] else None,
                    "activities": [],
                    "currentStep": 0,
                }
                act_rows = db.execute(sql_text(
                    "SELECT step, dtype, lifecyclestate, taskstocomplete FROM activity "
                    "WHERE workflow_id=:wid ORDER BY step ASC"
                ), {"wid": wf_id}).fetchall()
                current_step = 0
                for a in act_rows:
                    tasks = db.execute(sql_text(
                        "SELECT num, title, instructions, status, worker_login, "
                        "worker_workspace_id, duration, signature, closuredate, "
                        "closurecomment, startdate, targetiteration "
                        "FROM task WHERE workflow_id=:wid AND activity_step=:step "
                        "ORDER BY num ASC"
                    ), {"wid": wf_id, "step": a[0]}).fetchall()
                    task_list = []
                    all_completed = True
                    for t in tasks:
                        worker = None
                        if t[4]:
                            worker = self.get_account_dto(db, t[4], t[5] or rev.workspace_id)
                        task_list.append({
                            "num": t[0], "title": t[1], "instructions": t[2],
                            "status": t[3], "worker": worker, "duration": t[6],
                            "signature": t[7],
                            "closureDate": str(t[8]) if t[8] else None,
                            "closureComment": t[9],
                            "startDate": str(t[10]) if t[10] else None,
                            "targetIteration": t[11],
                        })
                        if t[3] not in ("APPROVED", "CLOSED"):
                            all_completed = False
                    wf_dict["activities"].append({
                        "step": a[0], "type": a[1], "lifeCycleState": a[2],
                        "tasksToComplete": a[3], "tasks": task_list,
                    })
                    if all_completed and current_step < len(act_rows):
                        current_step += 1
                wf_dict["currentStep"] = current_step
                dict_fields["workflow"] = wf_dict
        dict_fields.setdefault("lifeCycleState", None)
        dict_fields.setdefault("workflow", None)

        if db:
            tag_rows = db.execute(sql_text(
                "SELECT tag_label FROM documentrevision_tag "
                "WHERE documentmaster_workspace_id=:ws AND documentmaster_id=:did "
                "AND documentrevision_version=:ver"
            ), {"ws": rev.workspace_id, "did": rev.documentmaster_id, "ver": rev.version}).fetchall()
            dict_fields["tags"] = [tr[0] for tr in tag_rows]
        return dict_fields

    def get_aborted_workflows(self, db, ws, doc_id, ver):
        """查询已终止的工作流列表。"""
        rev = self.get_revision(db, ws, doc_id, ver)
        workflow_id = getattr(rev, "workflow_id", None)
        if not workflow_id:
            return []
        rows = db.execute(sql_text(
            "SELECT id, aborteddate, finallifecyclestate FROM workflow "
            "WHERE id=:wid AND aborteddate IS NOT NULL"
        ), {"wid": workflow_id}).fetchall()
        result = []
        for r in rows:
            activities = db.execute(sql_text(
                "SELECT step, dtype, lifecyclestate, taskstocomplete FROM activity "
                "WHERE workflow_id=:wid ORDER BY step ASC"
            ), {"wid": r[0]}).fetchall()
            activity_list = []
            for a in activities:
                tasks = db.execute(sql_text(
                    "SELECT num, title, instructions, status, worker_login, "
                    "worker_workspace_id, duration, signature, closuredate, "
                    "closurecomment, startdate, targetiteration "
                    "FROM task WHERE workflow_id=:wid AND activity_step=:step "
                    "ORDER BY num ASC"
                ), {"wid": r[0], "step": a[0]}).fetchall()
                task_list = []
                for t in tasks:
                    worker = None
                    if t[4]:
                        worker = self.get_account_dto(db, t[4], t[5] or ws)
                    task_list.append({
                        "num": t[0], "title": t[1], "instructions": t[2],
                        "status": t[3], "worker": worker, "duration": t[6],
                        "signature": t[7],
                        "closureDate": str(t[8]) if t[8] else None,
                        "closureComment": t[9],
                        "startDate": str(t[10]) if t[10] else None,
                        "targetIteration": t[11],
                    })
                activity_list.append({
                    "step": a[0], "type": a[1], "lifeCycleState": a[2],
                    "tasksToComplete": a[3], "tasks": task_list,
                })
            result.append({
                "id": r[0],
                "abortedDate": str(r[1]) if r[1] else None,
                "finalLifeCycleState": r[2],
                "activities": activity_list,
            })
        return result

    def get_inverse_document_links(self, db, ws, doc_id, ver, current_user_login=None):
        """查询反向文档链接（哪些文档引用了当前文档）。"""
        rows = db.execute(sql_text(
            "SELECT di.workspace_id, di.documentmaster_id, di.documentrevision_version, "
            "di.iteration, dl.id AS link_id, dl.target_documentmaster_id, "
            "dl.target_docrevision_version, dl.target_workspace_id, dl.commentdata "
            "FROM documentiteration_documentlink didl "
            "JOIN documentlink dl ON didl.documentlink_id = dl.id "
            "JOIN documentiteration di ON "
            "di.workspace_id=didl.workspace_id AND di.documentmaster_id=didl.documentmaster_id "
            "AND di.documentrevision_version=didl.documentrevision_version "
            "AND di.iteration=didl.iteration "
            "WHERE dl.target_workspace_id=:ws AND dl.target_documentmaster_id=:did "
            "AND dl.target_docrevision_version=:ver"
        ), {"ws": ws, "did": doc_id, "ver": ver}).fetchall()
        seen = set()
        result = []
        for r in rows:
            key = (r[0], r[1], r[2])
            if key in seen:
                continue
            seen.add(key)
            rev = self.get_revision(db, r[0], r[1], r[2])
            result.append(self.build_revision_dto(db, rev, current_user_login))
        return result

    def get_inverse_part_links(self, db, ws, doc_id, ver):
        """查询反向零件链接（哪些零件引用了当前文档）。"""
        rows = db.execute(sql_text(
            "SELECT pi.workspace_id, pi.partmaster_partnumber, pi.partrevision_version, "
            "pi.iteration, dl.id AS link_id, dl.target_documentmaster_id, "
            "dl.target_docrevision_version, dl.target_workspace_id "
            "FROM partiteration_documentlink pidl "
            "JOIN documentlink dl ON pidl.documentlink_id = dl.id "
            "JOIN partiteration pi ON "
            "pi.workspace_id=pidl.workspace_id AND pi.partmaster_partnumber=pidl.partmaster_partnumber "
            "AND pi.partrevision_version=pidl.partrevision_version AND pi.iteration=pidl.iteration "
            "WHERE dl.target_workspace_id=:ws AND dl.target_documentmaster_id=:did "
            "AND dl.target_docrevision_version=:ver"
        ), {"ws": ws, "did": doc_id, "ver": ver}).fetchall()
        from app.services.product_manager import ProductService
        from app.services.part_mapper import map_revision
        psvc = ProductService()
        seen = set()
        result = []
        for r in rows:
            key = (r[0], r[1], r[2])
            if key in seen:
                continue
            seen.add(key)
            pr = psvc.get_revision(db, r[0], r[1], r[2])
            result.append(map_revision(pr, db).model_dump())
        return result

    def get_inverse_product_links(self, db, ws, doc_id, ver):
        """查询反向产品实例链接（哪些产品实例引用了当前文档）。"""
        rows = db.execute(sql_text(
            "SELECT DISTINCT pidl.workspace_id, pidl.prdinstancemaster_serialnumber, "
            "pidl.configurationitem_id, pidl.iteration, "
            "pii.iterationnote, pii.creationdate, pii.author_login, pii.author_workspace_id "
            "FROM prdinstiteration_documentlink pidl "
            "JOIN documentlink dl ON pidl.documentlink_id = dl.id "
            "LEFT JOIN productinstanceiteration pii ON "
            "pii.workspace_id=pidl.workspace_id AND pii.configurationitem_id=pidl.configurationitem_id "
            "AND pii.prdinstancemaster_serialnumber=pidl.prdinstancemaster_serialnumber "
            "AND pii.iteration=pidl.iteration "
            "WHERE dl.target_workspace_id=:ws AND dl.target_documentmaster_id=:did "
            "AND dl.target_docrevision_version=:ver"
        ), {"ws": ws, "did": doc_id, "ver": ver}).fetchall()
        result = []
        for r in rows:
            result.append({
                "workspaceId": r[0],
                "serialNumber": r[1],
                "configurationItemId": r[2],
                "instanceIteration": r[3],
                "iterationNote": r[4] or "",
                "creationDate": str(r[5]) if r[5] else None,
                "author": self.get_account_dto(db, r[6], r[7] or ws) if r[6] else None,
            })
        return result

    def get_inverse_path_links(self, db, ws, doc_id, ver):
        """查询反向路径数据链接（哪些路径数据引用了当前文档）。"""
        rows = db.execute(sql_text(
            "SELECT DISTINCT pdm.id AS path_data_id, pdm.path "
            "FROM pathdataiteration_documentlink pdl "
            "JOIN documentlink dl ON pdl.documentlink_id = dl.id "
            "JOIN pathdatamaster pdm ON pdm.id = pdl.pathdatamaster_id "
            "WHERE dl.target_workspace_id=:ws AND dl.target_documentmaster_id=:did "
            "AND dl.target_docrevision_version=:ver"
        ), {"ws": ws, "did": doc_id, "ver": ver}).fetchall()
        from app.services.product_structure import ProductStructureService
        psvc = ProductStructureService()
        result = []
        for r in rows:
            pdm_id, path_str = r[0], r[1]
            dto = {"id": pdm_id, "path": path_str}
            pipd_row = db.execute(sql_text(
                "SELECT configurationitem_id, prdinstancemaster_serialnumber "
                "FROM prdinstiteration_pathdatamstr "
                "WHERE pathdatamaster_id=:pid LIMIT 1"
            ), {"pid": pdm_id}).first()
            if pipd_row:
                ci_id = pipd_row[0]
                dto["serialNumber"] = pipd_row[1]
                try:
                    part_links = psvc.decode_path(db, ws, ci_id, path_str)
                    dto["partLinksList"] = {"partLinks": part_links}
                except Exception:
                    dto["partLinksList"] = {"partLinks": []}
            else:
                dto["serialNumber"] = None
                dto["partLinksList"] = {"partLinks": []}
            result.append(dto)
        return result

    def build_iteration_dto_after_update(self, db, rev, doc_iter, user_login):
        """update_iteration 后的 DTO 组装（返回单个 iteration 的 dict）。"""
        target_it = next((it for it in rev.iterations if it.iteration == doc_iter), None)
        if target_it is None:
            raise EntityNotFoundException("DocumentIterationNotFoundException",
                                          rev.documentmaster_id, rev.version, str(doc_iter))
        ws = rev.workspace_id
        doc_id = rev.documentmaster_id
        ver = rev.version

        attached_files = self._query_attached_files(db, ws, doc_id, ver, doc_iter)

        linked_rows = db.execute(sql_text(
            "SELECT dl.id, dl.target_workspace_id, dl.target_documentmaster_id, "
            "dl.target_docrevision_version, dl.commentdata "
            "FROM documentiteration_documentlink didl "
            "JOIN documentlink dl ON didl.documentlink_id = dl.id "
            "WHERE didl.workspace_id=:ws AND didl.documentmaster_id=:did "
            "AND didl.documentrevision_version=:ver AND didl.iteration=:iter"
        ), {"ws": ws, "did": doc_id, "ver": ver, "iter": doc_iter}).fetchall()
        linked_documents = []
        for lr in linked_rows:
            try:
                linked_rev = self.get_revision(db, lr[1], lr[2], lr[3])
                ld = self.build_revision_dto(db, linked_rev, user_login)
                ld["commentLink"] = lr[4] or ""
                linked_documents.append(ld)
            except Exception:
                linked_documents.append({
                    "workspaceId": lr[1], "documentMasterId": lr[2],
                    "version": lr[3], "commentLink": lr[4] or "",
                })

        instance_attrs = self._query_instance_attributes(db, ws, doc_id, ver, doc_iter)

        return {
            "id": f"{rev.documentmaster_id}-{rev.version}-{doc_iter}",
            "iteration": doc_iter,
            "workspaceId": rev.workspace_id,
            "documentMasterId": rev.documentmaster_id,
            "documentRevisionVersion": rev.version,
            "version": rev.version,
            "title": rev.title,
            "revisionNote": target_it.revision_note,
            "creationDate": str(target_it.creation_date) if target_it.creation_date else None,
            "modificationDate": str(target_it.modification_date) if target_it.modification_date else None,
            "checkInDate": str(target_it.check_in_date) if target_it.check_in_date else None,
            "instanceAttributes": instance_attrs,
            "attachedFiles": attached_files,
            "linkedDocuments": linked_documents,
            "author": self.get_account_dto(db, target_it.author_login, target_it.workspace_id),
            "documentRevision": {
                "id": f"{rev.documentmaster_id}-{rev.version}-{rev.version}",
                "workspaceId": rev.workspace_id,
                "version": rev.version,
                "documentMasterId": f"{rev.documentmaster_id}-{rev.version}",
                "status": None, "publicShared": False, "acl": {},
                "attributesLocked": False, "checkOutUser": None,
                "checkOutDate": None, "releaseAuthor": None,
                "releaseDate": None, "iterationSubscription": False,
                "stateSubscription": False, "commentLink": None,
            },
        }

    def update_acl(self, db, ws, doc_id, ver, user_login, body):
        """更新文档 ACL（对齐 Java updateDocumentRevisionACL）。"""
        from app.services.factory.acl_factory import apply_acl
        dr = self.get_revision(db, ws, doc_id, ver)
        is_admin = db.execute(sql_text(
            "SELECT 1 FROM usergroupmapping WHERE login=:l AND groupname='admin'"
        ), {"l": user_login}).first() is not None
        is_author = dr.author_login == user_login
        if not is_admin and not is_author:
            raise AccessRightException("AccessRightException", user_login)
        user_entries = body.get("userEntries", {})
        group_entries = body.get("groupEntries", {})
        has_entries = bool(user_entries or group_entries)
        if has_entries:
            acl_id = getattr(dr, "acl_id", None)
            new_acl_id = apply_acl(db, acl_id, user_entries, group_entries)
            if dr.acl_id != new_acl_id:
                dr.acl_id = new_acl_id
                db.commit()
        else:
            acl_id = getattr(dr, "acl_id", None)
            if acl_id:
                db.execute(sql_text("DELETE FROM acluserentry WHERE acl_id=:aid"), {"aid": acl_id})
                db.execute(sql_text("DELETE FROM aclusergroupentry WHERE acl_id=:aid"), {"aid": acl_id})
                dr.acl_id = None
                db.commit()

    def _check_doc_file_writable(self, db, ws, doc_id, ver, iteration, user_login):
        """检查用户是否对文档迭代文件有写权限（已签出且是最新迭代）。"""
        dr = db.query(DocumentRevision).filter(
            DocumentRevision.workspace_id == ws,
            DocumentRevision.documentmaster_id == doc_id,
            DocumentRevision.version == ver,
        ).first()
        if dr is None:
            raise NotAllowedException("NotAllowedException4")
        if dr.checkout_user_login != user_login:
            raise NotAllowedException("NotAllowedException4")
        if dr.last_iteration_number != iteration:
            raise NotAllowedException("NotAllowedException4")

    def delete_document_file(self, db, ws, doc_id, ver, iteration, filename, user_login):
        """删除文档迭代中的文件（含 vault 文件系统操作）。"""
        from app.models.part import BinaryResource
        from app.core.config import settings
        from pathlib import Path

        self._check_doc_file_writable(db, ws, doc_id, ver, iteration, user_login)
        full_name = f"{ws}/documents/{doc_id}/{ver}/{iteration}/{filename}"

        db.execute(document_iteration_binres.delete().where(
            document_iteration_binres.c.workspace_id == ws,
            document_iteration_binres.c.documentmaster_id == doc_id,
            document_iteration_binres.c.documentrevision_version == ver,
            document_iteration_binres.c.iteration == iteration,
            document_iteration_binres.c.attachedfile_fullname == full_name,
        ))
        br = db.query(BinaryResource).filter(BinaryResource.full_name == full_name).first()
        if br:
            db.delete(br)
        try:
            vault_path = Path(settings.VAULT_PATH) / full_name
            if vault_path.exists():
                vault_path.unlink()
        except Exception:
            pass
        db.commit()

    def rename_document_file(self, db, ws, doc_id, ver, iteration, old_name, new_name, user_login):
        """重命名文档迭代中的文件（含 vault rename）。"""
        from app.models.part import BinaryResource
        from app.core.config import settings
        from pathlib import Path

        self._check_doc_file_writable(db, ws, doc_id, ver, iteration, user_login)
        old_full = f"{ws}/documents/{doc_id}/{ver}/{iteration}/{old_name}"
        new_full = f"{ws}/documents/{doc_id}/{ver}/{iteration}/{new_name}"

        br = db.query(BinaryResource).filter(BinaryResource.full_name == old_full).first()
        if br:
            br.full_name = new_full
        db.execute(document_iteration_binres.update().where(
            document_iteration_binres.c.workspace_id == ws,
            document_iteration_binres.c.documentmaster_id == doc_id,
            document_iteration_binres.c.documentrevision_version == ver,
            document_iteration_binres.c.iteration == iteration,
            document_iteration_binres.c.attachedfile_fullname == old_full,
        ).values(attachedfile_fullname=new_full))
        try:
            old_path = Path(settings.VAULT_PATH) / old_full
            new_path = Path(settings.VAULT_PATH) / new_full
            if old_path.exists():
                new_path.parent.mkdir(parents=True, exist_ok=True)
                old_path.rename(new_path)
        except Exception:
            pass
        db.commit()
        return {"fullName": new_full, "name": new_name}

    # ── tag CRUD ────────────────────────────────────────────────

    def get_all_tags(self, db, ws):
        from app.models.part import Tag
        tags = db.query(Tag).filter(Tag.workspace_id == ws).all()
        return [{"id": t.label, "label": t.label, "workspaceId": ws} for t in tags]

    def create_tag(self, db, ws, label):
        from app.models.part import Tag
        existing = db.query(Tag).filter(
            Tag.workspace_id == ws, Tag.label == label
        ).first()
        if existing is None:
            db.add(Tag(workspace_id=ws, label=label))
            db.commit()
        return {"id": label, "label": label, "workspaceId": ws}

    def create_tags_batch(self, db, ws, labels):
        from app.models.part import Tag
        for label in labels:
            if not label:
                continue
            existing = db.query(Tag).filter(
                Tag.workspace_id == ws, Tag.label == label
            ).first()
            if existing is None:
                db.add(Tag(workspace_id=ws, label=label))
        db.commit()

    def delete_tag(self, db, ws, label):
        db.execute(sql_text("DELETE FROM documentrevision_tag WHERE tag_label=:label AND tag_workspace_id=:ws"),
                   {"label": label, "ws": ws})
        db.execute(sql_text("DELETE FROM partrevision_tag WHERE tag_label=:label AND tag_workspace_id=:ws"),
                   {"label": label, "ws": ws})
        db.execute(sql_text("DELETE FROM changeissue_tag WHERE tag_label=:label AND tag_workspace_id=:ws"),
                   {"label": label, "ws": ws})
        db.execute(sql_text("DELETE FROM changeorder_tag WHERE tag_label=:label AND tag_workspace_id=:ws"),
                   {"label": label, "ws": ws})
        db.execute(sql_text("DELETE FROM changerequest_tag WHERE tag_label=:label AND tag_workspace_id=:ws"),
                   {"label": label, "ws": ws})
        db.execute(sql_text("DELETE FROM tagusersubscription WHERE tag_label=:label AND tag_workspace_id=:ws"),
                   {"label": label, "ws": ws})
        db.execute(sql_text("DELETE FROM tagusergroupsubscription WHERE tag_label=:label AND tag_workspace_id=:ws"),
                   {"label": label, "ws": ws})
        result = db.execute(
            sql_text("DELETE FROM tag WHERE label=:label AND workspace_id=:ws"),
            {"label": label, "ws": ws},
        )
        if result.rowcount:
            db.commit()

    def get_documents_by_tag(self, db, ws, tag_label, current_user_login=None):
        from app.models.document import DocumentRevision, document_revision_tags
        revisions = db.query(DocumentRevision).join(
            document_revision_tags,
            (DocumentRevision.workspace_id == document_revision_tags.c.documentmaster_workspace_id)
            & (DocumentRevision.documentmaster_id == document_revision_tags.c.documentmaster_id)
            & (DocumentRevision.version == document_revision_tags.c.documentrevision_version)
        ).filter(
            DocumentRevision.workspace_id == ws,
            document_revision_tags.c.tag_label == tag_label,
        ).all()
        return [self.build_revision_dto(db, dr, current_user_login) for dr in revisions]

    # ── move folder ─────────────────────────────────────────────

    def get_folder(self, db, completepath):
        return db.query(Folder).filter(Folder.completepath == completepath).first()

    def move_folder(self, db, ws, folder_id, new_parent, user_login):
        from app.core.exceptions import NotAllowedException, EntityAlreadyExistsException, FolderNotFoundException
        from fastapi import HTTPException

        folder = db.query(Folder).filter(Folder.completepath == folder_id).first()
        if not folder:
            raise FolderNotFoundException("FolderNotFoundException", folder_id)
        if self._is_root_folder(folder_id):
            raise NotAllowedException("NotAllowedException21")
        if self._is_home_folder(folder_id):
            raise NotAllowedException("NotAllowedException21")
        if self._is_another_user_home_folder(user_login, folder_id):
            raise NotAllowedException("NotAllowedException21")

        def _parse_workspace_id(path: str) -> str:
            idx = path.find("/")
            return path[:idx] if idx != -1 else path

        if _parse_workspace_id(new_parent) != ws:
            raise NotAllowedException("NotAllowedException23")

        old_prefix = folder.completepath
        old_name = old_prefix.split('/')[-1]
        new_path = f"{new_parent}/{old_name}" if new_parent else old_name
        existing = db.query(Folder).filter(Folder.completepath == new_path).first()
        if existing:
            raise EntityAlreadyExistsException("FolderAlreadyExistsException", new_path)

        rows = db.query(Folder).filter(Folder.completepath.like(f"{old_prefix}%")).all()
        for f in rows:
            f.completepath = f.completepath.replace(old_prefix, new_path, 1)
            if f.parentfolder_completepath:
                f.parentfolder_completepath = f.parentfolder_completepath.replace(old_prefix, new_path, 1)

        docs = db.query(DocumentRevision).filter(
            DocumentRevision.location_completepath.like(f"{old_prefix}%")
        ).all()
        for doc in docs:
            doc.location_completepath = doc.location_completepath.replace(old_prefix, new_path, 1)

        db.commit()

    # ── document template DTO ───────────────────────────────────

    def _build_template_acl_dict(self, db, acl_id):
        if not acl_id:
            return {}
        acl_obj = db.query(ACL).filter(ACL.id == acl_id).first()
        user_entries = []
        group_entries = []
        if acl_obj:
            user_entries = db.query(AclUserEntry).filter(AclUserEntry.acl_id == acl_id).all()
            group_entries = db.query(AclUserGroupEntry).filter(AclUserGroupEntry.acl_id == acl_id).all()
        perm_map = {0: "FORBIDDEN", 1: "READ_ONLY", 2: "FULL_ACCESS"}
        return {
            "userEntries": [{"key": e.principal_login, "value": perm_map.get(e.permission, "FORBIDDEN")} for e in user_entries],
            "groupEntries": [{"key": e.principal_id, "value": perm_map.get(e.permission, "FORBIDDEN")} for e in group_entries],
            "userEntriesMap": {e.principal_login: perm_map.get(e.permission, "FORBIDDEN") for e in user_entries},
            "userGroupEntriesMap": {e.principal_id: perm_map.get(e.permission, "FORBIDDEN") for e in group_entries},
        }

    def build_template_dto(self, db, t):
        author = None
        if t.author_login:
            acc = db.query(Account).filter(Account.login == t.author_login).first()
            author = {
                "login": t.author_login,
                "name": acc.name if acc else t.author_login,
                "email": acc.email if acc else None,
                "language": acc.language if acc else None,
                "workspaceId": t.workspace_id,
            }
        acl = self._build_template_acl_dict(db, t.acl_id)
        return {
            "id": t.id, "workspaceId": t.workspace_id,
            "documentType": t.document_type, "mask": t.mask,
            "idGenerated": t.id_generated,
            "attributesLocked": t.attributes_locked,
            "author": author or {},
            "acl": acl or {},
            "creationDate": str(t.creation_date) if t.creation_date else None,
            "attachedFiles": [],
            "attributeTemplates": [],
        }

    def list_templates_dto(self, db, ws):
        templates = self.list_templates(db, ws)
        return [self.build_template_dto(db, t) for t in templates]

    def get_template_dto(self, db, ws, template_id):
        t = self.get_template(db, ws, template_id)
        return self.build_template_dto(db, t)

    def update_template_with_attrs(self, db, ws, template_id, body):
        from datetime import datetime
        t = self.get_template(db, ws, template_id)
        for field in ("documentType", "mask", "idGenerated"):
            if field in body:
                col = "document_type" if field == "documentType" else (
                    "mask" if field == "mask" else "id_generated")
                setattr(t, col, body[field])
        if "workflowModelId" in body:
            t.workflowmodel_id = body["workflowModelId"]
        if "attributeTemplates" in body:
            db.execute(sql_text(
                "DELETE FROM documentmastertemplate_attr "
                "WHERE workspace_id=:ws AND documentmastertemplate_id=:tid"
            ), {"ws": ws, "tid": template_id})
            for order, attr in enumerate(body["attributeTemplates"]):
                attr_name = attr.get("name", "")
                attr_dtype = attr.get("dtype", "InstanceTextAttribute")
                attr_mandatory = attr.get("mandatory", False)
                attr_locked = attr.get("locked", False)
                attr_type = attr.get("attributeType", 0)
                lov_name = attr.get("lovName")
                lov_ws = attr.get("lovWorkspaceId")
                result = db.execute(sql_text(
                    "INSERT INTO instanceattributetemplate "
                    "(dtype, name, mandatory, locked, attributetype, lov_name, lov_workspace_id) "
                    "VALUES (:dtype, :name, :mand, :locked, :atype, :lovn, :lovw) RETURNING id"
                ), {"dtype": attr_dtype, "name": attr_name, "mand": attr_mandatory,
                    "locked": attr_locked, "atype": attr_type,
                    "lovn": lov_name, "lovw": lov_ws})
                attr_id = result.fetchone()[0]
                db.execute(sql_text(
                    "INSERT INTO documentmastertemplate_attr "
                    "(workspace_id, documentmastertemplate_id, instanceattributetemplate_id, attr_order) "
                    "VALUES (:ws, :tid, :aid, :ord)"
                ), {"ws": ws, "tid": template_id, "aid": attr_id, "ord": order})
        if "lovs" in body or "LOVs" in body:
            pass
        t.modification_date = datetime.utcnow()
        db.commit()
        return {"id": t.id, "status": "updated"}

    def update_doc_template_acl(self, db, ws, template_id, body):
        from app.services.factory.acl_factory import apply_acl
        tpl = db.query(DocumentMasterTemplate).filter(
            DocumentMasterTemplate.workspace_id == ws,
            DocumentMasterTemplate.id == template_id,
        ).first()
        if not tpl:
            from app.core.exceptions import EntityNotFoundException
            raise EntityNotFoundException("DocumentMasterTemplateNotFoundException", template_id)
        acl_id = getattr(tpl, "acl_id", None)
        new_acl_id = apply_acl(db, acl_id, body.get("userEntries", {}), body.get("groupEntries", {}))
        if tpl.acl_id != new_acl_id:
            tpl.acl_id = new_acl_id
            db.commit()
        return new_acl_id

    def create_document_in_root_with_tag(self, db, ws, body, tag_label, user_login):
        doc_id = body.get("reference", body.get("id", ""))
        title = body.get("title", "")
        template_id = body.get("templateId")
        workflow_model_id = body.get("workflowModelId")

        dr = self.create_document(
            db, ws, doc_id, title, user_login,
            folder_path=ws,
            template_id=template_id,
            workflow_model_id=workflow_model_id,
        )
        self._ensure_tag(db, ws, tag_label)
        self.add_tag(db, ws, dr.documentmaster_id, dr.version, tag_label, user_login)

        return self.build_revision_dto(db, dr, user_login)

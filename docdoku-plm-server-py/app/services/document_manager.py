from datetime import datetime
from fastapi import HTTPException
from sqlalchemy import text as sql_text
from app.models.document import (
    DocumentMaster, DocumentRevision, DocumentIteration,
    DocumentMasterTemplate, Folder, document_iteration_binres,
    document_revision_tags,
)
from app.core.exceptions import (
    EntityAlreadyExistsException, EntityConstraintException,
    NotAllowedException, EntityNotFoundException,
)


class DocumentService:

    def get_revision(self, db, ws, doc_id, ver):
        pr = db.query(DocumentRevision).filter(
            DocumentRevision.workspace_id == ws,
            DocumentRevision.documentmaster_id == doc_id,
            DocumentRevision.version == ver,
        ).first()
        if pr is None:
            raise HTTPException(404, f"Document {doc_id}-{ver} not found")
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
                        folder_path=None):
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
        db.add(master); db.flush()
        rev = DocumentRevision(
            workspace_id=ws, documentmaster_id=doc_id, version="A",
            title=title, status=0, creation_date=now,
            location_completepath=location,
            author_workspace_id=ws, author_login=user_login,
            checkout_user_workspace_id=ws, checkout_user_login=user_login,
            check_out_date=now)
        db.add(rev); db.flush()
        it = DocumentIteration(
            workspace_id=ws, documentmaster_id=doc_id,
            documentrevision_version="A", iteration=1,
            creation_date=now, author_workspace_id=ws,
            author_login=user_login)
        db.add(it)
        db.commit(); db.refresh(rev)
        return rev

    def delete_revision(self, db, ws, doc_id, ver, user_login):
        pr = self.get_revision(db, ws, doc_id, ver)

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
        pr = self.get_revision(db, ws, doc_id, ver)
        if pr.checkout_user_login:
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
        pr.checkout_user_login = user_login
        pr.checkout_user_workspace_id = ws
        pr.check_out_date = now
        # 复制上一迭代的 attached_files 到新迭代
        if previous_iteration:
            self._copy_attached_files(db, ws, doc_id, ver,
                                      previous_iteration.iteration,
                                      new_it.iteration)
        db.commit(); db.refresh(pr)
        return pr

    def _copy_attached_files(self, db, ws, doc_id, ver, src_iter, dst_iter):
        """将 src_iter 的 attached_files 复制到 dst_iter。"""
        from sqlalchemy import text
        rows = db.execute(text(
            "SELECT attachedfile_fullname FROM documentiteration_binres "
            "WHERE workspace_id=:ws AND documentmaster_id=:did "
            "AND documentrevision_version=:ver AND iteration=:iter"),
            {"ws": ws, "did": doc_id, "ver": ver, "iter": src_iter},
        ).fetchall()
        for row in rows:
            db.execute(document_iteration_binres.insert().values(
                workspace_id=ws, documentmaster_id=doc_id,
                documentrevision_version=ver, iteration=dst_iter,
                attachedfile_fullname=row[0]))

    def checkin(self, db, ws, doc_id, ver, user_login):
        pr = self.get_revision(db, ws, doc_id, ver)
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
        return pr

    def undo_checkout(self, db, ws, doc_id, ver, user_login):
        pr = self.get_revision(db, ws, doc_id, ver)
        if pr.checkout_user_login != user_login:
            raise NotAllowedException("NotAllowedException19")
        if len(pr.iterations) <= 1:
            raise NotAllowedException("NotAllowedException27")
        last = pr.last_iteration
        if last and last.check_in_date is None:
            db.delete(last)
        pr.checkout_user_login = None
        pr.checkout_user_workspace_id = None
        pr.check_out_date = None
        db.commit(); db.refresh(pr)
        return pr

    def release(self, db, ws, doc_id, ver, user_login):
        pr = self.get_revision(db, ws, doc_id, ver)
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

    def update_iteration(self, db, ws, doc_id, ver, iteration, data):
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
                    "tws": ws,
                })
                link_id = result.fetchone()[0]
                db.execute(sql_text(
                    "INSERT INTO documentiteration_documentlink "
                    "(workspace_id, documentmaster_id, documentrevision_version, "
                    "iteration, documentlink_id) "
                    "VALUES (:ws, :did, :ver, :iter, :lid)"
                ), {"ws": ws, "did": doc_id, "ver": ver, "iter": iteration, "lid": link_id})
            di.modification_date = di_modification_date
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
        if pr.status != 1:
            raise NotAllowedException("NotAllowedException65")
        pr.status = 2
        pr.obsolete_date = datetime.utcnow()
        pr.obsolete_user_login = user_login
        pr.obsolete_user_workspace = ws
        db.commit(); db.refresh(pr)
        return pr

    def create_new_version(self, db, ws, doc_id, ver, user_login):
        pr = self.get_revision(db, ws, doc_id, ver)
        if pr.checkout_user_login:
            raise NotAllowedException("NotAllowedException40")
        if not pr.iterations:
            raise NotAllowedException("NotAllowedException27")
        now = datetime.utcnow()
        new_ver = self._next_version(ver)
        new_pr = DocumentRevision(
            workspace_id=ws, documentmaster_id=doc_id, version=new_ver,
            title=pr.title, description=pr.description, status=0,
            creation_date=now,
            location_completepath=pr.location_completepath,
            author_workspace_id=ws, author_login=user_login,
            checkout_user_workspace_id=ws, checkout_user_login=user_login,
            check_out_date=now)
        db.add(new_pr); db.flush()
        db.add(DocumentIteration(
            workspace_id=ws, documentmaster_id=doc_id,
            documentrevision_version=new_ver, iteration=1,
            creation_date=now, author_workspace_id=ws,
            author_login=user_login))
        db.commit(); db.refresh(new_pr)
        return new_pr

    def _ensure_tag(self, db, ws, label):
        from app.models.part import Tag
        t = db.query(Tag).filter(Tag.workspace_id == ws,
                                 Tag.label == label).first()
        if t is None:
            db.add(Tag(workspace_id=ws, label=label)); db.flush()

    def set_tags(self, db, ws, doc_id, ver, labels):
        pr = self.get_revision(db, ws, doc_id, ver)
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
        return pr

    def add_tag(self, db, ws, doc_id, ver, label):
        pr = self.get_revision(db, ws, doc_id, ver)
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

    def remove_tag(self, db, ws, doc_id, ver, label):
        pr = self.get_revision(db, ws, doc_id, ver)
        db.execute(document_revision_tags.delete().where(
            document_revision_tags.c.documentmaster_workspace_id == ws,
            document_revision_tags.c.documentmaster_id == doc_id,
            document_revision_tags.c.documentrevision_version == ver,
            document_revision_tags.c.tag_label == label,
        ))
        db.commit(); db.refresh(pr)
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

    def move_document(self, db, ws, doc_id, ver, folder_path):
        """移动文档到指定文件夹（更新 location_completepath）。"""
        pr = self.get_revision(db, ws, doc_id, ver)
        pr.location_completepath = folder_path
        db.commit()
        db.refresh(pr)
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
        # 返回该 workspace 下所有子文件夹（匹配 Payara 行为）
        return db.query(Folder).filter(
            Folder.completepath.startswith(f"{ws}/"),
        ).order_by(Folder.completepath).all()

    def rename_folder(self, db, completepath, new_name):
        folder = db.query(Folder).filter(
            Folder.completepath == completepath).first()
        if folder is None:
            raise HTTPException(404, "Folder not found")
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
            raise HTTPException(404, "Folder not found")
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
            raise HTTPException(404, "Template not found")
        return t

    def create_template(self, db, ws, template_id, document_type, mask,
                        id_generated, user_login):
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
            author_workspace_id=ws, author_login=user_login)
        db.add(t); db.commit(); db.refresh(t)
        return t

    def delete_template(self, db, ws, template_id):
        t = self.get_template(db, ws, template_id)
        db.delete(t); db.commit()

    def save_file(self, db, ws, doc_id, ver, iteration, filename, data):
        from app.services import vault as vault_svc
        from app.models.part import BinaryResource
        path = (vault_svc._vault_root() / ws / "documents" / doc_id
                / ver / str(iteration) / filename)
        vault_svc.write_file(path, data)
        full_name = f"{ws}/documents/{doc_id}/{ver}/{iteration}/{filename}"
        br = db.query(BinaryResource).filter(
            BinaryResource.full_name == full_name).first()
        now = datetime.utcnow()
        if br is None:
            br = BinaryResource(full_name=full_name, content_length=len(data),
                                last_modified=now, dtype="BinaryResource")
            db.add(br)
        else:
            br.content_length = len(data)
            br.last_modified = now
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
        db.commit()
        return br

    def get_file_bytes(self, ws, doc_id, ver, iteration, filename):
        from app.services import vault as vault_svc
        path = (vault_svc._vault_root() / ws / "documents" / doc_id
                / ver / str(iteration) / filename)
        return vault_svc.read_file(path)

    def _next_version(self, current):
        if not current: return "A"
        last_char = current[-1]
        if last_char == "Z": return current + "A"
        return current[:-1] + chr(ord(last_char) + 1)

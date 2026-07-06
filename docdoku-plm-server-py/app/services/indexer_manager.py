"""ES 索引管理——对标 Payara IndexerManagerBean + EntityMapper + IndexerMapping。

索引粒度：按 PartIteration/DocumentIteration（一个 iteration = 一个 ES doc）。
"""
import logging
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import ConnectionError as ESConnectionError, ConnectionTimeout as ESConnectionTimeout
from elasticsearch.helpers import bulk
from sqlalchemy import text
from app.core.config import settings
from app.core.exceptions import AccessRightException, WorkspaceAlreadyExistsException

logger = logging.getLogger(__name__)

# ── ES 常量（来源: IndexerMapping.java）───────────────────────
_INDEX_PREFIX = "docdoku-plm"
_INDEX_PARTS = "parts"
_INDEX_DOCUMENTS = "documents"
_BULK_SIZE = 50

# ES 字段 key（= IndexerMapping 常量值）────────────────────────
KEY_WORKSPACE_ID = "workspaceId"
KEY_ITERATION = "iteration"
KEY_VERSION = "version"
KEY_AUTHOR_LOGIN = "authorLogin"
KEY_AUTHOR_NAME = "authorName"
KEY_CREATION_DATE = "creationDate"
KEY_MODIFICATION_DATE = "modificationDate"
KEY_TYPE = "type"
KEY_PART_NUMBER = "partNumber"
KEY_PART_NAME = "partName"
KEY_TITLE = "title"
KEY_DOCM_ID = "docMId"
KEY_DESCRIPTION = "description"
KEY_REVISION_NOTE = "revisionNote"
KEY_STANDARD_PART = "standardPart"
KEY_FOLDER = "folder"
KEY_TAGS = "tags"
KEY_FILES = "files"
KEY_CONTENT = "content"
KEY_FILE_NAME = "fileName"
KEY_ATTRIBUTES = "attributes"
KEY_ATTR_NAME = "attr_name"
KEY_ATTR_VALUE = "attr_value"
KEY_WORKFLOW = "workflow"

PART_MAPPING = {
    KEY_PART_NUMBER: {"type": "text", "analyzer": "simple"},
    KEY_PART_NAME: {"type": "text"},
    KEY_VERSION: {"type": "keyword"},
    KEY_ITERATION: {"type": "integer"},
    KEY_DESCRIPTION: {"type": "text"},
    KEY_REVISION_NOTE: {"type": "text"},
    KEY_AUTHOR_LOGIN: {"type": "keyword"},
    KEY_AUTHOR_NAME: {"type": "keyword"},
    KEY_CREATION_DATE: {"type": "date"},
    KEY_MODIFICATION_DATE: {"type": "date"},
    KEY_TYPE: {"type": "keyword"},
    KEY_STANDARD_PART: {"type": "boolean"},
    KEY_WORKSPACE_ID: {"type": "keyword"},
    KEY_TAGS: {"type": "keyword"},
    KEY_WORKFLOW: {"type": "keyword"},
    KEY_ATTRIBUTES: {
        "type": "nested",
        "properties": {
            KEY_ATTR_NAME: {"type": "keyword"},
            KEY_ATTR_VALUE: {"type": "keyword"},
        },
    },
    KEY_FILES: {
        "type": "nested",
        "properties": {
            KEY_FILE_NAME: {"type": "keyword"},
            KEY_CONTENT: {"type": "text"},
        },
    },
}

DOC_MAPPING = {
    KEY_DOCM_ID: {"type": "keyword"},
    KEY_TITLE: {"type": "text"},
    KEY_VERSION: {"type": "keyword"},
    KEY_ITERATION: {"type": "integer"},
    KEY_DESCRIPTION: {"type": "text"},
    KEY_REVISION_NOTE: {"type": "text"},
    KEY_AUTHOR_LOGIN: {"type": "keyword"},
    KEY_AUTHOR_NAME: {"type": "keyword"},
    KEY_CREATION_DATE: {"type": "date"},
    KEY_MODIFICATION_DATE: {"type": "date"},
    KEY_TYPE: {"type": "keyword"},
    KEY_WORKSPACE_ID: {"type": "keyword"},
    KEY_FOLDER: {"type": "keyword"},
    KEY_TAGS: {"type": "keyword"},
    KEY_WORKFLOW: {"type": "keyword"},
    KEY_ATTRIBUTES: {
        "type": "nested",
        "properties": {
            KEY_ATTR_NAME: {"type": "keyword"},
            KEY_ATTR_VALUE: {"type": "keyword"},
        },
    },
    KEY_FILES: {
        "type": "nested",
        "properties": {
            KEY_FILE_NAME: {"type": "keyword"},
            KEY_CONTENT: {"type": "text"},
        },
    },
}


class IndexerManager:
    def __init__(self):
        self._es = None

    @property
    def es(self):
        if self._es is None:
            self._es = Elasticsearch([settings.ES_URL])
        return self._es

    def ping(self) -> bool:
        try:
            return self.es.ping()
        except Exception:
            return False

    # ── 索引命名（来源: IndexerMapping.java:24-41）─────────────────

    @staticmethod
    def _part_index(ws: str) -> str:
        return f"{_INDEX_PREFIX}-{ws.lower()}-{_INDEX_PARTS}"

    @staticmethod
    def _doc_index(ws: str) -> str:
        return f"{_INDEX_PREFIX}-{ws.lower()}-{_INDEX_DOCUMENTS}"

    # ── 索引生命周期 ──────────────────────────────────────────────

    def create_index(self, ws: str):
        try:
            for idx, mapping in [
                (self._part_index(ws), PART_MAPPING),
                (self._doc_index(ws), DOC_MAPPING),
            ]:
                if self.es.indices.exists(index=idx):
                    raise WorkspaceAlreadyExistsException(ws)
                self.es.indices.create(index=idx, body={"mappings": {"_doc": {"properties": mapping}}})
        except WorkspaceAlreadyExistsException:
            logger.warning("ES index already exists for workspace %s", ws)
        except Exception:
            logger.warning("Cannot create ES index for workspace %s", ws, exc_info=True)

    def delete_index(self, ws: str):
        try:
            for idx in [self._part_index(ws), self._doc_index(ws)]:
                if self.es.indices.exists(index=idx):
                    self.es.indices.delete(index=idx)
        except Exception:
            logger.warning("Cannot delete ES index for workspace %s", ws, exc_info=True)

    # ── 序列化：PartIteration/DocumentIteration → ES doc ─────────
    # 字段来源对照 EntityMapper.java:71-93 (part) + 48-68 (document)
    # 作者来源：PartMaster/DocumentMaster 级别（非 PartRevision/DocumentRevision）

    @staticmethod
    def _part_iteration_to_doc(pi, author_name=None, attributes=None,
                               attached_file_names=None, workflow_state=None) -> dict:
        """PartIteration → ES doc（EntityMapper.partIterationToJSON）。"""
        pr = pi.revision
        pm = pr.part_master if pr else None
        doc = {
            KEY_WORKSPACE_ID: pi.workspace_id,
            KEY_PART_NUMBER: pi.partmaster_partnumber,
            KEY_PART_NAME: pm.name if pm else "",
            KEY_TYPE: pm.type if pm else "",
            KEY_VERSION: pi.partrevision_version,
            KEY_DESCRIPTION: pr.description or "" if pr else "",
            KEY_ITERATION: pi.iteration,
            KEY_STANDARD_PART: pm.standard_part if pm else False,
            KEY_CREATION_DATE: pi.creation_date.isoformat() if pi.creation_date else None,
            KEY_MODIFICATION_DATE: pi.modification_date.isoformat() if pi.modification_date else None,
            KEY_REVISION_NOTE: pi.iteration_note or "",
            KEY_AUTHOR_LOGIN: pm.author_login or "" if pm else "",
            KEY_AUTHOR_NAME: author_name if author_name is not None else (pm.author_login or "" if pm else ""),
        }
        if pr and hasattr(pr, "tags"):
            try:
                if pr.tags:
                    doc[KEY_TAGS] = [tag.label for tag in pr.tags]
            except Exception:
                pass
        if attributes:
            doc[KEY_ATTRIBUTES] = attributes
        if attached_file_names:
            doc[KEY_FILES] = [{"fileName": fn, "content": ""} for fn in attached_file_names]
        if workflow_state:
            doc[KEY_WORKFLOW] = workflow_state
        return {k: v for k, v in doc.items() if v is not None}

    @staticmethod
    def _doc_iteration_to_doc(di, author_name=None, attributes=None,
                              attached_file_names=None, workflow_state=None) -> dict:
        """DocumentIteration → ES doc（EntityMapper.documentIterationToJSON）。"""
        dr = di.revision
        dm = dr.document_master if dr else None
        doc = {
            KEY_WORKSPACE_ID: di.workspace_id,
            KEY_DOCM_ID: di.documentmaster_id,
            KEY_TITLE: dr.title or "" if dr else "",
            KEY_TYPE: dm.type if dm else "",
            KEY_VERSION: di.documentrevision_version,
            KEY_DESCRIPTION: dr.description or "" if dr else "",
            KEY_ITERATION: di.iteration,
            KEY_CREATION_DATE: dr.creation_date.isoformat() if dr.creation_date else None,
            KEY_MODIFICATION_DATE: di.modification_date.isoformat() if di.modification_date else None,
            KEY_REVISION_NOTE: di.revision_note or "",
            KEY_AUTHOR_LOGIN: dm.author_login or "" if dm else "",
            KEY_AUTHOR_NAME: author_name if author_name is not None else (dm.author_login or "" if dm else ""),
            KEY_FOLDER: dr.location_completepath.rsplit("/", 1)[-1] if dr and dr.location_completepath else None,
        }
        if dr and hasattr(dr, "tags"):
            try:
                if dr.tags:
                    doc[KEY_TAGS] = [tag.label for tag in dr.tags]
            except Exception:
                pass
        if attributes:
            doc[KEY_ATTRIBUTES] = attributes
        if attached_file_names:
            doc[KEY_FILES] = [{"fileName": fn, "content": ""} for fn in attached_file_names]
        if workflow_state:
            doc[KEY_WORKFLOW] = workflow_state
        return {k: v for k, v in doc.items() if v is not None}

    @staticmethod
    def _part_iteration_id(pi) -> str:
        return f"{pi.partmaster_partnumber.lower()}-{pi.partrevision_version}-{pi.iteration}"

    @staticmethod
    def _doc_iteration_id(di) -> str:
        return f"{di.documentmaster_id.lower()}-{di.documentrevision_version}-{di.iteration}"

    # ── 实时索引：单 iteration ────────────────────────────────────

    def index_part_iteration(self, pi, author_name=None,
                             attributes=None, attached_file_names=None, workflow_state=None):
        try:
            doc = self._part_iteration_to_doc(
                pi, author_name=author_name,
                attributes=attributes, attached_file_names=attached_file_names,
                workflow_state=workflow_state,
            )
            self.es.index(index=self._part_index(pi.workspace_id), doc_type="_doc",
                          id=self._part_iteration_id(pi), body=doc)
        except (ESConnectionError, ESConnectionTimeout):
            logger.error("ES index failed for part %s-%s-%s",
                         pi.partmaster_partnumber, pi.partrevision_version, pi.iteration,
                         exc_info=True)
        except Exception:
            logger.warning("ES index failed for part %s-%s-%s",
                           pi.partmaster_partnumber, pi.partrevision_version, pi.iteration,
                           exc_info=True)

    def index_document_iteration(self, di, author_name=None,
                                 attributes=None, attached_file_names=None, workflow_state=None):
        try:
            doc = self._doc_iteration_to_doc(
                di, author_name=author_name,
                attributes=attributes, attached_file_names=attached_file_names,
                workflow_state=workflow_state,
            )
            self.es.index(index=self._doc_index(di.workspace_id), doc_type="_doc",
                          id=self._doc_iteration_id(di), body=doc)
        except (ESConnectionError, ESConnectionTimeout):
            logger.error("ES index failed for document %s-%s-%s",
                         di.documentmaster_id, di.documentrevision_version, di.iteration,
                         exc_info=True)
        except Exception:
            logger.warning("ES index failed for document %s-%s-%s",
                           di.documentmaster_id, di.documentrevision_version, di.iteration,
                           exc_info=True)

    def index_part_iterations(self, iterations: list, author_name=None):
        """便捷方法：批量索引 PartIteration 列表。"""
        for pi in iterations:
            self.index_part_iteration(pi, author_name=author_name)

    def index_document_iterations(self, iterations: list, author_name=None):
        """便捷方法：批量索引 DocumentIteration 列表。"""
        for di in iterations:
            self.index_document_iteration(di, author_name=author_name)

    # ── 实时索引：revision 便捷封装 ────────────────────────────────

    def index_part_revision(self, pr, author_name=None):
        for pi in pr.iterations:
            self.index_part_iteration(pi, author_name=author_name)

    def index_document_revision(self, dr, author_name=None):
        for di in dr.iterations:
            self.index_document_iteration(di, author_name=author_name)

    # ── 删除 ─────────────────────────────────────────────────────

    def delete_part_revision(self, pr):
        idx = self._part_index(pr.workspace_id)
        try:
            for pi in pr.iterations:
                self.es.delete(index=idx, doc_type="_doc",
                               id=self._part_iteration_id(pi), ignore=[404])
        except Exception:
            logger.warning("ES delete failed for part %s-%s",
                           pr.partmaster_partnumber, pr.version, exc_info=True)

    def delete_document_revision(self, dr):
        idx = self._doc_index(dr.workspace_id)
        try:
            for di in dr.iterations:
                self.es.delete(index=idx, doc_type="_doc",
                               id=self._doc_iteration_id(di), ignore=[404])
        except Exception:
            logger.warning("ES delete failed for document %s-%s",
                           dr.documentmaster_id, dr.version, exc_info=True)

    # ── 管理员检查 ──────────────────────────────────────────────────

    @staticmethod
    def _check_admin(db, ws: str, current_user):
        """检查用户是否为全局 admin 或工作区 admin。"""
        if not current_user or not current_user.login:
            raise AccessRightException("AccessRightException")

        # 检查全局 admin
        from app.models.auth import UserGroupMapping
        mapping = db.query(UserGroupMapping).filter(
            UserGroupMapping.login == current_user.login,
            UserGroupMapping.groupname == "admin",
        ).first()
        if mapping:
            return

        # 检查 workspace 级别 admin
        row = db.execute(
            text("SELECT 1 FROM workspace WHERE id=:w AND admin_login=:l"),
            {"w": ws, "l": current_user.login},
        ).fetchone()
        if not row:
            raise AccessRightException("AccessRightException")

    # ── 全量重建 ──────────────────────────────────────────────────

    def reindex_all(self, db, ws: str, current_user=None, check_admin: bool = False) -> dict:
        """全量重建。BULK_SIZE=50 分页，对齐 Java doIndexWorkspaceData。"""
        if check_admin:
            self._check_admin(db, ws, current_user)

        self.delete_index(ws)
        self.create_index(ws)

        errors = []
        parts_count = self._bulk_index_parts(db, ws, errors)
        docs_count = self._bulk_index_documents(db, ws, errors)

        result = {"parts": parts_count, "documents": docs_count, "errors": errors}

        if current_user and current_user.email:
            try:
                from app.services.notifier import send_reindex_notification
                send_reindex_notification(
                    to_email=current_user.email,
                    locale=getattr(current_user, "language", "en") or "en",
                    ws=ws,
                    result=result,
                )
            except Exception:
                logger.warning("Failed to send reindex notification", exc_info=True)

        return result

    def index_all_workspaces_data(self, db, current_user=None, check_admin: bool = False) -> dict:
        """遍历所有 workspace，逐一重建索引。"""
        rows = db.execute(text("SELECT id FROM workspace ORDER BY id")).fetchall()
        results = {}
        for (ws,) in rows:
            results[ws] = self.reindex_all(db, ws, current_user, check_admin=check_admin)
        return results

    # ── bulk 批次处理 ──────────────────────────────────────────

    def _bulk_index_parts(self, db, ws: str, errors: list) -> int:
        from app.models.part import PartRevision
        from app.models.auth import Account
        from app.models.workflow import Workflow
        from sqlalchemy.orm import joinedload

        total, offset = 0, 0
        while True:
            batch = db.query(PartRevision).options(
                joinedload(PartRevision.iterations),
                joinedload(PartRevision.part_master),
            ).filter(PartRevision.workspace_id == ws).order_by(
                PartRevision.partmaster_partnumber, PartRevision.version
            ).limit(_BULK_SIZE).offset(offset).all()
            if not batch:
                break

            # ── 收集 master 级作者登录名 ──
            author_logins = list({pr.part_master.author_login for pr in batch
                                  if pr.part_master and pr.part_master.author_login})
            name_map = {}
            if author_logins:
                accounts = db.query(Account).filter(Account.login.in_(author_logins)).all()
                name_map = {a.login: a.name for a in accounts}

            # ── 构建 ES actions ──
            actions = []
            for pr in batch:
                author_name = name_map.get(pr.part_master.author_login) if pr.part_master and pr.part_master.author_login else None
                for pi in pr.iterations:
                    if not pi.check_in_date:
                        continue
                    doc = self._part_iteration_to_doc(pi, author_name=author_name)
                    actions.append({
                        "_index": self._part_index(ws),
                        "_type": "_doc",
                        "_id": self._part_iteration_id(pi),
                        "_source": doc,
                    })
            if actions:
                try:
                    success, batch_errors = bulk(self.es, actions, raise_on_error=False)
                    errors.extend(batch_errors)
                except Exception:
                    logger.warning("ES bulk index failed for parts offset=%s", offset, exc_info=True)
                    errors.append(f"ES bulk index failed for parts offset={offset}")
            total += len(actions)
            offset += _BULK_SIZE
        return total

    def _bulk_index_documents(self, db, ws: str, errors: list) -> int:
        from app.models.document import DocumentRevision
        from app.models.auth import Account
        from app.models.workflow import Workflow
        from sqlalchemy.orm import joinedload

        total, offset = 0, 0
        while True:
            batch = db.query(DocumentRevision).options(
                joinedload(DocumentRevision.iterations),
                joinedload(DocumentRevision.document_master),
            ).filter(DocumentRevision.workspace_id == ws).order_by(
                DocumentRevision.documentmaster_id, DocumentRevision.version
            ).limit(_BULK_SIZE).offset(offset).all()
            if not batch:
                break

            # ── 收集 master 级作者登录名 ──
            author_logins = list({dr.document_master.author_login for dr in batch
                                  if dr.document_master and dr.document_master.author_login})
            name_map = {}
            if author_logins:
                accounts = db.query(Account).filter(Account.login.in_(author_logins)).all()
                name_map = {a.login: a.name for a in accounts}

            # ── 构建 ES actions ──
            actions = []
            for dr in batch:
                author_name = name_map.get(dr.document_master.author_login) if dr.document_master and dr.document_master.author_login else None
                for di in dr.iterations:
                    if not di.check_in_date:
                        continue
                    doc = self._doc_iteration_to_doc(di, author_name=author_name)
                    actions.append({
                        "_index": self._doc_index(ws),
                        "_type": "_doc",
                        "_id": self._doc_iteration_id(di),
                        "_source": doc,
                    })
            if actions:
                try:
                    success, batch_errors = bulk(self.es, actions, raise_on_error=False)
                    errors.extend(batch_errors)
                except Exception:
                    logger.warning("ES bulk index failed for documents offset=%s", offset, exc_info=True)
                    errors.append(f"ES bulk index failed for documents offset={offset}")
            total += len(actions)
            offset += _BULK_SIZE
        return total


indexer_manager = IndexerManager()

import logging
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
from app.core.config import settings

logger = logging.getLogger(__name__)

PART_MAPPING = {
    "partNumber": {"type": "text", "analyzer": "simple"},
    "partName": {"type": "text"},
    "partKey": {"type": "keyword"},
    "version": {"type": "keyword"},
    "iteration": {"type": "integer"},
    "description": {"type": "text"},
    "revisionNote": {"type": "text"},
    "authorLogin": {"type": "keyword"},
    "authorName": {"type": "keyword"},
    "creationDate": {"type": "date"},
    "modificationDate": {"type": "date"},
    "standardPart": {"type": "boolean"},
    "workspaceId": {"type": "keyword"},
}

DOC_MAPPING = {
    "docKey": {"type": "keyword"},
    "docMasterId": {"type": "keyword"},
    "title": {"type": "text"},
    "version": {"type": "keyword"},
    "iteration": {"type": "integer"},
    "description": {"type": "text"},
    "revisionNote": {"type": "text"},
    "authorLogin": {"type": "keyword"},
    "authorName": {"type": "keyword"},
    "creationDate": {"type": "date"},
    "modificationDate": {"type": "date"},
    "workspaceId": {"type": "keyword"},
}


class IndexerManager:
    def __init__(self):
        self._es = None

    @property
    def es(self):
        if self._es is None:
            self._es = Elasticsearch([settings.ES_URL])
        return self._es

    def _part_index_name(self, ws: str) -> str:
        return f"parts-{ws.lower()}"

    def _doc_index_name(self, ws: str) -> str:
        return f"documents-{ws.lower()}"

    def create_index(self, ws: str):
        try:
            for prefix, mapping in [(_part_index_name, PART_MAPPING), (_doc_index_name, DOC_MAPPING)]:
                idx = prefix(ws)
                if not self.es.indices.exists(index=idx):
                    self.es.indices.create(index=idx, body={"mappings": {"_doc": {"properties": mapping}}})
        except Exception:
            logger.warning(f"Failed to create ES index for workspace {ws}", exc_info=True)

    def delete_index(self, ws: str):
        try:
            for prefix in [_part_index_name, _doc_index_name]:
                idx = prefix(ws)
                if self.es.indices.exists(index=idx):
                    self.es.indices.delete(index=idx)
        except Exception:
            logger.warning(f"Failed to delete ES index for workspace {ws}", exc_info=True)

    def _part_to_doc(self, pr) -> dict:
        it = pr.last_iteration
        pm = pr.part_master
        return {
            "partKey": f"{pm.number}-{pr.version}",
            "partNumber": pm.number,
            "partName": pm.name,
            "version": pr.version,
            "iteration": it.iteration if it else 0,
            "description": pr.description,
            "revisionNote": it.iteration_note if it else "",
            "authorLogin": pr.author_login or "",
            "authorName": pr.author_login or "",
            "creationDate": pr.creation_date.isoformat() if pr.creation_date else None,
            "modificationDate": it.modification_date.isoformat() if it and it.modification_date else None,
            "standardPart": pm.standard_part or False,
            "workspaceId": pr.workspace_id,
        }

    def _doc_to_es_doc(self, dr) -> dict:
        it = dr.last_iteration
        return {
            "docKey": f"{dr.documentmaster_id}-{dr.version}",
            "docMasterId": dr.documentmaster_id,
            "title": dr.title,
            "version": dr.version,
            "iteration": it.iteration if it else 0,
            "description": dr.description,
            "revisionNote": it.revision_note if it else "",
            "authorLogin": dr.author_login or "",
            "authorName": dr.author_login or "",
            "creationDate": dr.creation_date.isoformat() if dr.creation_date else None,
            "modificationDate": it.modification_date.isoformat() if it and it.modification_date else None,
            "workspaceId": dr.workspace_id,
        }

    def index_part_revision(self, pr):
        try:
            idx = self._part_index_name(pr.workspace_id)
            doc = self._part_to_doc(pr)
            self.es.index(index=idx, doc_type="_doc", id=doc["partKey"], body=doc)
        except Exception:
            logger.warning(f"ES index failed for part {pr.partmaster_partnumber}-{pr.version}", exc_info=True)

    def delete_part_revision(self, key: str, ws: str):
        try:
            idx = self._part_index_name(ws)
            self.es.delete(index=idx, doc_type="_doc", id=key, ignore=[404])
        except Exception:
            logger.warning(f"ES delete failed for part {key}", exc_info=True)

    def index_document_revision(self, dr):
        try:
            idx = self._doc_index_name(dr.workspace_id)
            doc = self._doc_to_es_doc(dr)
            self.es.index(index=idx, doc_type="_doc", id=doc["docKey"], body=doc)
        except Exception:
            logger.warning(f"ES index failed for document {dr.documentmaster_id}-{dr.version}", exc_info=True)

    def delete_document_revision(self, key: str, ws: str):
        try:
            idx = self._doc_index_name(ws)
            self.es.delete(index=idx, doc_type="_doc", id=key, ignore=[404])
        except Exception:
            logger.warning(f"ES delete failed for document {key}", exc_info=True)

    def reindex_all(self, db, ws: str):
        from app.models.part import PartRevision
        from app.models.document import DocumentRevision
        from sqlalchemy.orm import joinedload

        self.delete_index(ws)
        self.create_index(ws)

        parts = db.query(PartRevision).options(
            joinedload(PartRevision.iterations),
            joinedload(PartRevision.part_master),
        ).filter(PartRevision.workspace_id == ws).all()

        docs = db.query(DocumentRevision).options(
            joinedload(DocumentRevision.iterations),
        ).filter(DocumentRevision.workspace_id == ws).all()

        count_parts = 0
        count_docs = 0
        try:
            actions = []
            for pr in parts:
                doc = self._part_to_doc(pr)
                actions.append({"_index": self._part_index_name(ws), "_type": "_doc", "_id": doc["partKey"], "_source": doc})
            if actions:
                bulk(self.es, actions)
            count_parts = len(actions)

            actions = []
            for dr in docs:
                doc = self._doc_to_es_doc(dr)
                actions.append({"_index": self._doc_index_name(ws), "_type": "_doc", "_id": doc["docKey"], "_source": doc})
            if actions:
                bulk(self.es, actions)
            count_docs = len(actions)
        except Exception:
            logger.warning(f"ES reindex failed for workspace {ws}", exc_info=True)

        return {"parts": count_parts, "documents": count_docs}


indexer_manager = IndexerManager()

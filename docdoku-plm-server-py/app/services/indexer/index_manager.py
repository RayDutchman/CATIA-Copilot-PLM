"""ES 索引管理——对标 Payara IndexManagerBean。

低层 ES 操作：连接、索引生命周期、单文档索引/删除、Bulk、搜索。
"""
import logging
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import ConnectionError as ESConnectionError, ConnectionTimeout as ESConnectionTimeout
from elasticsearch.helpers import bulk
from app.core.config import settings
from app.core.exceptions import WorkspaceAlreadyExistsException

logger = logging.getLogger(__name__)

_INDEX_PREFIX = "docdoku-plm"
_INDEX_PARTS = "parts"
_INDEX_DOCUMENTS = "documents"


class IndexManager:
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
    def part_index(ws: str) -> str:
        return f"{_INDEX_PREFIX}-{ws.lower()}-{_INDEX_PARTS}"

    @staticmethod
    def doc_index(ws: str) -> str:
        return f"{_INDEX_PREFIX}-{ws.lower()}-{_INDEX_DOCUMENTS}"

    # ── 索引生命周期 ──────────────────────────────────────────────

    def create_indices(self, ws: str, part_mapping: dict, doc_mapping: dict):
        try:
            for idx, mapping in [
                (self.part_index(ws), part_mapping),
                (self.doc_index(ws), doc_mapping),
            ]:
                if self.es.indices.exists(index=idx):
                    raise WorkspaceAlreadyExistsException(ws)
                self.es.indices.create(index=idx, body={"mappings": {"_doc": {"properties": mapping}}})
        except WorkspaceAlreadyExistsException:
            logger.warning("ES index already exists for workspace %s", ws)
        except Exception:
            logger.warning("Cannot create ES index for workspace %s", ws, exc_info=True)

    def delete_indices(self, ws: str):
        try:
            for idx in [self.part_index(ws), self.doc_index(ws)]:
                if self.es.indices.exists(index=idx):
                    self.es.indices.delete(index=idx)
        except Exception:
            logger.warning("Cannot delete ES index for workspace %s", ws, exc_info=True)

    def indices_exist(self, ws: str) -> bool:
        try:
            pi = self.part_index(ws)
            di = self.doc_index(ws)
            return self.es.indices.exists(index=pi) and self.es.indices.exists(index=di)
        except Exception:
            return False

    # ── 单文档操作 ─────────────────────────────────────────────────

    def index_document(self, index: str, doc_id: str, body: dict):
        """写入单个 ES 文档。"""
        try:
            self.es.index(index=index, doc_type="_doc", id=doc_id, body=body)
        except (ESConnectionError, ESConnectionTimeout):
            logger.error("ES index failed for %s/%s", index, doc_id, exc_info=True)
        except Exception:
            logger.warning("ES index failed for %s/%s", index, doc_id, exc_info=True)

    def delete_document(self, index: str, doc_id: str):
        """删除单个 ES 文档。"""
        try:
            self.es.delete(index=index, doc_type="_doc", id=doc_id, ignore=[404])
        except Exception:
            logger.warning("ES delete failed for %s/%s", index, doc_id, exc_info=True)

    # ── Bulk 操作 ─────────────────────────────────────────────────

    def bulk_actions(self, actions: list) -> tuple:
        """执行 bulk 写入，返回 (success_count, errors)。"""
        try:
            success, errors = bulk(self.es, actions, raise_on_error=False)
            return success, errors
        except Exception:
            logger.warning("ES bulk failed", exc_info=True)
            return 0, ["ES bulk error"]

    # ── 搜索 ─────────────────────────────────────────────────────

    def search(self, index: str, body: dict, **kwargs):
        """执行 ES 搜索，返回原生 ES response。"""
        return self.es.search(index=index, body=body, **kwargs)


index_manager = IndexManager()

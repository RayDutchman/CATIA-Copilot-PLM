"""IndexerClient——ES 客户端代理。

对齐 Java IndexerClientProducer。提供 ES 客户端实例获取。
"""
import os
from elasticsearch import Elasticsearch
from app.core.config import settings


class IndexerClient:
    """ES 客户端管理器。"""

    def __init__(self):
        self._client = None

    @property
    def client(self) -> Elasticsearch:
        """获取 Elasticsearch 客户端（懒初始化）。"""
        if self._client is None:
            es_url = getattr(settings, 'ES_URL', os.getenv('ES_URL', 'http://es:9200'))
            es_user = getattr(settings, 'ES_USER', os.getenv('ES_USER'))
            es_pass = getattr(settings, 'ES_PASSWORD', os.getenv('ES_PASSWORD'))
            if es_user:
                self._client = Elasticsearch(
                    [es_url],
                    http_auth=(es_user, es_pass),
                    verify_certs=False,
                )
            else:
                self._client = Elasticsearch([es_url])
        return self._client

    def close(self):
        """关闭 ES 客户端连接。"""
        if self._client:
            self._client.close()
            self._client = None


indexer_client = IndexerClient()

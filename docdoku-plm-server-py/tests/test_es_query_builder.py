"""ES es_query_builder 集成测试——真实 DB 数据 + Mock ES 客户端。"""
import pytest
from unittest.mock import MagicMock
from app.services.es_query_builder import es_query_builder
from app.services.indexer_manager import indexer_manager as im

WS = "Workspace_2"


@pytest.fixture
def mock_es():
    """每个测试独立的 ES mock。"""
    saved = im._es
    im._es = MagicMock()
    im._es.search.return_value = {"hits": {"hits": []}}
    yield im._es
    im._es = saved


class TestSearchParts:
    def test_empty_params_match_all(self, mock_es):
        es_query_builder.search_parts(WS, {})
        body = mock_es.search.call_args[1]["body"]
        assert body["query"] == {"match_all": {}}

    def test_number_match(self, mock_es):
        es_query_builder.search_parts(WS, {"number": "PN-001"})
        body = mock_es.search.call_args[1]["body"]
        must = body["query"]["bool"]["must"]
        assert {"match": {"partNumber": "PN-001"}} in must

    def test_name_fuzzy(self, mock_es):
        es_query_builder.search_parts(WS, {"name": "bracket"})
        body = mock_es.search.call_args[1]["body"]
        must = body["query"]["bool"]["must"]
        assert {"match": {"partName": {"query": "bracket", "fuzziness": "AUTO"}}} in must

    def test_q_query_string(self, mock_es):
        """验证 q 使用 query_string（搜索全字段）。"""
        es_query_builder.search_parts(WS, {"q": "bolt M6"})
        body = mock_es.search.call_args[1]["body"]
        must = body["query"]["bool"]["must"]
        qs = [m for m in must if "query_string" in str(m)]
        assert len(qs) > 0, f"No query_string found in must: {must}"

    def test_version_term(self, mock_es):
        es_query_builder.search_parts(WS, {"version": "A"})
        body = mock_es.search.call_args[1]["body"]
        must = body["query"]["bool"]["must"]
        assert {"term": {"version": "A"}} in must

    def test_author_should(self, mock_es):
        es_query_builder.search_parts(WS, {"author": "john"})
        body = mock_es.search.call_args[1]["body"]
        must = body["query"]["bool"]["must"]
        author_q = [m for m in must if "bool" in m and "should" in m["bool"]]
        assert len(author_q) >= 1, f"No author should query: {must}"
        should_clauses = author_q[0]["bool"]["should"]
        assert len(should_clauses) == 2

    def test_date_range(self, mock_es):
        es_query_builder.search_parts(WS, {"createdFrom": "2024-01-01", "modifiedTo": "2024-12-31"})
        body = mock_es.search.call_args[1]["body"]
        must = body["query"]["bool"]["must"]
        assert {"range": {"creationDate": {"gte": "2024-01-01"}}} in must
        assert {"range": {"modificationDate": {"lte": "2024-12-31"}}} in must

    def test_pagination(self, mock_es):
        es_query_builder.search_parts(WS, {"from": 20, "size": 10})
        body = mock_es.search.call_args[1]["body"]
        assert body["from"] == 20
        assert body["size"] == 10

    def test_returns_ids(self, mock_es):
        mock_es.search.return_value = {
            "hits": {"hits": [{"_id": "P1-A-1"}, {"_id": "P1-A-2"}]}
        }
        result = es_query_builder.search_parts(WS, {})
        assert result == ["P1-A-1", "P1-A-2"]

    def test_index_naming(self, mock_es):
        es_query_builder.search_parts(WS, {})
        idx = mock_es.search.call_args[1]["index"]
        assert idx == f"docdoku-plm-{WS.lower()}-parts"

    def test_attributes_search(self, mock_es):
        """attributes nested query 构建。"""
        es_query_builder.search_parts(WS, {"attributes": "TEXT:material:steel;NUMBER:weight:5.0"})
        body = mock_es.search.call_args[1]["body"]
        must = body["query"]["bool"]["must"]
        nested_qs = [m for m in must if "nested" in m]
        assert len(nested_qs) >= 2, f"Expected >=2 nested queries, got: {nested_qs}"


class TestSearchDocuments:
    def test_empty_params(self, mock_es):
        es_query_builder.search_documents(WS, {})
        body = mock_es.search.call_args[1]["body"]
        assert body["query"] == {"match_all": {}}

    def test_id_match(self, mock_es):
        es_query_builder.search_documents(WS, {"id": "DOC1"})
        body = mock_es.search.call_args[1]["body"]
        must = body["query"]["bool"]["must"]
        assert {"match": {"docMId": "DOC1"}} in must

    def test_title_fuzzy(self, mock_es):
        es_query_builder.search_documents(WS, {"title": "spec"})
        body = mock_es.search.call_args[1]["body"]
        must = body["query"]["bool"]["must"]
        assert {"match": {"title": {"query": "spec", "fuzziness": "AUTO"}}} in must

    def test_folder_fuzzy(self, mock_es):
        es_query_builder.search_documents(WS, {"folder": "engine"})
        body = mock_es.search.call_args[1]["body"]
        must = body["query"]["bool"]["must"]
        assert {"match": {"folder": {"query": "engine", "fuzziness": "AUTO"}}} in must

    def test_nested_content(self, mock_es):
        es_query_builder.search_documents(WS, {"content": "important"})
        body = mock_es.search.call_args[1]["body"]
        must = body["query"]["bool"]["must"]
        nested_q = [m for m in must if "nested" in m]
        assert len(nested_q) >= 1
        assert nested_q[0]["nested"]["path"] == "files"

    def test_tags_terms(self, mock_es):
        es_query_builder.search_documents(WS, {"tags": "a, b , c"})
        body = mock_es.search.call_args[1]["body"]
        must = body["query"]["bool"]["must"]
        tags_q = [m for m in must if "terms" in m]
        assert len(tags_q) == 1
        assert set(tags_q[0]["terms"]["tags"]) == {"a", "b", "c"}

    def test_doc_index_naming(self, mock_es):
        es_query_builder.search_documents(WS, {})
        idx = mock_es.search.call_args[1]["index"]
        assert idx == f"docdoku-plm-{WS.lower()}-documents"


class TestPing:
    def test_ping(self, mock_es):
        mock_es.ping.return_value = True
        assert es_query_builder.ping() is True


class TestErrorHandling:
    def test_connection_error_returns_empty(self, mock_es):
        mock_es.search.side_effect = ConnectionError("ES down")
        result = es_query_builder.search_parts(WS, {})
        assert result == []

    def test_timeout_returns_empty(self, mock_es):
        mock_es.search.side_effect = ConnectionError("timeout")
        result = es_query_builder.search_documents(WS, {"q": "test"})
        assert result == []

"""ES indexer_manager 集成测试——真实 DB 数据 + Mock ES 客户端。"""
import pytest
from unittest.mock import MagicMock
from app.services.indexer_manager import indexer_manager as im
from app.models.part import PartRevision
from app.models.document import DocumentRevision
from sqlalchemy.orm import joinedload

WS = "Workspace_2"


@pytest.fixture
def mock_es():
    saved = im._es
    im._es = MagicMock()
    im._es.indices.exists.return_value = False
    yield im._es
    im._es = saved


@pytest.fixture
def part_revision(db):
    """查询 DB 中任意一个有 iteration 的 PartRevision。"""
    pr = db.query(PartRevision).options(
        joinedload(PartRevision.iterations),
        joinedload(PartRevision.part_master),
    ).filter(
        PartRevision.workspace_id == WS,
    ).first()
    if pr is None or not pr.iterations:
        pytest.skip("No PartRevision with iterations in DB")
    return pr


@pytest.fixture
def doc_revision(db):
    """查询 DB 中任意一个有 iteration 的 DocumentRevision。"""
    dr = db.query(DocumentRevision).options(
        joinedload(DocumentRevision.iterations),
    ).filter(
        DocumentRevision.workspace_id == WS,
    ).first()
    if dr is None or not dr.iterations:
        pytest.skip("No DocumentRevision with iterations in DB")
    return dr


class TestIndexNaming:
    def test_part_index(self):
        assert im._part_index("WS1") == "docdoku-plm-ws1-parts"

    def test_doc_index(self):
        assert im._doc_index("WS1") == "docdoku-plm-ws1-documents"


class TestPartIterationToDoc:
    def test_real_data(self, part_revision):
        pi = part_revision.iterations[0]
        doc = im._part_iteration_to_doc(pi)
        assert doc["partNumber"] == pi.partmaster_partnumber
        assert doc["version"] == pi.partrevision_version
        assert doc["iteration"] == pi.iteration
        assert "workspaceId" in doc
        assert "description" in doc


class TestIndexPartRevision:
    def test_indexes_all_iterations(self, part_revision, mock_es):
        iterations = len(part_revision.iterations)
        im.index_part_revision(part_revision)
        assert mock_es.index.call_count == iterations
        for c in mock_es.index.call_args_list:
            assert c[1]["index"] == f"docdoku-plm-{WS.lower()}-parts"
            assert c[1]["doc_type"] == "_doc"
            assert c[1]["id"].startswith(part_revision.partmaster_partnumber.lower())


class TestDeletePartRevision:
    def test_deletes_all_iterations(self, part_revision, mock_es):
        iterations = len(part_revision.iterations)
        im.delete_part_revision(part_revision)
        assert mock_es.delete.call_count == iterations
        for c in mock_es.delete.call_args_list:
            assert c[1]["index"] == f"docdoku-plm-{WS.lower()}-parts"
            assert c[1]["ignore"] == [404]


class TestDocumentIndexing:
    def test_indexes_doc_iterations(self, doc_revision, mock_es):
        iterations = len(doc_revision.iterations)
        im.index_document_revision(doc_revision)
        assert mock_es.index.call_count == iterations
        for c in mock_es.index.call_args_list:
            assert c[1]["index"] == f"docdoku-plm-{WS.lower()}-documents"

    def test_deletes_doc_iterations(self, doc_revision, mock_es):
        iterations = len(doc_revision.iterations)
        im.delete_document_revision(doc_revision)
        assert mock_es.delete.call_count == iterations


class TestIndexLifecycle:
    def test_create_index(self, mock_es):
        im.create_index("TestWS")
        assert mock_es.indices.exists.call_count >= 2
        assert mock_es.indices.create.call_count == 2

    def test_delete_index(self, mock_es):
        mock_es.indices.exists.return_value = True
        im.delete_index("TestWS")
        assert mock_es.indices.exists.call_count >= 2
        assert mock_es.indices.delete.call_count == 2


class TestPing:
    def test_ping(self, mock_es):
        mock_es.ping.return_value = True
        assert im.ping() is True
        mock_es.ping.return_value = False
        assert im.ping() is False


class TestReindexAll:
    def test_reindex_all_with_data(self, db, mock_es):
        mock_es.indices.exists.return_value = False
        result = im.reindex_all(db, WS)
        assert "parts" in result
        assert "documents" in result
        assert isinstance(result["parts"], int)
        assert isinstance(result["documents"], int)

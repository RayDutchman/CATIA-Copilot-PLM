from app.services.document_service import DocumentService
from app.core.exceptions import EntityAlreadyExistsException
WS = "Workspace_2"
svc = DocumentService()


def _make(db, doc_id):
    return svc.create_document(db, WS, doc_id, "T", "test1")


def test_create_and_delete(db):
    pr = _make(db, "P2SVC-1")
    assert pr.documentmaster_id == "P2SVC-1"
    assert pr.checkout_user_login == "test1"
    svc.checkin(db, WS, "P2SVC-1", "A", "test1")
    svc.delete_revision(db, WS, "P2SVC-1", "A", "test1")


def test_duplicate_raises(db):
    _make(db, "P2SVC-DUP")
    try:
        _make(db, "P2SVC-DUP")
        assert False
    except EntityAlreadyExistsException as e:
        assert e.key == "DocumentMasterAlreadyExistsException"
    svc.checkin(db, WS, "P2SVC-DUP", "A", "test1")
    svc.delete_revision(db, WS, "P2SVC-DUP", "A", "test1")

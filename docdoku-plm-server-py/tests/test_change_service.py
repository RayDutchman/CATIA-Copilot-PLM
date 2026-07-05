from app.services.change_service import ChangeService
from app.models.change import ChangeIssue, Milestone
WS = "Workspace_2"
svc = ChangeService()


def test_issue_crud(db):
    it = svc.create_item(db, WS, "issue",
                         body={"name": "Test Issue", "description": "desc",
                               "priority": 1, "initiator": "test1"},
                         user_login="test1")
    assert it.name == "Test Issue"
    found = svc.get_by_id(db, ChangeIssue, WS, it.id)
    assert found.name == "Test Issue"
    svc.delete_item(db, ChangeIssue, WS, it.id)


def test_milestone_crud(db):
    ms = svc.create_item(db, WS, "milestone",
                         body={"title": "M1", "description": "desc",
                               "dueDate": "2026-12-31"},
                         user_login="test1")
    assert ms.title == "M1"
    svc.delete_item(db, Milestone, WS, ms.id)

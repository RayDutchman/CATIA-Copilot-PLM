from app.models.change import ChangeIssue, ChangeRequest, ChangeOrder, Milestone


def test_tables_exist():
    assert ChangeIssue.__tablename__ == "changeissue"
    assert ChangeRequest.__tablename__ == "changerequest"
    assert ChangeOrder.__tablename__ == "changeorder"
    assert Milestone.__tablename__ == "milestone"

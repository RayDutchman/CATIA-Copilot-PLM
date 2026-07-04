from app.core.database import SessionLocal
from app.models.document import DocumentMaster, DocumentRevision, Folder


def test_folder_rows_exist():
    db = SessionLocal()
    count = db.query(Folder).count()
    assert count >= 4
    db.close()


def test_tables_exist():
    db = SessionLocal()
    assert DocumentMaster.__tablename__ == "documentmaster"
    assert DocumentRevision.__tablename__ == "documentrevision"
    db.close()

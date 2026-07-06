"""Document ORM 模型 — Folder 保留在此，实体已拆分到 models.document.*。"""
from sqlalchemy import Column, String, ForeignKey
from app.core.database import Base


class Folder(Base):
    __tablename__ = "folder"
    completepath = Column("completepath", String, primary_key=True)
    parentfolder_completepath = Column("parentfolder_completepath", String,
                                        ForeignKey("folder.completepath"))


# 向后兼容重新导出
from app.models.document.document_master import DocumentMaster  # noqa: E402, F401
from app.models.document.document_revision import DocumentRevision, document_revision_tags  # noqa: E402, F401
from app.models.document.document_iteration import DocumentIteration, document_iteration_binres  # noqa: E402, F401
from app.models.document.document_master_template import DocumentMasterTemplate  # noqa: E402, F401
from app.models.document.document_link import DocumentLink  # noqa: E402, F401

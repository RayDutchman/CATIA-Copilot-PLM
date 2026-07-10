"""PathToPathLink ORM 模型，映射 pathtopathlink 表。

实际列：id, description, sourcepath, targetpath, type
无 name/workspace_id 列（避免旧代码误引发 ColumnError）。
"""
from sqlalchemy import Column, String, Integer, Text
from app.core.database import Base


class PathToPathLink(Base):
    __tablename__ = "pathtopathlink"

    id = Column(Integer, primary_key=True, autoincrement=True)
    # 链接类型（如 "wire"/"pipe" 等，用户自定义）
    type = Column(String(255))
    # 源路径字符串，如 "-1-u2-u5"
    source_path = Column("sourcepath", String(255))
    # 目标路径字符串
    target_path = Column("targetpath", String(255))
    # 链接描述
    description = Column(Text)

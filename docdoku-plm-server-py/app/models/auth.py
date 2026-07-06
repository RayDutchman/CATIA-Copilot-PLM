"""认证相关 ORM 模型，映射现有 docdokuplm 数据库表。不修改表结构。

UserGroupMapping 已移至 models.security.user_group_mapping。"""
from sqlalchemy import Column, String, Boolean
from app.core.database import Base

class Account(Base):
    """对应 account 表。"""
    __tablename__ = "account"

    login = Column(String, primary_key=True)
    email = Column(String)
    name = Column(String)
    language = Column(String)
    timezone = Column(String)
    enabled = Column(Boolean, default=True)


# 向后兼容：从新位置重新导出
from app.models.security.user_group_mapping import UserGroupMapping  # noqa: E402, F401

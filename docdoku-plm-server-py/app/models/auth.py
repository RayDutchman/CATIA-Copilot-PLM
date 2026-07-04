"""认证相关 ORM 模型，映射现有 docdokuplm 数据库表。不修改表结构。"""
from sqlalchemy import Column, String, Boolean
from app.core.database import Base

class Account(Base):
    """对应 account 表。"""
    __tablename__ = "account"

    login = Column(String, primary_key=True)
    email = Column(String, nullable=False)
    name = Column(String)
    language = Column(String)
    timezone = Column(String)
    admin = Column(Boolean, default=False)
    enabled = Column(Boolean, default=True)


class Credential(Base):
    """对应 credential 表。密码为 MD5 哈希。"""
    __tablename__ = "credential"

    login = Column(String, primary_key=True)
    password = Column(String, nullable=False)

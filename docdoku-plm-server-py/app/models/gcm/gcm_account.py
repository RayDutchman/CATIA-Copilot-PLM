"""GCMAccount ORM 模型 — Google Cloud Messaging 账户。"""
from sqlalchemy import Column, String, ForeignKey
from app.core.database import Base

class GCMAccount(Base):
    __tablename__ = "gcmaccount"
    account_login = Column(String, ForeignKey("account.login"), primary_key=True)
    gcm_id = Column("gcmid", String)

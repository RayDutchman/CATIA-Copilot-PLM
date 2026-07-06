"""PasswordRecoveryRequest ORM 模型。"""
from sqlalchemy import Column, String, ForeignKey
from app.core.database import Base

class PasswordRecoveryRequest(Base):
    __tablename__ = "passwordrecoveryrequest"
    uuid = Column(String, primary_key=True)
    login = Column(String, ForeignKey("account.login"))

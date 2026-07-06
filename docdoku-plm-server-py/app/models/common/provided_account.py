"""ProvidedAccount ORM 模型，映射 providedaccount 表。"""
from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class ProvidedAccount(Base):
    __tablename__ = "providedaccount"

    provider_id = Column("id", Integer, ForeignKey("oauthprovider.id"), primary_key=True)
    sub = Column(String, primary_key=True)
    account_login = Column("login", String, ForeignKey("account.login"), primary_key=True)

    provider = relationship("OAuthProvider", foreign_keys=[provider_id])
    account = relationship("Account", foreign_keys=[account_login])

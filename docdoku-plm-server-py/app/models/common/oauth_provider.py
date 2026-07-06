"""OAuthProvider ORM 模型，映射 oauthprovider 表。"""
from sqlalchemy import Column, String, Integer, Boolean
from app.core.database import Base


class OAuthProvider(Base):
    __tablename__ = "oauthprovider"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String)
    enabled = Column(Boolean, default=True)
    authority = Column(String)
    issuer = Column(String)
    clientid = Column(String)
    jwsalgorithm = Column(String)
    jwkseturl = Column(String)
    redirecturi = Column(String)
    secret = Column(String)
    scope = Column(String)
    responsetype = Column(String)
    authorizationendpoint = Column(String)

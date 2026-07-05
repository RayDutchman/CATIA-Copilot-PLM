from sqlalchemy import Column, String, ForeignKey
from app.core.database import Base


class UserGroup(Base):
    __tablename__ = "usergroup"
    id = Column(String, primary_key=True)
    workspace_id = Column(String, primary_key=True)


class Credential(Base):
    __tablename__ = "credential"
    login = Column(String, ForeignKey("account.login"), primary_key=True)
    password = Column(String)

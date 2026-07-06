"""Organization ORM 模型，映射 organization 表。"""
from sqlalchemy import Column, String, Text, Table, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


organization_account = Table(
    "organization_account", Base.metadata,
    Column("organization_name", String, ForeignKey("organization.name"), primary_key=True),
    Column("account_login", String, ForeignKey("account.login"), primary_key=True),
    Column("account_order", String),
)


class Organization(Base):
    __tablename__ = "organization"

    name = Column(String(100), primary_key=True)
    owner_login = Column(String, ForeignKey("account.login"), nullable=False)
    description = Column(Text, nullable=True)

    owner = relationship("Account", foreign_keys=[owner_login])
    members = relationship(
        "Account",
        secondary=organization_account,
        order_by="organization_account.c.account_order",
    )

"""ChangeItem 抽象基类 — 对应 Java @MappedSuperclass。共享字段被各子类直接定义。"""
from app.core.database import Base


class ChangeItem(Base):
    """抽象基类，不映射到独立表。子类各自定义完整字段。"""
    __abstract__ = True

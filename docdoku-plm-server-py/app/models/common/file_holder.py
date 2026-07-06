"""FileHolder 抽象基类 — 对应 Java FileHolder 接口。"""
from abc import ABC, abstractmethod
from typing import Set


class FileHolder(ABC):
    """拥有附件的实体的标记接口。"""

    @abstractmethod
    def get_attached_files(self) -> Set["BinaryResource"]:
        ...

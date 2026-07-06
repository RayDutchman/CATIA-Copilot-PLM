"""PartLinkList DTO — 对应 Java PartLinkList 便利类。"""
from typing import List, Optional


class PartLinkList:
    """部件链接列表 DTO。"""

    def __init__(self, links: Optional[List["PartLink"]] = None):
        self.links = links or []

"""TaskWrapper DTO — 对应 Java TaskWrapper 便利类。"""
from typing import Optional


class TaskWrapper:
    def __init__(self, task=None, full_name: str = "", workspace_id: str = ""):
        self.task = task
        self.full_name = full_name
        self.workspace_id = workspace_id

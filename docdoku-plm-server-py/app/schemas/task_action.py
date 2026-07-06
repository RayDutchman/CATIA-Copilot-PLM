"""DTO: TaskAction enum."""
from enum import StrEnum


class TaskAction(StrEnum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"

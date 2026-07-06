"""DTO: TaskStatus enum."""
from enum import StrEnum


class TaskStatus(StrEnum):
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    NOT_TO_BE_DONE = "NOT_TO_BE_DONE"

"""DTO: ActivityType enum."""
from enum import StrEnum


class ActivityType(StrEnum):
    SEQUENTIAL = "SEQUENTIAL"
    PARALLEL = "PARALLEL"

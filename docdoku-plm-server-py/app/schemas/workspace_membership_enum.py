"""DTO: WorkspaceMembership enum."""
from enum import StrEnum


class WorkspaceMembership(StrEnum):
    READ_ONLY = "READ_ONLY"
    FULL_ACCESS = "FULL_ACCESS"

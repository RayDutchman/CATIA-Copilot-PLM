"""DTO: InstanceAttributeType enum."""
from enum import StrEnum


class InstanceAttributeType(StrEnum):
    TEXT = "TEXT"
    NUMBER = "NUMBER"
    DATE = "DATE"
    BOOLEAN = "BOOLEAN"
    URL = "URL"
    LOV = "LOV"
    LONG_TEXT = "LONG_TEXT"
    PART_NUMBER = "PART_NUMBER"

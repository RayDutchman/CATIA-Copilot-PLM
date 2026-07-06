"""PlatformOptions DTO。"""
from dataclasses import dataclass
from app.models.admin.operation_security_strategy import OperationSecurityStrategy

@dataclass
class PlatformOptions:
    registration_strategy: int = 0
    workspace_creation_strategy: int = 0
    operation_security_strategy: OperationSecurityStrategy = None

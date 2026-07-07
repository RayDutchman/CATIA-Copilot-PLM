"""上下文管理——对标 Payara ContextManagerBean。

提供当前请求上下文中的用户身份信息。
"""
from fastapi import Request


class ContextService:
    """从请求上下文中提取用户身份。"""

    def get_caller_login(self, request: Request) -> str:
        """获取当前调用者登录名。"""
        from app.core.deps import get_current_user_from_request
        user = get_current_user_from_request(request)
        return user.login if user else ""

    def get_caller_name(self, request: Request) -> str:
        """获取当前调用者名称。"""
        from app.core.deps import get_current_user_from_request
        user = get_current_user_from_request(request)
        return user.name if user else ""

    def is_caller_in_role(self, request: Request, role: str) -> bool:
        """检查当前用户是否在指定角色中。"""
        # FastAPI 依赖注入中已有角色检查逻辑
        from app.core.deps import get_current_user_roles
        roles = get_current_user_roles(request)
        return role in roles


context_service = ContextService()

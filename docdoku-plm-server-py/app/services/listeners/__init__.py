"""Listeners 包。CDI 事件监听器的 Python 等价实现。

Java 中这些类通过 @Observes 注解响应 CDI 事件。
Python 侧以显式方法调用的方式提供等价功能。
"""
from app.services.listeners.user_folder_manager import UserFolderManager
from app.services.listeners.part_notification_manager import PartNotificationManager
from app.services.listeners.subscription_manager import SubscriptionManager
from app.services.listeners.role_manager import RoleManager

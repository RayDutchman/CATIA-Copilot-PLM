"""活动检查拦截器——对标 Payara ActivityCheckerInterceptor。"""
from sqlalchemy.orm import Session


def check_activity(db: Session, ws: str, user_login: str,
                   workflow_id: int, activity_step: int, task_num: int) -> None:
    """验证用户是 task 的 potential worker。"""
    from app.services.task_manager import task_service
    if not task_service._is_potential_worker(db, ws, user_login,
                                              workflow_id, activity_step, task_num):
        from app.core.exceptions import NotAllowedException
        raise NotAllowedException("NotAllowedException41")


activity_checker = type('ActivityChecker', (), {'check': staticmethod(check_activity)})()

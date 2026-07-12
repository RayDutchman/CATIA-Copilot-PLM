"""变更模块共享工具函数—— _item_to_dict, _get_acl_dict, _get_user_name 等。
所有 DB 操作已迁入 services/change_manager.py。"""
from typing import Optional, Sequence
from sqlalchemy import text as sql_text
from sqlalchemy.orm import Session
from app.core.exceptions import AccessRightException
from app.services.change_manager import ChangeService

_svc = ChangeService()


def _get_user_name(db, login: str) -> str:
    return _svc.get_user_name(db, login)


def _check_workspace_access(db: Session, ws: str, login: str):
    row = db.execute(sql_text(
        "SELECT 1 FROM userdata WHERE login = :l AND workspace_id = :w"
    ), {"l": login, "w": ws}).first()
    if not row:
        raise AccessRightException("AccessRightException", login)


def _item_to_dict(item, db: Optional[Session] = None, current_user=None) -> dict:
    return _svc.build_item_dto(item, db, current_user)


def _set_affected_parts(db: Session, ws: str, item_id: int,
                        parts_data: Sequence[dict], table_name: str, id_column: str,
                        user_login: str | None = None, is_admin: bool = False):
    _svc.set_affected_parts(db, ws, item_id, parts_data, table_name, id_column,
                            user_login=user_login, is_admin=is_admin)


def _set_affected_documents(db: Session, ws: str, item_id: int,
                            docs_data: Sequence[dict], table_name: str, id_column: str,
                            user_login: str | None = None, is_admin: bool = False):
    _svc.set_affected_documents(db, ws, item_id, docs_data, table_name, id_column,
                                user_login=user_login, is_admin=is_admin)

"""FastAPI 依赖项：数据库会话、当前用户认证。"""
import re
from typing import Annotated
from fastapi import Depends, HTTPException, status, Response, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import get_db
from app.core.security import verify_token, create_token, should_refresh_token
from app.models.auth import Account
from app.core.exceptions import WorkspaceNotEnabledException, EntityNotFoundException

bearer_scheme = HTTPBearer(auto_error=False)

_WS_RE = re.compile(r"^/docdoku-plm-server-rest/api/workspaces/([^/]+)")


def get_current_user(
    request: Request,
    response: Response,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)] = None,
    db: Session = Depends(get_db),
) -> Account:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未提供认证 token")
    try:
        payload = verify_token(credentials.credentials)
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="token 无效或已过期")
    if should_refresh_token(payload["exp"]):
        new_token = create_token(payload["login"], payload["groupName"])
        response.headers["jwt"] = new_token
    account = db.query(Account).filter(Account.login == payload["login"]).first()
    if account is None or not account.enabled:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="账号不存在或已禁用")
    # 对齐 Payara checkWorkspaceReadAccess / checkWorkspaceWriteAccess
    m = _WS_RE.match(request.url.path)
    if m:
        ws = m.group(1)
        row = db.execute(text("SELECT enabled FROM workspace WHERE id = :w"), {"w": ws}).first()
        if row and not bool(row[0]):
            raise WorkspaceNotEnabledException("WorkspaceNotEnabledException", ws)
        member = db.execute(text(
            "SELECT 1 FROM userdata WHERE login=:l AND workspace_id=:w"
        ), {"l": account.login, "w": ws}).first()
        if not member:
            raise EntityNotFoundException("UserNotFoundException", account.login)
    return account

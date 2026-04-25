from __future__ import annotations

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select

from server.auth.security import decode_token
from server.db import get_session
from server.models import User


bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    session=Depends(get_session),
) -> User:
    if creds is None:
        raise HTTPException(status_code=401, detail="未登录")
    try:
        payload = decode_token(creds.credentials)
        email = payload.get("sub")
        if not email:
            raise ValueError("missing sub")
    except Exception:
        raise HTTPException(status_code=401, detail="Token 无效或过期")

    res = await session.exec(select(User).where(User.email == email))
    user = res.first()
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")
    return user


async def require_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return user


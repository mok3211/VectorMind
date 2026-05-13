from __future__ import annotations

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlmodel.ext.asyncio.session import AsyncSession

from server.auth.security import decode_token
from server.auth.rbac import get_user_permission_codes, get_user_role_codes, has_permissions
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

    result = await session.execute(select(User).where(User.email == email))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")
    return user


async def require_admin(user: User = Depends(get_current_user)) -> User:
    # 兼容旧字段：管理员直接放行
    if user.is_admin:
        return user
    # 新 RBAC：由前端/后端改用 require_role('admin') 或 require_permission(...)
    raise HTTPException(status_code=403, detail="需要管理员权限")
    return user


def require_permission(code: str):
    async def _dep(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)) -> User:
        if user.is_admin:
            return user
        if not user.id:
            raise HTTPException(status_code=403, detail="用户无效")
        perms = await get_user_permission_codes(session, user.id)
        if not has_permissions(user.is_admin, perms, code):
            raise HTTPException(status_code=403, detail=f"缺少权限：{code}")
        return user

    return _dep


def require_role(role_code: str):
    async def _dep(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)) -> User:
        if user.is_admin and role_code == "admin":
            return user
        if not user.id:
            raise HTTPException(status_code=403, detail="用户无效")
        roles = await get_user_role_codes(session, user.id)
        if role_code not in roles:
            raise HTTPException(status_code=403, detail=f"需要角色：{role_code}")
        return user

    return _dep

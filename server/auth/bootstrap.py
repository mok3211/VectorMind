from __future__ import annotations

from sqlalchemy import select

from server.config import settings
from server.db import AsyncSessionLocal
from server.models import User
from server.auth.security import hash_password


async def ensure_builtin_admin() -> None:
    """
    启动时自动初始化一个内置管理员账号。
    账号与密码由环境变量控制，默认：
    - 账号：zhangchi
    - 密码：zhangchi2026
    """

    if not getattr(settings, "bootstrap_admin_enabled", True):
        return

    identifier = (getattr(settings, "bootstrap_admin_identifier", "") or "").strip()
    password = getattr(settings, "bootstrap_admin_password", "") or ""
    if not identifier or not password:
        return

    async with AsyncSessionLocal() as session:
        try:
            result = await session.execute(select(User).where(User.email == identifier).limit(1))
            user = result.scalars().first()
            if user:
                # 已存在：可选重置密码（开发用）
                if getattr(settings, "bootstrap_admin_force_reset", False):
                    user.hashed_password = hash_password(password)
                    user.is_admin = True
                    session.add(user)
                    await session.commit()
                return

            # 不存在则创建
            user = User(email=identifier, hashed_password=hash_password(password), is_admin=True)
            session.add(user)
            await session.commit()
        except Exception:
            # 数据库未迁移/表不存在等情况，不阻塞服务启动
            await session.rollback()
            return

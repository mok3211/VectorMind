from __future__ import annotations

from sqlalchemy import select
from sqlmodel import select as sql_select

from server.config import settings
from server import db
from server.models import MenuModule, User
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

    async with db.AsyncSessionLocal() as session:
        try:
            result = await session.execute(select(User).where(User.email == identifier).limit(1))
            user = result.scalars().first()
            if user:
                changed = False
                if getattr(settings, "bootstrap_admin_force_reset", False):
                    user.hashed_password = hash_password(password)
                    changed = True
                if not user.is_admin:
                    user.is_admin = True
                    changed = True
                if changed:
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


async def ensure_builtin_menus() -> None:
    async with db.AsyncSessionLocal() as session:
        try:
            existing = await session.exec(sql_select(MenuModule.key))
            existing_keys = {x for x in existing.all()}
            items = [
                ("dashboard", "概览", "/", "◎", None, 10),
                ("agents", "智能体", "/agents", "⚡", None, 20),
                ("workflows", "工作流", "/workflows", "⟂", None, 30),
                ("prompts", "提示词", "/prompts", "✎", None, 40),
                ("llm", "模型与Key", "/llm", "⌬", None, 45),
                ("runs", "运行记录", "/runs", "⏱", None, 50),
                ("media", "媒体账号", "/media", "✦", None, 60),
                ("marketing", "运营中心", "/marketing", "◈", None, 70),
                ("rbac", "权限管理", "/rbac", "⚙", None, 80),
            ]
            for key, label, path, icon, perm, order in items:
                if key in existing_keys:
                    continue
                session.add(
                    MenuModule(
                        key=key,
                        label=label,
                        path=path,
                        icon=icon,
                        permission_code=perm,
                        sort_order=order,
                        enabled=True,
                    )
                )
            await session.commit()
        except Exception:
            await session.rollback()
            return

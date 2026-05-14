from __future__ import annotations

from datetime import datetime
from typing import Iterable

from sqlalchemy import select
from sqlmodel.ext.asyncio.session import AsyncSession

from server.models import (
    MenuModule,
    Permission,
    Role,
    RolePermission,
    SubscriptionPlan,
    User,
    UserRole,
)


DEFAULT_PERMISSIONS: list[tuple[str, str, str]] = [
    # code, name, group
    ("system.users.manage", "用户管理", "system"),
    ("system.roles.manage", "角色管理", "system"),
    ("system.permissions.manage", "权限管理", "system"),
    ("system.menus.manage", "菜单管理", "system"),
    ("billing.plans.manage", "套餐管理", "billing"),
    ("billing.subscriptions.manage", "订阅管理", "billing"),
    ("executors.manage", "执行器管理", "system"),
    ("marketing.view", "Marketing 查看", "marketing"),
    ("marketing.manage", "Marketing 管理", "marketing"),
    ("media.view", "媒体账号查看", "media"),
    ("media.manage", "媒体账号管理", "media"),
    ("runs.view", "运行记录查看", "runs"),
    ("agents.view", "Agent 查看", "agents"),
    ("agents.run", "Agent 运行", "agents"),
    ("workflows.view", "工作流查看", "workflows"),
    ("workflows.manage", "工作流管理", "workflows"),
    ("prompts.view", "Prompts 查看", "prompts"),
    ("prompts.manage", "Prompts 管理", "prompts"),
]


DEFAULT_ROLES: list[tuple[str, str]] = [
    ("admin", "管理员"),
    ("operator", "操作员"),
    ("user", "普通用户"),
]


DEFAULT_ROLE_PERMISSIONS: dict[str, list[str]] = {
    # 管理员：在代码里直接 bypass（也给一组完整权限，便于前端展示）
    "admin": [p[0] for p in DEFAULT_PERMISSIONS],
    "operator": [
        "marketing.view",
        "marketing.manage",
        "media.view",
        "media.manage",
        "runs.view",
        "agents.view",
        "agents.run",
        "workflows.view",
        "prompts.view",
    ],
    "user": [
        "marketing.view",
        "media.view",
        "runs.view",
        "agents.view",
        "agents.run",
        "workflows.view",
        "prompts.view",
    ],
}


DEFAULT_MENU_MODULES: list[tuple[str, str, str, str | None, int]] = [
    # key, label, path, permission_code, sort
    ("dashboard", "概览", "/", None, 10),
    ("agents", "Agent 运行", "/agents", "agents.view", 20),
    ("workflows", "工作流", "/workflows", "workflows.view", 30),
    ("prompts", "Prompts", "/prompts", "prompts.view", 40),
    ("marketing", "Marketing", "/marketing", "marketing.view", 50),
    ("runs", "生成记录", "/runs", "runs.view", 60),
    ("media", "媒体账号", "/media", "media.view", 70),
    ("rbac", "用户与权限", "/rbac", "system.users.manage", 90),
]


DEFAULT_PLANS: list[tuple[str, str]] = [
    ("free", "Free"),
    ("pro", "Pro"),
    ("vip", "VIP"),
]


async def ensure_rbac_defaults(session: AsyncSession) -> None:
    now = datetime.utcnow()

    # permissions
    for code, name, group in DEFAULT_PERMISSIONS:
        res = await session.execute(select(Permission).where(Permission.code == code).limit(1))
        if res.scalars().first():
            continue
        session.add(Permission(code=code, name=name, group=group, created_at=now))

    # roles
    for code, name in DEFAULT_ROLES:
        res = await session.execute(select(Role).where(Role.code == code).limit(1))
        if res.scalars().first():
            continue
        session.add(Role(code=code, name=name, created_at=now))

    await session.commit()

    # role_permissions
    # 先拿到 role_id / permission_id 映射
    role_rows = (await session.execute(select(Role))).scalars().all()
    perm_rows = (await session.execute(select(Permission))).scalars().all()
    role_id = {r.code: r.id for r in role_rows if r.id is not None}
    perm_id = {p.code: p.id for p in perm_rows if p.id is not None}

    for rcode, p_codes in DEFAULT_ROLE_PERMISSIONS.items():
        rid = role_id.get(rcode)
        if not rid:
            continue
        for pcode in p_codes:
            pid = perm_id.get(pcode)
            if not pid:
                continue
            res = await session.execute(
                select(RolePermission).where(
                    (RolePermission.role_id == rid) & (RolePermission.permission_id == pid)
                )
            )
            if res.scalars().first():
                continue
            session.add(RolePermission(role_id=rid, permission_id=pid, created_at=now))

    # menu modules
    for key, label, path, permission_code, sort in DEFAULT_MENU_MODULES:
        res = await session.execute(select(MenuModule).where(MenuModule.key == key).limit(1))
        if res.scalars().first():
            continue
        session.add(
            MenuModule(
                key=key,
                label=label,
                path=path,
                permission_code=permission_code,
                sort_order=sort,
                enabled=True,
                created_at=now,
            )
        )

    # plans
    for code, name in DEFAULT_PLANS:
        res = await session.execute(select(SubscriptionPlan).where(SubscriptionPlan.code == code).limit(1))
        if res.scalars().first():
            continue
        session.add(SubscriptionPlan(code=code, name=name, currency="CNY", price_month=0, price_quarter=0, price_year=0, active=True, created_at=now))

    await session.commit()


async def ensure_user_has_role(session: AsyncSession, *, user: User, role_code: str) -> None:
    res = await session.execute(select(Role).where(Role.code == role_code).limit(1))
    role = res.scalars().first()
    if not role or role.id is None or user.id is None:
        return
    res = await session.execute(
        select(UserRole).where((UserRole.user_id == user.id) & (UserRole.role_id == role.id))
    )
    if res.scalars().first():
        return
    session.add(UserRole(user_id=user.id, role_id=role.id, created_at=datetime.utcnow()))
    await session.commit()


async def get_user_role_codes(session: AsyncSession, user_id: int) -> list[str]:
    rows = await session.execute(
        select(Role.code)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == user_id)
    )
    return [r[0] for r in rows.all()]


async def get_user_permission_codes(session: AsyncSession, user_id: int) -> set[str]:
    rows = await session.execute(
        select(Permission.code)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(Role, Role.id == RolePermission.role_id)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == user_id)
    )
    return {r[0] for r in rows.all()}


def has_permissions(user_is_admin: bool, user_permissions: Iterable[str], required: str | list[str]) -> bool:
    if user_is_admin:
        return True
    perms = set(user_permissions)
    if isinstance(required, str):
        return required in perms
    return all(r in perms for r in required)

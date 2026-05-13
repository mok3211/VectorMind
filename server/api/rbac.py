from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import delete
from sqlmodel import select

from server.auth.deps import require_permission
from server.auth.deps import get_current_user
from server.auth.security import hash_password
from server.auth.rbac import get_user_permission_codes, has_permissions
from server.db import get_session
from server.models import (
    MenuModule,
    Permission,
    Role,
    RolePermission,
    SubscriptionPlan,
    User,
    UserRole,
    UserSubscription,
)


router = APIRouter(prefix="/api/rbac", tags=["rbac"])

@router.get("/my-menus")
async def my_menus(user: User = Depends(get_current_user), session=Depends(get_session)):
    perms: set[str] = set()
    if user.id and not user.is_admin:
        try:
            perms = await get_user_permission_codes(session, user.id)
        except Exception:
            perms = set()
    res = await session.exec(select(MenuModule).where(MenuModule.enabled == True).order_by(MenuModule.sort_order))  # noqa: E712
    items = []
    for m in res.all():
        if not m.permission_code or has_permissions(user.is_admin, perms, m.permission_code):
            items.append(m.model_dump())
    return {"items": items}


# -------- permissions --------
@router.get("/permissions")
async def list_permissions(_: object = Depends(require_permission("system.permissions.manage")), session=Depends(get_session)):
    res = await session.exec(select(Permission).order_by(Permission.group, Permission.code))
    return {"items": [p.model_dump() for p in res.all()]}


class PermissionUpsert(BaseModel):
    code: str
    name: str
    group: str | None = None
    description: str | None = None


@router.post("/permissions")
async def upsert_permission(req: PermissionUpsert, _: object = Depends(require_permission("system.permissions.manage")), session=Depends(get_session)):
    code = req.code.strip()
    if not code:
        raise HTTPException(status_code=400, detail="code 不能为空")
    res = await session.exec(select(Permission).where(Permission.code == code))
    item = res.first()
    if item:
        item.name = req.name
        item.group = req.group
        item.description = req.description
        session.add(item)
        await session.commit()
        return {"item": item.model_dump()}
    item = Permission(code=code, name=req.name, group=req.group, description=req.description, created_at=datetime.utcnow())
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return {"item": item.model_dump()}


# -------- roles --------
@router.get("/roles")
async def list_roles(_: object = Depends(require_permission("system.roles.manage")), session=Depends(get_session)):
    res = await session.exec(select(Role).order_by(Role.code))
    roles = res.all()
    out = []
    for r in roles:
        pr = await session.exec(
            select(Permission.code)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .where(RolePermission.role_id == r.id)
        )
        out.append({**r.model_dump(), "permissions": [x[0] for x in pr.all()]})
    return {"items": out}


class RoleCreate(BaseModel):
    code: str
    name: str
    description: str | None = None
    permissions: list[str] = []


@router.post("/roles")
async def create_role(req: RoleCreate, _: object = Depends(require_permission("system.roles.manage")), session=Depends(get_session)):
    code = req.code.strip()
    if not code:
        raise HTTPException(status_code=400, detail="code 不能为空")
    exists = await session.exec(select(Role).where(Role.code == code))
    if exists.first():
        raise HTTPException(status_code=400, detail="role code 已存在")
    role = Role(code=code, name=req.name, description=req.description, created_at=datetime.utcnow())
    session.add(role)
    await session.commit()
    await session.refresh(role)
    await _set_role_permissions(session, role.id, req.permissions)
    return {"item": role.model_dump()}


class RoleUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    permissions: list[str] | None = None


@router.put("/roles/{role_id}")
async def update_role(role_id: int, req: RoleUpdate, _: object = Depends(require_permission("system.roles.manage")), session=Depends(get_session)):
    role = await session.get(Role, role_id)
    if not role:
        raise HTTPException(status_code=404, detail="not found")
    if req.name is not None:
        role.name = req.name
    if req.description is not None:
        role.description = req.description
    session.add(role)
    await session.commit()
    if req.permissions is not None:
        await _set_role_permissions(session, role_id, req.permissions)
    return {"item": role.model_dump()}


async def _set_role_permissions(session, role_id: int, permission_codes: list[str]) -> None:
    await session.execute(delete(RolePermission).where(RolePermission.role_id == role_id))
    # 逐条插入
    for code in permission_codes:
        res = await session.exec(select(Permission).where(Permission.code == code))
        p = res.first()
        if not p or p.id is None:
            continue
        session.add(RolePermission(role_id=role_id, permission_id=p.id, created_at=datetime.utcnow()))
    await session.commit()


# -------- users --------
@router.get("/users")
async def list_users(_: object = Depends(require_permission("system.users.manage")), session=Depends(get_session)):
    res = await session.exec(select(User).order_by(User.id.desc()))
    users = res.all()
    out = []
    for u in users:
        rr = await session.exec(
            select(Role.code).join(UserRole, UserRole.role_id == Role.id).where(UserRole.user_id == u.id)
        )
        out.append({**u.model_dump(), "roles": [x[0] for x in rr.all()]})
    return {"items": out}


class UserCreate(BaseModel):
    email: str
    password: str
    roles: list[str] = []
    is_admin: bool = False


@router.post("/users")
async def create_user(req: UserCreate, _: object = Depends(require_permission("system.users.manage")), session=Depends(get_session)):
    email = req.email.strip()
    if not email:
        raise HTTPException(status_code=400, detail="email 不能为空")
    exists = await session.exec(select(User).where(User.email == email))
    if exists.first():
        raise HTTPException(status_code=400, detail="用户已存在")
    u = User(email=email, hashed_password=hash_password(req.password), is_admin=bool(req.is_admin), created_at=datetime.utcnow())
    session.add(u)
    await session.commit()
    await session.refresh(u)
    await _set_user_roles(session, u.id, req.roles)
    return {"item": u.model_dump()}


class UserUpdate(BaseModel):
    password: str | None = None
    roles: list[str] | None = None
    is_admin: bool | None = None


@router.put("/users/{user_id}")
async def update_user(user_id: int, req: UserUpdate, _: object = Depends(require_permission("system.users.manage")), session=Depends(get_session)):
    u = await session.get(User, user_id)
    if not u:
        raise HTTPException(status_code=404, detail="not found")
    if req.password is not None and req.password.strip():
        u.hashed_password = hash_password(req.password)
    if req.is_admin is not None:
        u.is_admin = bool(req.is_admin)
    session.add(u)
    await session.commit()
    if req.roles is not None:
        await _set_user_roles(session, user_id, req.roles)
    return {"item": u.model_dump()}


async def _set_user_roles(session, user_id: int, role_codes: list[str]) -> None:
    await session.execute(delete(UserRole).where(UserRole.user_id == user_id))
    for code in role_codes:
        res = await session.exec(select(Role).where(Role.code == code))
        r = res.first()
        if not r or r.id is None:
            continue
        session.add(UserRole(user_id=user_id, role_id=r.id, created_at=datetime.utcnow()))
    await session.commit()


# -------- menu modules --------
@router.get("/menu-modules")
async def list_menu_modules(_: object = Depends(require_permission("system.menus.manage")), session=Depends(get_session)):
    res = await session.exec(select(MenuModule).order_by(MenuModule.sort_order))
    return {"items": [m.model_dump() for m in res.all()]}


class MenuUpsert(BaseModel):
    key: str
    label: str
    path: str
    icon: str | None = None
    permission_code: str | None = None
    sort_order: int = 100
    enabled: bool = True


@router.post("/menu-modules")
async def upsert_menu(req: MenuUpsert, _: object = Depends(require_permission("system.menus.manage")), session=Depends(get_session)):
    key = req.key.strip()
    if not key:
        raise HTTPException(status_code=400, detail="key 不能为空")
    res = await session.exec(select(MenuModule).where(MenuModule.key == key))
    item = res.first()
    if item:
        for k, v in req.model_dump().items():
            setattr(item, k, v)
        session.add(item)
        await session.commit()
        return {"item": item.model_dump()}
    item = MenuModule(**req.model_dump(), created_at=datetime.utcnow())
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return {"item": item.model_dump()}


# -------- plans/subscriptions (no payment integration) --------
@router.get("/plans")
async def list_plans(_: object = Depends(require_permission("billing.plans.manage")), session=Depends(get_session)):
    res = await session.exec(select(SubscriptionPlan).order_by(SubscriptionPlan.code))
    return {"items": [p.model_dump() for p in res.all()]}


class PlanUpsert(BaseModel):
    code: str
    name: str
    description: str | None = None
    currency: str = "CNY"
    price_month: float = 0
    price_quarter: float = 0
    price_year: float = 0
    active: bool = True


@router.post("/plans")
async def upsert_plan(req: PlanUpsert, _: object = Depends(require_permission("billing.plans.manage")), session=Depends(get_session)):
    code = req.code.strip()
    res = await session.exec(select(SubscriptionPlan).where(SubscriptionPlan.code == code))
    item = res.first()
    if item:
        for k, v in req.model_dump().items():
            setattr(item, k, v)
        session.add(item)
        await session.commit()
        return {"item": item.model_dump()}
    item = SubscriptionPlan(**req.model_dump(), created_at=datetime.utcnow())
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return {"item": item.model_dump()}


class GrantSub(BaseModel):
    user_id: int
    plan_code: str
    days: int = 30


@router.post("/grant-subscription")
async def grant_subscription(req: GrantSub, _: object = Depends(require_permission("billing.subscriptions.manage")), session=Depends(get_session)):
    plan_res = await session.exec(select(SubscriptionPlan).where(SubscriptionPlan.code == req.plan_code))
    plan = plan_res.first()
    if not plan or plan.id is None:
        raise HTTPException(status_code=400, detail="plan not found")
    user = await session.get(User, req.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="user not found")
    start = datetime.utcnow()
    end = start + timedelta(days=max(1, req.days))
    sub = UserSubscription(user_id=req.user_id, plan_id=plan.id, status="active", start_at=start, end_at=end, auto_renew=False, created_at=start)
    session.add(sub)
    await session.commit()
    await session.refresh(sub)
    return {"item": sub.model_dump()}

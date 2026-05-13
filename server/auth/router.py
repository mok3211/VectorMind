from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from server.auth.deps import get_current_user
from server.auth.rbac import get_user_permission_codes, get_user_role_codes
from server.auth.security import create_access_token, hash_password, verify_password
from server.db import get_session
from server.models import SubscriptionPlan, UserSubscription
from server.models import User


router = APIRouter(prefix="/auth", tags=["auth"])


class BootstrapReq(BaseModel):
    # 兼容“邮箱/账号”两种输入，这里不强制 Email 格式
    email: str
    password: str


@router.post("/bootstrap")
async def bootstrap_admin(req: BootstrapReq, session=Depends(get_session)):
    """
    初始化管理员：仅当库里没有任何用户时允许调用。
    """
    res = await session.exec(select(User))
    if res.first():
        raise HTTPException(status_code=400, detail="已初始化过用户，禁止 bootstrap")

    user = User(email=req.email, hashed_password=hash_password(req.password), is_admin=True)
    session.add(user)
    await session.commit()
    return {"ok": True}


class LoginReq(BaseModel):
    # 兼容“邮箱/账号”两种输入，这里不强制 Email 格式
    email: str
    password: str


@router.post("/login")
async def login(req: LoginReq, session=Depends(get_session)):
    # 兼容 SQLAlchemy / SQLModel 在不同版本下 select(User) 返回 Row 的差异：
    # 一律通过 scalars() 拿到 User 实体，避免 BaseRow 没有 hashed_password 的问题。
    result = await session.execute(select(User).where(User.email == req.email))
    user = result.scalars().first()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="账号或密码错误")

    token = create_access_token(subject=user.email)
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me")
async def me(user: User = Depends(get_current_user), session=Depends(get_session)):
    roles: list[str] = []
    perms: list[str] = []
    plan: dict | None = None
    if user.id:
        try:
            roles = await get_user_role_codes(session, user.id)
            perms = sorted(list(await get_user_permission_codes(session, user.id)))
        except Exception:
            roles = []
            perms = []

        # active plan（最新一条 active 且未过期）
        try:
            from sqlalchemy import desc, or_
            from datetime import datetime as _dt

            now = _dt.utcnow()
            res = await session.execute(
                select(UserSubscription, SubscriptionPlan)
                .join(SubscriptionPlan, SubscriptionPlan.id == UserSubscription.plan_id)
                .where(UserSubscription.user_id == user.id)
                .where(UserSubscription.status == "active")
                .where(or_(UserSubscription.end_at.is_(None), UserSubscription.end_at > now))
                .order_by(desc(UserSubscription.start_at))
                .limit(1)
            )
            row = res.first()
            if row:
                sub, pl = row[0], row[1]
                plan = {
                    "code": pl.code,
                    "name": pl.name,
                    "currency": pl.currency,
                    "price_month": float(pl.price_month),
                    "price_quarter": float(pl.price_quarter),
                    "price_year": float(pl.price_year),
                    "end_at": sub.end_at.isoformat() if sub.end_at else None,
                }
        except Exception:
            plan = None

    return {"email": user.email, "is_admin": user.is_admin, "id": user.id, "roles": roles, "permissions": perms, "plan": plan}

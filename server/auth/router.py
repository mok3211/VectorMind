from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy import select

from server.auth.deps import get_current_user
from server.auth.security import create_access_token, hash_password, verify_password
from server.db import get_session
from server.models import User


router = APIRouter(prefix="/auth", tags=["auth"])


class BootstrapReq(BaseModel):
    email: EmailStr
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
    email: EmailStr
    password: str


@router.post("/login")
async def login(req: LoginReq, session=Depends(get_session)):
    res = await session.exec(select(User).where(User.email == req.email))
    user = res.first()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="邮箱或密码错误")

    token = create_access_token(subject=user.email)
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me")
async def me(user: User = Depends(get_current_user)):
    return {"email": user.email, "is_admin": user.is_admin, "id": user.id}


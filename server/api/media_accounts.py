from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel import select

from server.auth.deps import require_permission
from server.db import get_session
from server.models import MediaAccount


router = APIRouter(prefix="/api/media-accounts", tags=["media-accounts"])


class MediaAccountCreate(BaseModel):
    platform: str
    nickname: str | None = None
    notes: str | None = None
    auth_json: str | None = None


@router.get("")
async def list_accounts(_: object = Depends(require_permission("media.view")), session=Depends(get_session)):
    res = await session.exec(select(MediaAccount).order_by(MediaAccount.updated_at.desc()))
    items = res.all()
    return {"items": [i.model_dump() for i in items]}


@router.post("")
async def create_account(
    req: MediaAccountCreate, _: object = Depends(require_permission("media.manage")), session=Depends(get_session)
):
    item = MediaAccount(
        platform=req.platform,
        nickname=req.nickname,
        notes=req.notes,
        auth_json=req.auth_json,
        status="disconnected",
        updated_at=datetime.utcnow(),
    )
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return {"item": item.model_dump()}


class MediaAccountUpdate(BaseModel):
    nickname: str | None = None
    status: str | None = None
    notes: str | None = None
    auth_json: str | None = None


@router.put("/{account_id}")
async def update_account(
    account_id: int, req: MediaAccountUpdate, _: object = Depends(require_permission("media.manage")), session=Depends(get_session)
):
    item = await session.get(MediaAccount, account_id)
    if not item:
        return {"ok": False, "detail": "not found"}

    if req.nickname is not None:
        item.nickname = req.nickname
    if req.status is not None:
        item.status = req.status
    if req.notes is not None:
        item.notes = req.notes
    if req.auth_json is not None:
        item.auth_json = req.auth_json
    item.updated_at = datetime.utcnow()

    session.add(item)
    await session.commit()
    await session.refresh(item)
    return {"item": item.model_dump()}


@router.delete("/{account_id}")
async def delete_account(account_id: int, _: object = Depends(require_permission("media.manage")), session=Depends(get_session)):
    item = await session.get(MediaAccount, account_id)
    if not item:
        return {"ok": True}
    await session.delete(item)
    await session.commit()
    return {"ok": True}

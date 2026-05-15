from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlmodel import select

from server.auth.deps import require_permission
from server.db import get_session
from server.marketing.login import create_qr_login
from server.marketing.models import MktPlatformProfile, MktPlatformSession
from server.models import MediaAccount


router = APIRouter(prefix="/api/media-accounts", tags=["media-accounts"])


class MediaAccountCreate(BaseModel):
    platform: str
    nickname: str | None = None
    notes: str | None = None
    auth_json: str | None = None
    auto_login: bool = True


@router.get("")
async def list_accounts(
    platform: str | None = None,
    status: str | None = None,
    page: int | None = 1,
    page_size: int | None = 20,
    limit: int | None = None,
    _: object = Depends(require_permission("media.view")),
    session=Depends(get_session),
):
    if page_size is None and limit is not None:
        page_size = int(limit)
    page_size = int(page_size or 20)
    if page_size not in {20, 50, 100}:
        raise HTTPException(status_code=400, detail="page_size 仅支持 20/50/100")
    page = max(1, int(page or 1))
    offset = (page - 1) * page_size

    stmt = select(MediaAccount)
    if platform:
        stmt = stmt.where(MediaAccount.platform == platform)
    if status:
        stmt = stmt.where(MediaAccount.status == status)

    count_stmt = select(func.count()).select_from(MediaAccount)
    if platform:
        count_stmt = count_stmt.where(MediaAccount.platform == platform)
    if status:
        count_stmt = count_stmt.where(MediaAccount.status == status)
    total_row = (await session.exec(count_stmt)).one()
    total = int(total_row[0] if isinstance(total_row, tuple) else total_row)

    stmt = stmt.order_by(MediaAccount.updated_at.desc()).offset(offset).limit(page_size)
    res = await session.exec(stmt)
    items = res.all()

    out: list[dict] = []
    for acc in items:
        d = acc.model_dump()
        profile_id = acc.profile_id
        if profile_id:
            sres = await session.exec(
                select(MktPlatformSession)
                .where(MktPlatformSession.profile_id == profile_id)
                .order_by(MktPlatformSession.updated_at.desc())
                .limit(1)
            )
            s = sres.first()
            if s:
                d["latest_session_id"] = s.id
                d["session_status"] = s.status
                d["session_last_validated_at"] = s.last_validated_at
                d["session_last_error"] = s.last_error
                d["status"] = {"valid": "connected", "expired": "expired", "invalid": "disconnected"}.get(s.status, acc.status)
                try:
                    sd = s.session_data if isinstance(s.session_data, dict) else {}
                    acct = sd.get("account") if isinstance(sd.get("account"), dict) else {}
                    nn = str(acct.get("nickname") or "").strip()
                    if nn:
                        d["nickname"] = nn
                except Exception:
                    pass
            else:
                d["session_status"] = None
                d["status"] = "disconnected"
        out.append(d)
    return {"items": out, "total": total, "page": page, "page_size": page_size}


@router.post("")
async def create_account(
    req: MediaAccountCreate, _: object = Depends(require_permission("media.manage")), session=Depends(get_session)
):
    platform = (req.platform or "").strip().lower()
    if platform not in {"xhs", "douyin"}:
        raise HTTPException(status_code=400, detail="platform 仅支持 xhs / douyin")

    profile = MktPlatformProfile(
        platform=platform,
        profile_type="owned",
        nickname=req.nickname,
        status="active",
        updated_at=datetime.utcnow(),
    )
    session.add(profile)
    await session.commit()
    await session.refresh(profile)

    item = MediaAccount(
        platform=platform,
        nickname=req.nickname,
        notes=req.notes,
        auth_json=req.auth_json,
        status="disconnected",
        profile_id=profile.id,
        updated_at=datetime.utcnow(),
    )
    session.add(item)
    await session.commit()
    await session.refresh(item)

    run = None
    if req.auto_login:
        run = await create_qr_login(profile.id, timeout_sec=300)
        item.last_login_run_id = run.id
        item.updated_at = datetime.utcnow()
        session.add(item)
        await session.commit()
        await session.refresh(item)

    return {"item": item.model_dump(), "login_run": (run.model_dump() if run else None)}


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
    if item.profile_id:
        prof = await session.get(MktPlatformProfile, item.profile_id)
        if prof:
            prof.status = "disabled"
            prof.updated_at = datetime.utcnow()
            session.add(prof)
    await session.delete(item)
    await session.commit()
    return {"ok": True}


@router.post("/{account_id}/login")
async def start_login(
    account_id: int,
    _: object = Depends(require_permission("media.manage")),
    session=Depends(get_session),
):
    acc = await session.get(MediaAccount, account_id)
    if not acc:
        raise HTTPException(status_code=404, detail="not found")

    profile_id = acc.profile_id
    if not profile_id:
        profile = MktPlatformProfile(
            platform=acc.platform,
            profile_type="owned",
            nickname=acc.nickname,
            status="active",
            updated_at=datetime.utcnow(),
        )
        session.add(profile)
        await session.commit()
        await session.refresh(profile)
        profile_id = profile.id
        acc.profile_id = profile_id
        session.add(acc)
        await session.commit()

    run = await create_qr_login(profile_id, timeout_sec=300)
    acc.last_login_run_id = run.id
    acc.updated_at = datetime.utcnow()
    session.add(acc)
    await session.commit()
    await session.refresh(acc)
    return {"ok": True, "account": acc.model_dump(), "run": run.model_dump()}

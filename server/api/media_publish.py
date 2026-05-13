from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from server.auth.deps import require_permission
from server.config import settings
from server.db import get_session
from server.models import MediaAccount
from server.new_media import build_automator, now_iso
from server.publishers.base import PublishPayload


router = APIRouter(prefix="/api/media-publish", tags=["media-publish"])


PROFILE_ROOT = (Path(__file__).resolve().parents[2] / settings.media_profile_root).resolve()


class ConnectReq(BaseModel):
    timeout_sec: int = Field(default=180, ge=30, le=600)
    headless: bool = False


@router.post("/accounts/{account_id}/connect")
async def connect_account(
    account_id: int,
    req: ConnectReq,
    _: object = Depends(require_permission("media.manage")),
    session=Depends(get_session),
):
    item = await session.get(MediaAccount, account_id)
    if not item:
        return {"ok": False, "detail": "account not found"}

    automator = build_automator(platform=item.platform, account_id=account_id, root=PROFILE_ROOT)
    result = await automator.connect_qr(timeout_sec=req.timeout_sec, headless=req.headless)

    if result.ok and result.fingerprint:
        item.status = "connected"
        item.auth_json = json.dumps(
            {
                "connected_at": now_iso(),
                "fingerprint": result.fingerprint,
            },
            ensure_ascii=False,
        )
        item.updated_at = datetime.utcnow()
        session.add(item)
        await session.commit()

    return {"ok": result.ok, "status": result.status, "detail": result.detail}


class PublishReq(BaseModel):
    title: str
    text: str
    tags: list[str] | None = None
    dry_run: bool = False


@router.post("/accounts/{account_id}/publish")
async def publish_by_account(
    account_id: int,
    req: PublishReq,
    _: object = Depends(require_permission("media.manage")),
    session=Depends(get_session),
):
    item = await session.get(MediaAccount, account_id)
    if not item:
        return {"ok": False, "detail": "account not found"}

    automator = build_automator(platform=item.platform, account_id=account_id, root=PROFILE_ROOT)
    result = await automator.publish(
        payload=PublishPayload(title=req.title, text=req.text, tags=req.tags),
        dry_run=req.dry_run,
    )
    if result.ok:
        item.status = "connected"
    elif result.status in {"not_connected"}:
        item.status = "disconnected"
    item.updated_at = datetime.utcnow()
    session.add(item)
    await session.commit()

    return {
        "ok": result.ok,
        "status": result.status,
        "detail": result.detail,
        "platform": result.platform,
        "mode": result.mode,
        "preview": result.preview,
    }

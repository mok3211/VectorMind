from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from server.api.executors import get_executor_from_token
from server.db import get_session
from server.marketing.ingest import ingest_marketing_payload


router = APIRouter(prefix="/api/marketing", tags=["marketing"])


class IngestReq(BaseModel):
    platform: str
    payload: dict
    ensure_track_media: bool = True


@router.post("/ingest")
async def ingest(req: IngestReq, _: object = Depends(get_executor_from_token), session=Depends(get_session)):
    platform = (req.platform or "").strip().lower()
    if platform not in {"xhs", "douyin"}:
        raise HTTPException(status_code=400, detail="platform 仅支持 xhs/douyin")
    stats = await ingest_marketing_payload(
        session=session,
        platform=platform,
        payload=req.payload or {},
        ensure_track_media=bool(req.ensure_track_media),
    )
    return {"ok": True, "stats": stats}


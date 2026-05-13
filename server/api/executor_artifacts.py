from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from server.api.executors import get_executor_from_token
from server.config import settings


router = APIRouter(prefix="/api/executors", tags=["executors"])


@router.post("/artifacts")
async def upload_artifact(
    kind: str = Form(...),
    filename: str = Form(...),
    file: UploadFile = File(...),
    executor=Depends(get_executor_from_token),
):
    kind = (kind or "").strip().lower()
    if kind not in {"screenshot", "video"}:
        raise HTTPException(status_code=400, detail="kind 仅支持 screenshot/video")
    filename = os.path.basename(filename)
    if not filename:
        raise HTTPException(status_code=400, detail="filename 不能为空")

    root = Path(settings.media_profile_root).resolve() / "executor_artifacts" / str(executor.id)
    root.mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    target = root / f"{ts}_{kind}_{filename}"

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="空文件")
    target.write_bytes(data)

    # 这里先返回 server 本地路径（企业内网部署足够用）；后续可接对象存储并返回 URL
    return {"ok": True, "path": str(target), "kind": kind}


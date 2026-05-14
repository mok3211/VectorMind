from __future__ import annotations

import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import desc, select

from server.auth.deps import require_admin
from server.db import get_session
from server.llm.secrets import decrypt_secret, encrypt_secret, mask_secret
from server.models import LLMProviderConfig, SystemSetting


router = APIRouter(prefix="/api/llm", tags=["llm"])


DEFAULT_SETTING_KEY = "llm.default"


class ConfigCreate(BaseModel):
    name: str
    provider: str
    api_key: str
    api_base: str | None = None


class ConfigUpdate(BaseModel):
    name: str | None = None
    api_key: str | None = None
    api_base: str | None = None


@router.get("/configs")
async def list_configs(_: object = Depends(require_admin), session=Depends(get_session)):
    res = await session.execute(select(LLMProviderConfig).order_by(desc(LLMProviderConfig.updated_at)))
    items = res.scalars().all()
    out = []
    for i in items:
        try:
            key_plain = decrypt_secret(i.api_key_enc)
        except Exception:
            key_plain = ""
        out.append(
            {
                "id": i.id,
                "name": i.name,
                "provider": i.provider,
                "api_base": i.api_base,
                "key_mask": mask_secret(key_plain),
                "updated_at": i.updated_at.isoformat(),
            }
        )
    return {"items": out}


@router.post("/configs")
async def create_config(req: ConfigCreate, _: object = Depends(require_admin), session=Depends(get_session)):
    if not req.name.strip():
        raise HTTPException(status_code=400, detail="name 不能为空")
    if not req.provider.strip():
        raise HTTPException(status_code=400, detail="provider 不能为空")
    if not req.api_key.strip():
        raise HTTPException(status_code=400, detail="api_key 不能为空")
    item = LLMProviderConfig(
        name=req.name.strip(),
        provider=req.provider.strip(),
        api_key_enc=encrypt_secret(req.api_key.strip()),
        api_base=(req.api_base.strip() if req.api_base else None),
        updated_at=datetime.utcnow(),
    )
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return {"item": {"id": item.id}}


@router.put("/configs/{config_id}")
async def update_config(
    config_id: int, req: ConfigUpdate, _: object = Depends(require_admin), session=Depends(get_session)
):
    item = await session.get(LLMProviderConfig, config_id)
    if not item:
        raise HTTPException(status_code=404, detail="not found")
    if req.name is not None:
        item.name = req.name.strip()
    if req.api_key is not None and req.api_key.strip():
        item.api_key_enc = encrypt_secret(req.api_key.strip())
    if req.api_base is not None:
        item.api_base = req.api_base.strip() if req.api_base else None
    item.updated_at = datetime.utcnow()
    session.add(item)
    await session.commit()
    return {"ok": True}


@router.delete("/configs/{config_id}")
async def delete_config(config_id: int, _: object = Depends(require_admin), session=Depends(get_session)):
    item = await session.get(LLMProviderConfig, config_id)
    if not item:
        return {"ok": True}
    await session.delete(item)
    await session.commit()
    return {"ok": True}


class DefaultSet(BaseModel):
    config_id: int | None = None
    model: str | None = None


@router.get("/default")
async def get_default(_: object = Depends(require_admin), session=Depends(get_session)):
    s = await session.get(SystemSetting, DEFAULT_SETTING_KEY)
    if not s:
        return {"item": {"config_id": None, "model": None}}
    try:
        data = json.loads(s.value)
    except Exception:
        data = {}
    return {"item": {"config_id": data.get("config_id"), "model": data.get("model")}}


@router.put("/default")
async def set_default(req: DefaultSet, _: object = Depends(require_admin), session=Depends(get_session)):
    payload = {"config_id": req.config_id, "model": req.model}
    s = await session.get(SystemSetting, DEFAULT_SETTING_KEY)
    if not s:
        s = SystemSetting(key=DEFAULT_SETTING_KEY, value=json.dumps(payload, ensure_ascii=False))
        session.add(s)
        await session.commit()
        return {"ok": True}
    s.value = json.dumps(payload, ensure_ascii=False)
    s.updated_at = datetime.utcnow()
    session.add(s)
    await session.commit()
    return {"ok": True}


async def resolve_config(session, config_id: int) -> tuple[str, str | None, str]:
    item = await session.get(LLMProviderConfig, config_id)
    if not item:
        raise HTTPException(status_code=404, detail="llm config not found")
    return decrypt_secret(item.api_key_enc), item.api_base, item.provider

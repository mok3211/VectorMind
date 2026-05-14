from __future__ import annotations

import json

from fastapi import HTTPException

from server.api.llm import DEFAULT_SETTING_KEY, resolve_config
from server.models import SystemSetting


DEFAULT_MODELS: dict[str, str] = {
    "nvidia_nim": "meta/llama-3.1-70b-instruct",
    "openai": "openai/gpt-4o-mini",
    "gemini": "gemini/gemini-1.5-flash",
    "deepseek": "deepseek/deepseek-chat",
}


def normalize_model(*, provider: str | None, model: str | None) -> str:
    m = (model or "").strip()
    if not m:
        raise HTTPException(status_code=400, detail="model 不能为空")
    if "/" in m:
        return m
    if provider:
        return f"{provider}/{m}"
    return m


async def resolve_llm_override(session, llm: dict | None) -> tuple[str | None, dict | None]:
    if not llm:
        return None, None

    mode = (llm.get("mode") or "default").strip()
    model = llm.get("model")

    if mode == "default":
        if model:
            return normalize_model(provider=None, model=model), None
        s = await session.get(SystemSetting, DEFAULT_SETTING_KEY)
        if not s:
            return None, None
        try:
            data = json.loads(s.value)
        except Exception:
            data = {}
        cid = data.get("config_id")
        m = data.get("model")
        if cid:
            key, base, provider = await resolve_config(session, int(cid))
            extra = {"api_key": key}
            if base:
                extra["api_base"] = base
            return (normalize_model(provider=provider, model=m) if m else None), extra
        if m:
            return normalize_model(provider=None, model=m), None
        return None, None

    if mode == "server":
        cid = llm.get("config_id")
        if not cid:
            raise HTTPException(status_code=400, detail="config_id 不能为空")
        key, base, provider = await resolve_config(session, int(cid))
        extra = {"api_key": key}
        if base:
            extra["api_base"] = base
        if model:
            return normalize_model(provider=provider, model=model), extra
        return normalize_model(provider=provider, model=DEFAULT_MODELS.get(provider)), extra

    if mode == "local":
        provider = llm.get("provider")
        api_key = llm.get("api_key")
        api_base = llm.get("api_base")
        if not provider:
            raise HTTPException(status_code=400, detail="provider 不能为空")
        if not api_key:
            raise HTTPException(status_code=400, detail="api_key 不能为空")
        extra = {"api_key": api_key}
        if api_base:
            extra["api_base"] = api_base
        if model:
            return normalize_model(provider=str(provider), model=model), extra
        return normalize_model(provider=str(provider), model=DEFAULT_MODELS.get(str(provider))), extra

    raise HTTPException(status_code=400, detail=f"unknown llm mode: {mode}")

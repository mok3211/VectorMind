from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from deeplegacy.agent import agent
from server.auth.deps import require_permission
from server.db import get_session
from server.models import AgentRun
from server.publishers.base import PublishPayload
from server.publishers.registry import publisher_registry


router = APIRouter(prefix="/morning-history", tags=["morning-history"])


class GenerateReq(BaseModel):
    # 预留：未来支持传入指定日期
    llm: dict | None = None


@router.post("/generate")
async def generate(_: GenerateReq, __: object = Depends(require_permission("agents.run")), session=Depends(get_session)):
    try:
        from server.llm.runtime import resolve_llm_override

        llm_model, llm_extra = await resolve_llm_override(session, _.llm)
        result = await agent.run(llm_model=llm_model, llm_extra=llm_extra)
        session.add(
            AgentRun(
                agent="morning_history",
                input_json="{}",
                output_text=result.text,
                model=(result.meta or {}).get("model"),
                prompt_version=(result.meta or {}).get("prompt_version"),
                steps_json=json.dumps((result.meta or {}).get("steps", []), ensure_ascii=False),
                assets_json=json.dumps((result.meta or {}).get("artifacts", {}), ensure_ascii=False),
            )
        )
        await session.commit()
        return {"text": result.text, "meta": result.meta}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)[:500])


class PublishReq(BaseModel):
    publisher: str
    title: str
    text: str
    tags: list[str] | None = None


@router.post("/publish")
async def publish(req: PublishReq):
    publisher = publisher_registry.get(req.publisher)
    payload = PublishPayload(title=req.title, text=req.text, tags=req.tags)
    return await publisher.publish(payload)

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from server.auth.deps import require_permission
from server.db import get_session
from server.models import AgentRun
from server.publishers.base import PublishPayload
from server.publishers.registry import publisher_registry
from travel_planner.agent import agent


router = APIRouter(prefix="/travel-planner", tags=["travel-planner"])


class GenerateReq(BaseModel):
    destination: str = Field(..., description="目的地，如：成都/东京/杭州")
    days: int = 3
    budget: str | None = None
    preferences: str | None = None
    llm: dict | None = None


@router.post("/generate")
async def generate(req: GenerateReq, _: object = Depends(require_permission("agents.run")), session=Depends(get_session)):
    try:
        from server.llm.runtime import resolve_llm_override

        llm_model, llm_extra = await resolve_llm_override(session, req.llm)
        result = await agent.run(
            destination=req.destination,
            days=req.days,
            budget=req.budget,
            preferences=req.preferences,
            llm_model=llm_model,
            llm_extra=llm_extra,
        )
        session.add(
            AgentRun(
                agent="travel_planner",
                input_json=req.model_dump_json(),
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

from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from deeplegacy.agent import agent
from server.auth.deps import require_admin
from server.db import get_session
from server.models import AgentRun
from server.publishers.base import PublishPayload
from server.publishers.registry import publisher_registry


router = APIRouter(prefix="/morning-history", tags=["morning-history"])


class GenerateReq(BaseModel):
    # 预留：未来支持传入指定日期
    pass


@router.post("/generate")
async def generate(_: GenerateReq, __: object = Depends(require_admin), session=Depends(get_session)):
    result = await agent.run()
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

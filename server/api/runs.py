from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import desc
from sqlmodel import select

from server.auth.deps import require_permission
from server.db import get_session
from server.models import AgentRun


router = APIRouter(prefix="/api/runs", tags=["runs"])


@router.get("")
async def list_runs(
    agent: str | None = None,
    limit: int = 50,
    _: object = Depends(require_permission("runs.view")),
    session=Depends(get_session),
):
    stmt = select(AgentRun).order_by(desc(AgentRun.created_at)).limit(min(limit, 200))
    if agent:
        stmt = select(AgentRun).where(AgentRun.agent == agent).order_by(desc(AgentRun.created_at)).limit(
            min(limit, 200)
        )
    res = await session.exec(stmt)
    items = res.all()
    return {"items": [i.model_dump() for i in items]}


@router.get("/{run_id}")
async def get_run(run_id: int, _: object = Depends(require_permission("runs.view")), session=Depends(get_session)):
    item = await session.get(AgentRun, run_id)
    if not item:
        return {"ok": False, "detail": "not found"}
    return {"item": item.model_dump()}

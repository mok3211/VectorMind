from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import desc, func
from sqlmodel import select

from server.auth.deps import require_permission
from server.db import get_session
from server.models import AgentRun


router = APIRouter(prefix="/api/runs", tags=["runs"])


@router.get("")
async def list_runs(
    agent: str | None = None,
    page: int | None = 1,
    page_size: int | None = 20,
    limit: int | None = None,
    _: object = Depends(require_permission("runs.view")),
    session=Depends(get_session),
):
    if page_size is None and limit is not None:
        page_size = int(limit)
    page_size = int(page_size or 20)
    if page_size not in {20, 50, 100}:
        page_size = 20
    page = max(1, int(page or 1))
    offset = (page - 1) * page_size

    stmt = select(AgentRun)
    if agent:
        stmt = stmt.where(AgentRun.agent == agent)

    count_stmt = select(func.count()).select_from(AgentRun)
    if agent:
        count_stmt = count_stmt.where(AgentRun.agent == agent)
    total_row = (await session.exec(count_stmt)).one()
    total = int(total_row[0] if isinstance(total_row, tuple) else total_row)

    stmt = stmt.order_by(desc(AgentRun.created_at)).offset(offset).limit(page_size)
    res = await session.exec(stmt)
    items = res.all()
    return {"items": [i.model_dump() for i in items], "total": total, "page": page, "page_size": page_size}


@router.get("/{run_id}")
async def get_run(run_id: int, _: object = Depends(require_permission("runs.view")), session=Depends(get_session)):
    item = await session.get(AgentRun, run_id)
    if not item:
        return {"ok": False, "detail": "not found"}
    return {"item": item.model_dump()}

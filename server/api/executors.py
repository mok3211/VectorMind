from __future__ import annotations

from datetime import datetime
from secrets import token_hex

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlmodel import select

from server.auth.deps import require_permission
from server.db import get_session
from server.models import Executor


router = APIRouter(prefix="/api/executors", tags=["executors"])


class ExecutorCreate(BaseModel):
    name: str


@router.get("")
async def list_executors(_: object = Depends(require_permission("executors.manage")), session=Depends(get_session)):
    res = await session.exec(select(Executor).order_by(Executor.created_at.desc()))
    return {"items": [i.model_dump() for i in res.all()]}


@router.post("")
async def create_executor(req: ExecutorCreate, _: object = Depends(require_permission("executors.manage")), session=Depends(get_session)):
    name = req.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="name 不能为空")
    token = token_hex(24)  # 48 chars
    item = Executor(name=name, token=token, enabled=True, created_at=datetime.utcnow())
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return {"item": item.model_dump(), "token": token}


@router.post("/{executor_id}/rotate-token")
async def rotate_token(executor_id: int, _: object = Depends(require_permission("executors.manage")), session=Depends(get_session)):
    item = await session.get(Executor, executor_id)
    if not item:
        raise HTTPException(status_code=404, detail="not found")
    token = token_hex(24)
    item.token = token
    item.updated_at = datetime.utcnow() if hasattr(item, "updated_at") else item.created_at  # type: ignore[attr-defined]
    session.add(item)
    await session.commit()
    return {"ok": True, "token": token}


async def get_executor_from_token(
    x_executor_token: str | None = Header(default=None),
    session=Depends(get_session),
) -> Executor:
    if not x_executor_token:
        raise HTTPException(status_code=401, detail="缺少 X-Executor-Token")
    res = await session.exec(select(Executor).where(Executor.token == x_executor_token))
    executor = res.first()
    if not executor or not executor.enabled:
        raise HTTPException(status_code=401, detail="Executor token 无效")
    executor.last_seen_at = datetime.utcnow()
    session.add(executor)
    await session.commit()
    return executor


@router.post("/heartbeat")
async def heartbeat(executor: Executor = Depends(get_executor_from_token)):
    return {"ok": True, "executor": executor.model_dump()}

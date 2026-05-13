from __future__ import annotations

from fastapi import APIRouter, Depends

from server.auth.deps import require_permission
from server.skills.registry import skill_registry


router = APIRouter(prefix="/api/skills", tags=["skills"])


@router.get("")
async def list_skills(_: object = Depends(require_permission("agents.view"))):
    return {"skills": skill_registry.list()}

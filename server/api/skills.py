from __future__ import annotations

from fastapi import APIRouter, Depends

from server.auth.deps import require_admin
from server.skills.registry import skill_registry


router = APIRouter(prefix="/api/skills", tags=["skills"])


@router.get("")
async def list_skills(_: object = Depends(require_admin)):
    return {"skills": skill_registry.list()}


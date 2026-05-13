from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from server.auth.deps import require_permission
from server.core.agents import AGENTS


router = APIRouter(prefix="/api/prompts", tags=["prompts"])


def safe_read_text(path: Path) -> str:
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail=f"prompt 文件不存在：{path.name}")
    return path.read_text(encoding="utf-8")


def safe_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


@router.get("")
async def list_prompts(_: object = Depends(require_permission("prompts.view"))):
    items = []
    for key, info in AGENTS.items():
        prompt_root = info.dir / "prompts"
        versions: list[str] = []
        if prompt_root.exists():
            for p in prompt_root.iterdir():
                if p.is_dir():
                    versions.append(p.name)
        versions = sorted(versions)
        items.append({"agent": key, "name": info.name, "versions": versions})
    return {"items": items}


@router.get("/{agent}/{version}")
async def get_prompt(agent: str, version: str, _: object = Depends(require_permission("prompts.view"))):
    if agent not in AGENTS:
        raise HTTPException(status_code=404, detail="未知 agent")
    base = AGENTS[agent].dir / "prompts" / version
    return {
        "agent": agent,
        "version": version,
        "system": safe_read_text(base / "system.jinja"),
        "user": safe_read_text(base / "user.jinja"),
    }


class SaveReq(BaseModel):
    system: str
    user: str


@router.put("/{agent}/{version}")
async def save_prompt(agent: str, version: str, req: SaveReq, _: object = Depends(require_permission("prompts.manage"))):
    if agent not in AGENTS:
        raise HTTPException(status_code=404, detail="未知 agent")
    base = AGENTS[agent].dir / "prompts" / version
    safe_write_text(base / "system.jinja", req.system)
    safe_write_text(base / "user.jinja", req.user)
    return {"ok": True}

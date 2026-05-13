from __future__ import annotations

from fastapi import APIRouter, Depends

from server.auth.deps import require_permission
from server.workflows.registry import workflow_registry


router = APIRouter(prefix="/api/workflows", tags=["workflows"])


@router.get("")
async def list_workflows(_: object = Depends(require_permission("workflows.view"))):
    specs = workflow_registry.list()
    return {
        "items": [
            {"agent": s.agent, "name": s.name, "nodes": s.nodes, "edges": s.edges} for s in specs
        ]
    }


@router.get("/{agent}")
async def get_workflow(agent: str, _: object = Depends(require_permission("workflows.view"))):
    s = workflow_registry.get(agent)
    return {"agent": s.agent, "name": s.name, "nodes": s.nodes, "edges": s.edges}

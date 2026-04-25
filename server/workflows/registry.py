from __future__ import annotations

from server.workflows.specs import WorkflowSpec


class WorkflowRegistry:
    def __init__(self) -> None:
        self._items: dict[str, WorkflowSpec] = {}

    def register(self, spec: WorkflowSpec) -> None:
        self._items[spec.agent] = spec

    def get(self, agent: str) -> WorkflowSpec:
        if agent not in self._items:
            raise KeyError(f"unknown workflow agent: {agent}")
        return self._items[agent]

    def list(self) -> list[WorkflowSpec]:
        return [self._items[k] for k in sorted(self._items.keys())]


workflow_registry = WorkflowRegistry()


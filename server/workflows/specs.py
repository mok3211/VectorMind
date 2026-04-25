from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class WorkflowSpec:
    agent: str
    name: str
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]


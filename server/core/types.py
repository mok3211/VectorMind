from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(slots=True)
class LLMMessage:
    role: str  # "system" | "user" | "assistant"
    content: str


@dataclass(slots=True)
class AgentResult:
    text: str
    meta: dict[str, Any] | None = None


TemplateVars = Mapping[str, Any]


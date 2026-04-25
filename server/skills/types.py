from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from server.core.types import LLMMessage


@dataclass(slots=True)
class AgentContext:
    """
    每次 agent 运行的上下文，skills 可以读写它来实现：
    - 关键节点记录（可视化、调试、复盘）
    - 未来的素材产出（图片/音频/视频）统一挂在 artifacts
    """

    agent: str
    model: str
    prompt_version: str
    inputs: dict[str, Any] = field(default_factory=dict)
    steps: list[dict[str, Any]] = field(default_factory=list)
    artifacts: dict[str, Any] = field(default_factory=dict)

    def log_step(self, *, name: str, data: dict[str, Any] | None = None) -> None:
        self.steps.append({"name": name, "data": data or {}})


@dataclass(slots=True)
class PromptPack:
    system: str
    user: str
    messages: list[LLMMessage]


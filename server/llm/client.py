from __future__ import annotations

from typing import Any

import litellm

from server.core.types import LLMMessage


class LLMClient:
    """
    统一 LLM 客户端（LiteLLM）。

    目标：
    - 未来切换模型/供应商只改 env（OpenAI/Anthropic/Gemini/DeepSeek...）
    - 上层 agent 不关心具体 SDK。
    """

    async def generate_text(
        self,
        *,
        model: str,
        messages: list[LLMMessage],
        temperature: float = 0.7,
        max_tokens: int = 800,
        extra: dict[str, Any] | None = None,
    ) -> str:
        payload_messages = [{"role": m.role, "content": m.content} for m in messages]
        resp = await litellm.acompletion(
            model=model,
            messages=payload_messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **(extra or {}),
        )
        # LiteLLM response -> OpenAI-like
        return resp["choices"][0]["message"]["content"]


llm_client = LLMClient()


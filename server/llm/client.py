from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_nvidia_ai_endpoints import ChatNVIDIA

from server.config import settings
from server.core.types import LLMMessage


class LLMClient:
    """
    统一 LLM 客户端（LangChain + NVIDIA）。

    目标：
    - 上层 agent 不关心具体 SDK；
    - 只需环境变量即可切模型。
    """

    @staticmethod
    def _to_langchain_messages(messages: list[LLMMessage]) -> list[SystemMessage | HumanMessage | AIMessage]:
        lc_messages: list[SystemMessage | HumanMessage | AIMessage] = []
        for m in messages:
            if m.role == "system":
                lc_messages.append(SystemMessage(content=m.content))
            elif m.role == "assistant":
                lc_messages.append(AIMessage(content=m.content))
            else:
                lc_messages.append(HumanMessage(content=m.content))
        return lc_messages

    async def generate_text(
        self,
        *,
        model: str,
        messages: list[LLMMessage],
        temperature: float = 0.7,
        max_tokens: int = 800,
        extra: dict[str, Any] | None = None,
    ) -> str:
        api_key = settings.nvidia_api_key
        if not api_key:
            raise RuntimeError("missing NVIDIA_API_KEY (env: NVIDIA_API_KEY)")

        llm = ChatNVIDIA(
            model=model,
            api_key=api_key,
            temperature=temperature,
            max_tokens=max_tokens,
            **(extra or {}),
        )
        resp = await llm.ainvoke(self._to_langchain_messages(messages))
        return str(resp.content)


llm_client = LLMClient()

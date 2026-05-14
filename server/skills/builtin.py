from __future__ import annotations

from pathlib import Path
from typing import Any

from server.core.types import LLMMessage
from server.llm.client import llm_client
from server.prompts.registry import prompt_registry
from server.skills.base import Skill
from server.skills.types import AgentContext, PromptPack


class PromptRenderSkill:
    name = "prompt_render"

    async def run(
        self,
        ctx: AgentContext,
        *,
        agent_dir: Path,
        version: str,
        vars: dict[str, Any],
    ) -> PromptPack:
        prompt = prompt_registry.load(agent_dir=agent_dir, version=version)
        system = prompt_registry.render(template=prompt.system, vars=vars)
        user = prompt_registry.render(template=prompt.user, vars=vars)
        messages = [LLMMessage(role="system", content=system), LLMMessage(role="user", content=user)]
        ctx.log_step(name="prompt_render", data={"version": version, "vars": vars})
        return PromptPack(system=system, user=user, messages=messages)


class LLMGenerateSkill:
    name = "llm_generate"

    async def run(
        self,
        ctx: AgentContext,
        *,
        messages: list[LLMMessage],
        temperature: float,
        max_tokens: int,
        extra: dict[str, Any] | None = None,
    ) -> str:
        ctx.log_step(
            name="llm_generate",
            data={
                "model": ctx.model,
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
        )
        return await llm_client.generate_text(
            model=ctx.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            extra=extra,
        )


class ImageGenerateSkill:
    """
    占位：未来接入真正的生图服务（例如 Flux/SDXL/官方文生图 API）。
    后台可视化会把它当成一个节点展示出来。
    """

    name = "image_generate"

    async def run(self, ctx: AgentContext, *, prompt: str, size: str = "1024x1024") -> dict:
        ctx.log_step(name="image_generate", data={"prompt": prompt, "size": size, "status": "stub"})
        return {
            "status": "stub",
            "detail": "尚未接入生图服务（已预留 skill）。",
            "prompt": prompt,
            "size": size,
        }


class VideoGenerateSkill:
    name = "video_generate"

    async def run(self, ctx: AgentContext, *, script: str, style: str = "short") -> dict:
        ctx.log_step(name="video_generate", data={"style": style, "status": "stub"})
        return {
            "status": "stub",
            "detail": "尚未接入生视频服务（已预留 skill）。",
            "style": style,
        }


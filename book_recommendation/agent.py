from __future__ import annotations

from pathlib import Path

from server.config import settings
from server.core.types import AgentResult
from server.skills.registry import skill_registry
from server.skills.types import AgentContext


AGENT_DIR = Path(__file__).resolve().parent


class BookRecommendationAgent:
    name = "book_recommendation"

    async def run(self, *, theme: str | None = None, level: str | None = None) -> AgentResult:
        model = settings.book_recommendation_model or settings.llm_model_default
        prompt_version = settings.book_recommendation_prompt_version
        ctx = AgentContext(
            agent=self.name,
            model=model,
            prompt_version=prompt_version,
            inputs={"theme": theme, "level": level},
        )

        prompt_pack = await skill_registry.get("prompt_render").run(
            ctx,
            agent_dir=AGENT_DIR,
            version=prompt_version,
            vars={"theme": theme, "level": level},
        )

        text = await skill_registry.get("llm_generate").run(
            ctx,
            messages=prompt_pack.messages,
            temperature=0.7,
            max_tokens=900,
        )
        return AgentResult(
            text=text,
            meta={
                "model": model,
                "prompt_version": prompt_version,
                "steps": ctx.steps,
                "artifacts": ctx.artifacts,
            },
        )


agent = BookRecommendationAgent()

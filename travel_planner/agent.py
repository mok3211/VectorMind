from __future__ import annotations

from pathlib import Path

from server.config import settings
from server.core.types import AgentResult
from server.skills.registry import skill_registry
from server.skills.types import AgentContext


AGENT_DIR = Path(__file__).resolve().parent


class TravelPlannerAgent:
    name = "travel_planner"

    async def run(
        self,
        *,
        destination: str,
        days: int = 3,
        budget: str | None = None,
        preferences: str | None = None,
    ) -> AgentResult:
        model = settings.travel_planner_model or settings.llm_model_default
        prompt_version = settings.travel_planner_prompt_version
        ctx = AgentContext(
            agent=self.name,
            model=model,
            prompt_version=prompt_version,
            inputs={
                "destination": destination,
                "days": days,
                "budget": budget,
                "preferences": preferences,
            },
        )

        prompt_pack = await skill_registry.get("prompt_render").run(
            ctx,
            agent_dir=AGENT_DIR,
            version=prompt_version,
            vars={
                "destination": destination,
                "days": days,
                "budget": budget,
                "preferences": preferences,
            },
        )

        text = await skill_registry.get("llm_generate").run(
            ctx,
            messages=prompt_pack.messages,
            temperature=0.4,
            max_tokens=1200,
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


agent = TravelPlannerAgent()

from __future__ import annotations

import datetime
from pathlib import Path

from server.config import settings
from server.core.types import AgentResult
from server.skills.registry import skill_registry
from server.skills.types import AgentContext


AGENT_DIR = Path(__file__).resolve().parent


class MorningHistoryAgent:
    name = "morning_history"

    async def run(
        self,
        *,
        date: datetime.date | None = None,
        llm_model: str | None = None,
        llm_extra: dict | None = None,
    ) -> AgentResult:
        model = llm_model or settings.morning_history_model or settings.llm_model_default
        prompt_version = settings.morning_history_prompt_version

        d = date or datetime.date.today()
        today = d.strftime("%m月%d日")

        ctx = AgentContext(
            agent=self.name,
            model=model,
            prompt_version=prompt_version,
            inputs={"today": today},
        )
        ctx.log_step(name="get_date", data={"today": today})

        prompt_pack = await skill_registry.get("prompt_render").run(
            ctx,
            agent_dir=AGENT_DIR,
            version=prompt_version,
            vars={"word_count": 520, "today": today},
        )

        text = await skill_registry.get("llm_generate").run(
            ctx,
            messages=prompt_pack.messages,
            temperature=0.6,
            max_tokens=1200,
            extra=llm_extra,
        )
        return AgentResult(
            text=text,
            meta={
                "model": model,
                "prompt_version": prompt_version,
                "today": today,
                "steps": ctx.steps,
                "artifacts": ctx.artifacts,
            },
        )


agent = MorningHistoryAgent()

from __future__ import annotations

import asyncio

from book_recommendation.agent import agent as book_agent
from deeplegacy.agent import agent as history_agent
from morning_radio.agent import agent as morning_radio_agent
from server.skills import register_builtin_skills
from travel_planner.agent import agent as travel_agent


def _preview(text: str) -> str:
    return text.replace("\n", " ").strip()[:120]


async def main() -> None:
    register_builtin_skills()

    r1 = await morning_radio_agent.run(topic="AI daily news", audience="tech workers")
    print("morning_radio:", len(r1.text), _preview(r1.text))

    r2 = await book_agent.run(theme="machine learning", level="beginner")
    print("book_recommendation:", len(r2.text), _preview(r2.text))

    r3 = await travel_agent.run(
        destination="Hangzhou",
        days=2,
        budget="2000 CNY",
        preferences="food and nature",
    )
    print("travel_planner:", len(r3.text), _preview(r3.text))

    r4 = await history_agent.run()
    print("morning_history:", len(r4.text), _preview(r4.text))


if __name__ == "__main__":
    asyncio.run(main())

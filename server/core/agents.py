from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class AgentInfo:
    key: str
    name: str
    dir: Path


ROOT = Path(__file__).resolve().parents[2]


AGENTS: dict[str, AgentInfo] = {
    "morning_radio": AgentInfo(
        key="morning_radio", name="早安电台", dir=(ROOT / "morning_radio").resolve()
    ),
    "book_recommendation": AgentInfo(
        key="book_recommendation", name="书单推荐", dir=(ROOT / "book_recommendation").resolve()
    ),
    "travel_planner": AgentInfo(
        key="travel_planner", name="旅游规划", dir=(ROOT / "travel_planner").resolve()
    ),
    "morning_history": AgentInfo(
        key="morning_history", name="早安历史（deeplegacy）", dir=(ROOT / "deeplegacy").resolve()
    ),
}


from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from server.core.types import TemplateVars


@dataclass(frozen=True, slots=True)
class Prompt:
    system: str
    user: str


class PromptRegistry:
    """
    从文件系统加载提示词模板，支持版本化目录：

    <agent_folder>/prompts/v1/system.jinja
    <agent_folder>/prompts/v1/user.jinja
    """

    def __init__(self) -> None:
        self._jinja = Environment(
            loader=FileSystemLoader("/"),
            undefined=StrictUndefined,
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def load(self, *, agent_dir: Path, version: str) -> Prompt:
        base = agent_dir / "prompts" / version
        system_path = base / "system.jinja"
        user_path = base / "user.jinja"
        if not system_path.exists():
            raise FileNotFoundError(f"system prompt not found: {system_path}")
        if not user_path.exists():
            raise FileNotFoundError(f"user prompt not found: {user_path}")

        system = system_path.read_text(encoding="utf-8")
        user = user_path.read_text(encoding="utf-8")
        return Prompt(system=system, user=user)

    def render(self, *, template: str, vars: TemplateVars) -> str:
        tpl = self._jinja.from_string(template)
        return tpl.render(**vars)


prompt_registry = PromptRegistry()


from server.skills.builtin import (
    ImageGenerateSkill,
    LLMGenerateSkill,
    LangChainGenerateSkill,
    PromptRenderSkill,
    VideoGenerateSkill,
)
from server.skills.registry import skill_registry


def register_builtin_skills() -> None:
    skill_registry.register(PromptRenderSkill())
    skill_registry.register(LangChainGenerateSkill())
    skill_registry.register(LLMGenerateSkill())
    skill_registry.register(ImageGenerateSkill())
    skill_registry.register(VideoGenerateSkill())

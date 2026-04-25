from __future__ import annotations

from typing import Any, Protocol

from server.skills.types import AgentContext


class Skill(Protocol):
    """
    Skill：可替换的能力插件。

    例子：
    - prompt_render：渲染提示词
    - llm_generate：调用模型
    - image_generate：生图（未来接 SD/Flux/官方 API）
    - video_generate：生视频（未来接第三方服务）
    - publish_export：导出平台文案/排版
    """

    name: str

    async def run(self, ctx: AgentContext, **kwargs) -> Any: ...


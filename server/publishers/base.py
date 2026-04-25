from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(slots=True)
class PublishPayload:
    """
    工作流输出的统一载体：先做“结构化内容”，后续才能适配不同平台格式与素材。
    """

    title: str
    text: str
    tags: list[str] | None = None
    # 预留：未来支持图片/音频/视频等素材
    assets: dict[str, str] | None = None


class Publisher(Protocol):
    name: str

    async def publish(self, payload: PublishPayload) -> dict:
        """
        返回：
        - 支持“纯导出”：返回 platform_text / markdown / json
        - 支持“自动化发布”：返回 job_id / status
        """


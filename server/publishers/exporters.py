from __future__ import annotations

from server.publishers.base import PublishPayload


class MarkdownExporter:
    name = "markdown"

    async def publish(self, payload: PublishPayload) -> dict:
        tags = ""
        if payload.tags:
            tags = "\n\n" + " ".join([f"#{t}" for t in payload.tags])
        md = f"# {payload.title}\n\n{payload.text.strip()}{tags}\n"
        return {"type": "export", "format": "markdown", "content": md}


class XHSExporter:
    """
    小红书文案的“导出器”（先不做自动发帖）。

    说明：小红书/抖音等平台公开 API 受限，建议先把系统设计成：
    1) 产出结构化内容
    2) 导出平台格式
    3) 如确有需求再做 Playwright 半自动发布（降低账号风险）
    """

    name = "xhs"

    async def publish(self, payload: PublishPayload) -> dict:
        tags = ""
        if payload.tags:
            # XHS 常见写法：末尾集中放话题
            tags = "\n\n" + " ".join([f"#{t}" for t in payload.tags])
        text = f"{payload.title}\n\n{payload.text.strip()}{tags}\n"
        return {"type": "export", "platform": "xhs", "content": text}


class DouyinExporter:
    name = "douyin"

    async def publish(self, payload: PublishPayload) -> dict:
        tags = ""
        if payload.tags:
            tags = "\n" + " ".join([f"#{t}" for t in payload.tags])
        text = f"{payload.title}\n{payload.text.strip()}{tags}\n"
        return {"type": "export", "platform": "douyin", "content": text}


from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from server.config import settings


@dataclass(slots=True)
class CrawlResult:
    profiles_upserted: int = 0
    contents_upserted: int = 0
    content_snapshots: int = 0
    profile_snapshots: int = 0
    comments_upserted: int = 0
    raw: dict[str, Any] | None = None


class Crawler(Protocol):
    platform: str

    async def run(self, *, job_type: str, params: dict[str, Any] | None = None) -> CrawlResult: ...


class StubCrawler:
    """
    占位爬虫：先把“任务执行→run 记录→stats 入库”打通。
    后续会在 Python 中替换为真实实现（不依赖 xiaots/noctua 代码）。
    """

    def __init__(self, platform: str):
        self.platform = platform

    async def run(self, *, job_type: str, params: dict[str, Any] | None = None) -> CrawlResult:
        """
        为了让你能“完整流程跑一遍”，stub 会产出 mock 数据（不访问平台）：
        - content_search / content_metrics：产出内容与指标快照
        - profile_metrics：产出账号指标快照
        - comment_sync：产出评论明细
        """

        params = params or {}
        now = datetime.utcnow().replace(microsecond=0)

        def gen_media_ids() -> list[str]:
            ids = params.get("platform_content_ids") or params.get("media_ids") or []
            if isinstance(ids, str):
                ids = [s.strip() for s in ids.split(",") if s.strip()]
            if not isinstance(ids, list):
                ids = []
            ids = [str(x).strip() for x in ids if str(x).strip()]
            if ids:
                return ids[:50]
            # fallback: keyword 生成一个稳定 id
            kw = str(params.get("keyword") or "demo").strip() or "demo"
            return [f"{self.platform}_{kw}_001"]

        mock: dict[str, Any] = {
            "mode": "mock",
            "platform": self.platform,
            "job_type": job_type,
            "generated_at": now.isoformat() + "Z",
        }

        if job_type in {"content_search", "content_metrics"}:
            ids = gen_media_ids()
            contents = []
            snapshots = []
            for i, mid in enumerate(ids):
                contents.append(
                    {
                        "platform": self.platform,
                        "platform_content_id": mid,
                        "content_type": "note" if self.platform == "xhs" else "video",
                        "url": params.get("base_url") or f"https://example.com/{self.platform}/{mid}",
                        "title": f"DEMO {self.platform} 内容 {i+1}",
                        "description": f"mock content for {mid}",
                        "published_at": now.isoformat() + "Z",
                        "source": params.get("keyword") or params.get("source") or "mock",
                    }
                )
                snapshots.append(
                    {
                        "platform_content_id": mid,
                        "captured_at": now.isoformat() + "Z",
                        "like_count": 10 + i,
                        "comment_count": 2 + i,
                        "share_count": 1,
                        "collect_count": 3,
                        "view_count": 100 + i * 5,
                    }
                )
            mock["contents"] = contents
            mock["content_snapshots"] = snapshots

        if job_type == "profile_metrics":
            profiles = params.get("profiles") or []
            if not isinstance(profiles, list):
                profiles = []
            if not profiles:
                profiles = [{"sec_uid": "demo_sec_uid"}]
            mock["profile_snapshots"] = [
                {
                    "sec_uid": str(p.get("sec_uid") or "demo_sec_uid"),
                    "captured_at": now.isoformat() + "Z",
                    "fans": 1000,
                    "follows": 10,
                    "interaction": 666,
                    "contents_count": 12,
                }
                for p in profiles[:50]
            ]

        if job_type == "comment_sync":
            ids = gen_media_ids()
            comments = []
            for i, mid in enumerate(ids):
                for j in range(2):
                    comments.append(
                        {
                            "platform_content_id": mid,
                            "platform_comment_id": f"c_{mid}_{j}",
                            "content": f"mock comment {j} for {mid}",
                            "nickname": f"user{j}",
                            "like_count": j,
                            "created_at_platform": now.isoformat() + "Z",
                        }
                    )
            mock["comments"] = comments

        return CrawlResult(
            contents_upserted=len(mock.get("contents", [])),
            content_snapshots=len(mock.get("content_snapshots", [])),
            profile_snapshots=len(mock.get("profile_snapshots", [])),
            comments_upserted=len(mock.get("comments", [])),
            raw=mock,
        )


def get_crawler(platform: str) -> Crawler:
    mode = getattr(settings, "marketing_crawler_mode", None) or "mock"
    mode = str(mode).strip().lower()
    if mode == "playwright":
        from server.marketing.crawlers_playwright import get_playwright_crawler

        return get_playwright_crawler(platform)

    p = (platform or "").lower().strip()
    if p in {"xhs", "xiaohongshu"}:
        return StubCrawler("xhs")
    if p in {"douyin", "dy"}:
        return StubCrawler("douyin")
    return StubCrawler(p or "unknown")

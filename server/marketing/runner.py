from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

from sqlmodel import select
from server.db import AsyncSessionLocal
from server.config import settings
from server.marketing.crawlers import get_crawler
from server.marketing.ingest import ingest_marketing_payload
from server.marketing.models import (
    MktJob,
    MktJobRun,
    MktTrackComment,
    MktTrackMedia,
)


async def run_job_async(job_id: int, run_id: int) -> None:
    """
    后台执行一个 job run。
    - 读取 job 定义
    - 调用 crawler（目前为 stub）
    - 更新 run 状态与 stats
    """

    async with AsyncSessionLocal() as session:
        job = await session.get(MktJob, job_id)
        run = await session.get(MktJobRun, run_id)
        if not job or not run:
            return

        try:
            # 为了让“完整流程可跑”，当 params 未指定目标时，自动从监控池取目标：
            params = dict(job.params or {})
            params.setdefault("headless", bool(getattr(settings, "marketing_playwright_headless", True)))
            params.setdefault("slow_mo_ms", int(getattr(settings, "marketing_playwright_slow_mo_ms", 0) or 0))
            if job.job_type in {"content_metrics", "comment_sync", "content_search"}:
                ids = params.get("platform_content_ids") or params.get("media_ids")
                if not ids:
                    if job.job_type == "comment_sync":
                        res = await session.exec(
                            select(MktTrackComment.platform_content_id, MktTrackComment.url, MktTrackComment.title).where(
                                (MktTrackComment.platform == job.platform) & (MktTrackComment.is_deleted == False)  # noqa: E712
                            )
                        )
                        rows = res.all()
                        ids = [r[0] for r in rows]
                        params["targets"] = [
                            {"platform_content_id": r[0], "url": r[1], "title": r[2], "source": None} for r in rows
                        ]
                    else:
                        res = await session.exec(
                            select(
                                MktTrackMedia.platform_content_id,
                                MktTrackMedia.url,
                                MktTrackMedia.title,
                                MktTrackMedia.source,
                            ).where(MktTrackMedia.platform == job.platform)
                        )
                        rows = res.all()
                        ids = [r[0] for r in rows]
                        params["targets"] = [
                            {"platform_content_id": r[0], "url": r[1], "title": r[2], "source": r[3]} for r in rows
                        ]
                    params["platform_content_ids"] = ids

            # 给 Playwright crawler 提供会话：取该平台最新一条 session（生产版会按账号池策略选择）
            if "session_data" not in params:
                from server.marketing.models import MktPlatformSession, MktPlatformProfile

                res = await session.exec(
                    select(MktPlatformSession.session_data)
                    .join(MktPlatformProfile, MktPlatformProfile.id == MktPlatformSession.profile_id)
                    .where(MktPlatformProfile.platform == job.platform)
                    .order_by(desc(MktPlatformSession.updated_at))
                    .limit(1)
                )
                row = res.first()
                if row:
                    params["session_data"] = row[0]

            crawler = get_crawler(job.platform)
            res = await crawler.run(job_type=job.job_type, params=params)

            raw = res.raw or {}
            if isinstance(raw, dict) and (raw.get("contents") or raw.get("content_snapshots") or raw.get("comments")):
                ingest_stats = await ingest_marketing_payload(
                    session=session,
                    platform=job.platform,
                    payload=raw,
                    ensure_track_media=True,
                )

            run.status = "success"
            run.finished_at = datetime.utcnow()
            run.stats = {
                "profiles_upserted": res.profiles_upserted,
                "contents_upserted": res.contents_upserted,
                "content_snapshots": res.content_snapshots,
                "profile_snapshots": res.profile_snapshots,
                "comments_upserted": res.comments_upserted,
                "ingest": ingest_stats if isinstance(raw, dict) else None,
                "raw": res.raw,
            }
        except Exception as e:
            run.status = "failed"
            run.finished_at = datetime.utcnow()
            run.error = str(e)

        session.add(run)
        await session.commit()


def launch_job(job_id: int, run_id: int) -> None:
    """
    在 FastAPI 请求线程里启动异步任务。
    """

    asyncio.create_task(run_job_async(job_id, run_id))

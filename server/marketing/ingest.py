from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlmodel import select

from server.marketing.models import (
    MktComment,
    MktContent,
    MktContentMetricSnapshot,
    MktTrackMedia,
)


async def ingest_marketing_payload(
    *,
    session,
    platform: str,
    payload: dict[str, Any],
    ensure_track_media: bool = True,
) -> dict[str, int]:
    """
    将 Local Agent/Runner 产出的内容、快照、评论写入数据库。
    payload 约定字段：
      - contents: list[dict]
      - content_snapshots: list[dict]
      - comments: list[dict]
    """

    now = datetime.utcnow().replace(microsecond=0)
    platform = (platform or "").strip().lower()

    content_id_by_platform_id: dict[str, int] = {}

    # upsert contents
    for c in payload.get("contents", []) or []:
        if not isinstance(c, dict):
            continue
        platform_content_id = str(c.get("platform_content_id") or "").strip()
        if not platform_content_id:
            continue

        stmt = select(MktContent).where(
            (MktContent.platform == platform) & (MktContent.platform_content_id == platform_content_id)
        )
        existing = (await session.exec(stmt)).first()
        if existing:
            existing.title = c.get("title") or existing.title
            existing.description = c.get("description") or existing.description
            existing.url = c.get("url") or existing.url
            existing.source = c.get("source") or existing.source
            existing.updated_at = now
            session.add(existing)
            await session.flush()
            content_id_by_platform_id[platform_content_id] = existing.id  # type: ignore[arg-type]
        else:
            item = MktContent(
                platform=platform,
                profile_id=None,
                platform_content_id=platform_content_id,
                content_type=c.get("content_type") or "content",
                url=c.get("url"),
                title=c.get("title"),
                description=c.get("description"),
                source=c.get("source"),
                raw=c,
                created_at=now,
                updated_at=now,
            )
            session.add(item)
            await session.flush()
            content_id_by_platform_id[platform_content_id] = item.id  # type: ignore[arg-type]

        if ensure_track_media:
            stmt = select(MktTrackMedia).where(
                (MktTrackMedia.platform == platform)
                & (MktTrackMedia.platform_content_id == platform_content_id)
            )
            tm = (await session.exec(stmt)).first()
            if not tm:
                tm = MktTrackMedia(
                    platform=platform,
                    platform_content_id=platform_content_id,
                    url=c.get("url"),
                    title=c.get("title"),
                    source=c.get("source"),
                    status=0,
                    created_at=now,
                    updated_at=now,
                )
                session.add(tm)
                await session.flush()

    # snapshots + update track media
    for s in payload.get("content_snapshots", []) or []:
        if not isinstance(s, dict):
            continue
        platform_content_id = str(s.get("platform_content_id") or "").strip()
        if not platform_content_id:
            continue
        content_id = content_id_by_platform_id.get(platform_content_id)
        if not content_id:
            stmt = select(MktContent.id).where(
                (MktContent.platform == platform) & (MktContent.platform_content_id == platform_content_id)
            )
            content_id = (await session.exec(stmt)).first()
        if not content_id:
            continue

        captured_at = now
        snap = MktContentMetricSnapshot(
            content_id=int(content_id),
            captured_at=captured_at,
            view_count=s.get("view_count"),
            like_count=s.get("like_count"),
            comment_count=s.get("comment_count"),
            share_count=s.get("share_count"),
            collect_count=s.get("collect_count"),
            metrics=s,
        )
        session.add(snap)
        try:
            await session.flush()
        except IntegrityError:
            await session.rollback()
            captured_at = captured_at.replace(second=(captured_at.second + 1) % 60)
            snap.captured_at = captured_at
            session.add(snap)
            await session.flush()

        stmt = select(MktTrackMedia).where(
            (MktTrackMedia.platform == platform) & (MktTrackMedia.platform_content_id == platform_content_id)
        )
        tm = (await session.exec(stmt)).first()
        if tm:
            tm.like_count = s.get("like_count")
            tm.comment_count = s.get("comment_count")
            tm.share_count = s.get("share_count")
            tm.collect_count = s.get("collect_count")
            tm.status = 1
            tm.last_track_at = now
            tm.updated_at = now
            session.add(tm)

    # comments
    comments_upserted = 0
    for c in payload.get("comments", []) or []:
        if not isinstance(c, dict):
            continue
        platform_content_id = str(c.get("platform_content_id") or "").strip()
        platform_comment_id = str(c.get("platform_comment_id") or "").strip()
        if not platform_content_id or not platform_comment_id:
            continue
        content_id = content_id_by_platform_id.get(platform_content_id)
        if not content_id:
            stmt = select(MktContent.id).where(
                (MktContent.platform == platform) & (MktContent.platform_content_id == platform_content_id)
            )
            content_id = (await session.exec(stmt)).first()
        if not content_id:
            continue

        stmt = select(MktComment).where(
            (MktComment.platform == platform) & (MktComment.platform_comment_id == platform_comment_id)
        )
        existing = (await session.exec(stmt)).first()
        if existing:
            continue
        cm = MktComment(
            platform=platform,
            content_id=int(content_id),
            platform_comment_id=platform_comment_id,
            parent_comment_id=c.get("parent_comment_id"),
            user_sec_uid=c.get("user_sec_uid"),
            nickname=c.get("nickname"),
            location=c.get("location"),
            content=c.get("content"),
            like_count=c.get("like_count"),
            sub_comment_count=c.get("sub_comment_count"),
            pictures=c.get("pictures"),
            created_at_platform=None,
            raw=c.get("raw") or c,
            created_at=now,
            updated_at=now,
        )
        session.add(cm)
        comments_upserted += 1

    await session.commit()

    return {
        "contents": len(payload.get("contents", []) or []),
        "content_snapshots": len(payload.get("content_snapshots", []) or []),
        "comments": comments_upserted,
    }


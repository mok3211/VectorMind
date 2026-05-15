from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, func, or_
from sqlmodel import select

from server.auth.deps import require_permission
from server.db import get_session
from server.logging_utils import get_logger
from server.marketing.models import (
    MktComment,
    MktContent,
    MktContentMetricSnapshot,
    MktInteractionRecord,
    MktLoginRun,
    MktJob,
    MktJobRun,
    MktPlatformProfile,
    MktPlatformSession,
    MktProfileMetricSnapshot,
    MktTrackComment,
    MktTrackMedia,
)
from server.marketing.session_format import SessionFormatError, normalize_marketing_session_v1
from server.marketing.runner import launch_job
from server.marketing.schemas import (
    JobCreate,
    ProfileCreate,
    ProfileUpdate,
    SessionImport,
    TrackCommentCreate,
    TrackMediaCreate,
    InteractionSendCommentRequest,
    QrLoginStartRequest,
    VideoSearchRequest,
    CreatorSearchRequest,
)
from server.marketing.login import create_qr_login, detect_logged_in
from server.marketing.search import search_creators, search_videos_with_page

logger = get_logger(__name__)


router = APIRouter(prefix="/api/marketing", tags=["marketing"])


def _as_int(v: Any) -> int | None:
    if v is None:
        return None
    if isinstance(v, bool):
        return int(v)
    if isinstance(v, int):
        return v
    if isinstance(v, float):
        return int(v)
    if isinstance(v, str):
        s = v.strip()
        if s == "":
            return None
        if s.isdigit() or (s.startswith("-") and s[1:].isdigit()):
            return int(s)
    return None


def _parse_platform_dt(v: Any) -> datetime | None:
    iv = _as_int(v)
    if iv is None:
        return None
    if iv > 10_000_000_000:
        iv = int(iv / 1000)
    if iv <= 0:
        return None
    try:
        return datetime.utcfromtimestamp(iv)
    except Exception:
        return None


def _normalize_pagination(*, page: int | None, page_size: int | None, limit: int | None) -> tuple[int, int, int]:
    if page_size is None and limit is not None:
        page_size = int(limit)
    if page_size is None:
        page_size = 20
    page_size = int(page_size)
    if page_size not in {20, 50, 100}:
        raise HTTPException(status_code=400, detail="page_size 仅支持 20/50/100")
    if page is None:
        page = 1
    page = max(1, int(page))
    offset = (page - 1) * page_size
    return page, page_size, offset


def _normalize_item(d: dict[str, Any]) -> dict[str, Any]:
    for k in (
        "source_type",
        "type",
        "liked_count",
        "comment_count",
        "share_count",
        "collected_count",
        "collect_count",
        "status",
        "track_status",
    ):
        if k in d:
            iv = _as_int(d.get(k))
            if iv is not None:
                d[k] = iv
    return d


def _dump(item: Any) -> dict[str, Any]:
    return _normalize_item(item.model_dump())


@router.get("/profiles")
async def list_profiles(
    platform: str | None = None,
    profile_type: str | None = None,
    sec_uid: str | None = None,
    nickname: str | None = None,
    status: str | None = None,
    risk_status: str | None = None,
    page: int | None = 1,
    page_size: int | None = 20,
    limit: int | None = None,
    _: object = Depends(require_permission("marketing.view")),
    session=Depends(get_session),
):
    page, page_size, offset = _normalize_pagination(page=page, page_size=page_size, limit=limit)
    stmt = select(MktPlatformProfile)
    if platform:
        stmt = stmt.where(MktPlatformProfile.platform == platform)
    if profile_type:
        stmt = stmt.where(MktPlatformProfile.profile_type == profile_type)
    if sec_uid:
        stmt = stmt.where(MktPlatformProfile.sec_uid == sec_uid)
    if nickname:
        kw = nickname.strip()
        if kw:
            stmt = stmt.where(MktPlatformProfile.nickname.ilike(f"%{kw}%"))
    if status:
        stmt = stmt.where(MktPlatformProfile.status == status)
    if risk_status:
        stmt = stmt.where(MktPlatformProfile.risk_status == risk_status)

    count_stmt = select(func.count()).select_from(MktPlatformProfile)
    if platform:
        count_stmt = count_stmt.where(MktPlatformProfile.platform == platform)
    if profile_type:
        count_stmt = count_stmt.where(MktPlatformProfile.profile_type == profile_type)
    if sec_uid:
        count_stmt = count_stmt.where(MktPlatformProfile.sec_uid == sec_uid)
    if nickname and nickname.strip():
        count_stmt = count_stmt.where(MktPlatformProfile.nickname.ilike(f"%{nickname.strip()}%"))
    if status:
        count_stmt = count_stmt.where(MktPlatformProfile.status == status)
    if risk_status:
        count_stmt = count_stmt.where(MktPlatformProfile.risk_status == risk_status)
    total_row = (await session.exec(count_stmt)).one()
    total = int(total_row[0] if isinstance(total_row, tuple) else total_row)

    stmt = stmt.order_by(desc(MktPlatformProfile.updated_at)).offset(offset).limit(page_size)
    res = await session.exec(stmt)
    return {"items": [_dump(i) for i in res.all()], "total": total, "page": page, "page_size": page_size}


@router.post("/profiles")
async def create_profile(
    req: ProfileCreate,
    _: object = Depends(require_permission("marketing.manage")),
    session=Depends(get_session),
):
    item = MktPlatformProfile(**req.model_dump())
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return {"item": _dump(item)}


@router.put("/profiles/{profile_id}")
async def update_profile(
    profile_id: int,
    req: ProfileUpdate,
    _: object = Depends(require_permission("marketing.manage")),
    session=Depends(get_session),
):
    item = await session.get(MktPlatformProfile, profile_id)
    if not item:
        raise HTTPException(status_code=404, detail="not found")
    for k, v in req.model_dump(exclude_unset=True).items():
        setattr(item, k, v)
    item.updated_at = datetime.utcnow()
    session.add(item)
    await session.commit()
    return {"item": _dump(item)}


@router.get("/sessions")
async def list_sessions(
    profile_id: int | None = None,
    status: str | None = None,
    page: int | None = 1,
    page_size: int | None = 20,
    limit: int | None = None,
    _: object = Depends(require_permission("marketing.view")),
    session=Depends(get_session),
):
    page, page_size, offset = _normalize_pagination(page=page, page_size=page_size, limit=limit)
    stmt = select(MktPlatformSession)
    if profile_id:
        stmt = stmt.where(MktPlatformSession.profile_id == profile_id)
    if status:
        stmt = stmt.where(MktPlatformSession.status == status)

    count_stmt = select(func.count()).select_from(MktPlatformSession)
    if profile_id:
        count_stmt = count_stmt.where(MktPlatformSession.profile_id == profile_id)
    if status:
        count_stmt = count_stmt.where(MktPlatformSession.status == status)
    total_row = (await session.exec(count_stmt)).one()
    total = int(total_row[0] if isinstance(total_row, tuple) else total_row)

    stmt = stmt.order_by(desc(MktPlatformSession.updated_at)).offset(offset).limit(page_size)
    res = await session.exec(stmt)
    items = res.all()
    if not profile_id:
        seen: set[int] = set()
        deduped: list[MktPlatformSession] = []
        for it in items:
            pid = int(getattr(it, "profile_id") or 0)
            if pid and pid in seen:
                continue
            if pid:
                seen.add(pid)
            deduped.append(it)
        items = deduped
    return {"items": [_dump(i) for i in items], "total": total, "page": page, "page_size": page_size}


@router.post("/sessions/import")
async def import_session(
    req: SessionImport,
    _: object = Depends(require_permission("marketing.manage")),
    session=Depends(get_session),
):
    profile = await session.get(MktPlatformProfile, req.profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="profile not found")
    if (profile.profile_type or "").strip().lower() != "owned":
        raise HTTPException(status_code=400, detail="仅允许为自有账号（owned）导入会话")

    try:
        normalized = normalize_marketing_session_v1(
            req.session_data,
            fallback_platform=profile.platform,
            fallback_user_agent=req.user_agent,
        )
    except SessionFormatError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # 平台一致性：profile.platform 与 session_data.platform 必须一致
    if (profile.platform or "").lower().strip() != normalized.platform:
        raise HTTPException(status_code=400, detail="session_data.platform 与 profile.platform 不一致")

    item = MktPlatformSession(
        profile_id=req.profile_id,
        status="valid",
        user_agent=normalized.user_agent,
        session_data=normalized.session_data,
        expires_at=req.expires_at,
        last_validated_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return {"item": _dump(item), "warnings": normalized.warnings, "format": "MarketingSession v1"}


@router.post("/sessions/{session_id}/validate")
async def validate_session(
    session_id: int,
    _: object = Depends(require_permission("marketing.manage")),
    session=Depends(get_session),
):
    """真实校验（Playwright）：打开主页探测登录态（尽力而为）。"""

    item = await session.get(MktPlatformSession, session_id)
    if not item:
        raise HTTPException(status_code=404, detail="not found")
    profile = await session.get(MktPlatformProfile, item.profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="profile not found")

    # 真实校验：用 Playwright 带 cookie 打开首页
    try:
        from server.config import settings
        from server.marketing.playwright_client import new_context_from_marketing_session
        from playwright.async_api import async_playwright

        headless = bool(getattr(settings, "marketing_playwright_headless", True))
        slow_mo_ms = int(getattr(settings, "marketing_playwright_slow_mo_ms", 0) or 0)
        session_data = item.session_data or {}
        storage = session_data.get("storage") if isinstance(session_data, dict) else None
        user_data_dir = (storage.get("user_data_dir") if isinstance(storage, dict) else None) or ""
        user_data_dir = str(user_data_dir).strip()

        if user_data_dir:
            pw = await async_playwright().start()
            launch_kwargs: dict[str, Any] = {"headless": headless}
            if slow_mo_ms and slow_mo_ms > 0:
                launch_kwargs["slow_mo"] = int(slow_mo_ms)
            context = await pw.chromium.launch_persistent_context(user_data_dir=user_data_dir, **launch_kwargs)
            browser = None
        else:
            pw, browser, context = await new_context_from_marketing_session(
                session_data=session_data,
                headless=headless,
                slow_mo_ms=slow_mo_ms,
            )
        try:
            page = await context.new_page()
            url = "https://www.xiaohongshu.com/explore" if profile.platform == "xhs" else "https://www.douyin.com/"
            await page.goto(url, wait_until="domcontentloaded", timeout=60_000)
            maybe_logged_in, _meta = await detect_logged_in(profile.platform, page=page, context=context)
        finally:
            await context.close()
            if browser is not None:
                await browser.close()
            await pw.stop()
    except Exception as e:
        item.status = "invalid"
        item.last_error = str(e)
        item.last_validated_at = datetime.utcnow()
        item.updated_at = datetime.utcnow()
        session.add(item)
        await session.commit()
        return {"item": _dump(item), "validated": False, "detail": str(e)}

    item.status = "valid" if maybe_logged_in else "expired"
    item.last_error = None if maybe_logged_in else "可能未登录（页面包含登录提示）"
    item.last_validated_at = datetime.utcnow()
    item.updated_at = datetime.utcnow()
    session.add(item)
    await session.commit()
    return {"item": _dump(item), "validated": maybe_logged_in, "detail": "playwright"}


@router.post("/qr-login/start")
async def start_qr_login(
    req: QrLoginStartRequest,
    _: object = Depends(require_permission("marketing.manage")),
    session=Depends(get_session),
):
    profile = await session.get(MktPlatformProfile, req.profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="profile not found")
    if (profile.profile_type or "").strip().lower() != "owned":
        raise HTTPException(status_code=400, detail="仅允许为自有账号（owned）扫码登录")
    run = await create_qr_login(req.profile_id, timeout_sec=req.timeout_sec)
    return {"run": _dump(run)}


@router.get("/qr-login/{run_id}")
async def get_qr_login_run(
    run_id: int,
    _: object = Depends(require_permission("marketing.view")),
    session=Depends(get_session),
):
    item = await session.get(MktLoginRun, run_id)
    if not item:
        raise HTTPException(status_code=404, detail="not found")
    return {"run": _dump(item)}


async def _new_page_from_latest_session(platform: str, *, headless: bool, slow_mo_ms: int) -> Any:
    from server.marketing.models import MktPlatformProfile, MktPlatformSession
    from server import db

    async with db.AsyncSessionLocal() as s:
        res = await s.exec(
            select(MktPlatformSession)
            .join(MktPlatformProfile, MktPlatformProfile.id == MktPlatformSession.profile_id)
            .where(MktPlatformProfile.platform == platform)
            .where(MktPlatformProfile.profile_type == "owned")
            .order_by(desc(MktPlatformSession.updated_at))
            .limit(1)
        )
        sess = res.first()
        if not sess or not sess.session_data:
            raise HTTPException(status_code=400, detail=f"{platform} 暂无可用会话，请先在“会话”页扫码登录")
        session_data = sess.session_data

    storage = (session_data.get("storage") or {}) if isinstance(session_data, dict) else {}
    user_data_dir = (storage.get("user_data_dir") or "").strip() if isinstance(storage, dict) else ""

    from playwright.async_api import async_playwright

    pw = await async_playwright().start()
    launch_kwargs: dict[str, Any] = {"headless": headless}
    if slow_mo_ms and slow_mo_ms > 0:
        launch_kwargs["slow_mo"] = int(slow_mo_ms)
    if user_data_dir:
        context = await pw.chromium.launch_persistent_context(user_data_dir=user_data_dir, **launch_kwargs)
        page = await context.new_page()

        async def _cleanup() -> None:
            await context.close()
            await pw.stop()

        page.on("close", lambda: asyncio.create_task(_cleanup()))
        return page

    from server.marketing.playwright_client import new_context_from_marketing_session

    _pw, browser, context = await new_context_from_marketing_session(
        session_data=session_data, headless=headless, slow_mo_ms=slow_mo_ms
    )
    page = await context.new_page()

    async def _cleanup2() -> None:
        await context.close()
        await browser.close()
        await _pw.stop()

    page.on("close", lambda: asyncio.create_task(_cleanup2()))
    return page


@router.post("/search/videos")
async def search_videos(
    req: VideoSearchRequest,
    _: object = Depends(require_permission("marketing.view")),
    session=Depends(get_session),
):
    from server.config import settings

    headless = bool(req.headless) if req.headless is not None else bool(getattr(settings, "marketing_playwright_headless", True))
    slow_mo_ms = int(getattr(settings, "marketing_playwright_slow_mo_ms", 0) or 0)

    platform = (req.platform or "").strip().lower()
    logger.info("search_videos start platform=%s keyword=%s page=%s", platform, req.keyword, req.page)
    if platform == "xhs":
        sres = await session.exec(
            select(MktPlatformSession)
            .join(MktPlatformProfile, MktPlatformProfile.id == MktPlatformSession.profile_id)
            .where(MktPlatformProfile.platform == "xhs")
            .where(MktPlatformProfile.profile_type == "owned")
            .order_by(desc(MktPlatformSession.updated_at))
            .limit(1)
        )
        sess = sres.first()
        if not sess or not sess.session_data:
            raise HTTPException(status_code=400, detail="xhs 暂无可用会话，请先在“会话”页扫码登录")
        from server.marketing.noctua_web_api import xhs_search_notes

        try:
            items = await xhs_search_notes(
                session_data=sess.session_data,
                keyword=req.keyword,
                page=req.page,
                timeout_ms=req.timeout_ms,
            )
        except Exception as e:
            logger.exception("search_videos xhs failed keyword=%s", req.keyword)
            raise HTTPException(status_code=400, detail=str(e))
    else:
        async def new_page():
            return await _new_page_from_latest_session(platform, headless=headless, slow_mo_ms=slow_mo_ms)

        try:
            items = await search_videos_with_page(
                platform=platform,
                keyword=req.keyword,
                page=req.page,
                timeout_ms=req.timeout_ms,
                new_page=new_page,
            )
        except Exception as e:
            logger.exception("search_videos failed platform=%s keyword=%s", platform, req.keyword)
            raise HTTPException(status_code=400, detail=str(e))
    now = datetime.utcnow()
    for i in items:
        stmt = select(MktContent).where(MktContent.platform == i.platform).where(MktContent.platform_content_id == i.platform_content_id)
        res = await session.exec(stmt)
        existing = res.first()
        raw_data = json.dumps(i.raw or {}, ensure_ascii=False)
        xsec_token: str | None = None
        xsec_source: str | None = None
        model_type: str | None = None
        content_type: str | None = None
        description: str | None = None
        create_time: datetime | None = None
        liked_count: int | None = None
        comment_count: int | None = None
        share_count: int | None = None
        collected_count: int | None = None
        if isinstance(i.raw, dict):
            if i.platform == "xhs":
                xsec_token = (i.raw.get("xsec_token") or "").strip() or None
                xsec_source = "pc_search" if xsec_token else None
                model_type = (i.raw.get("model_type") or "").strip() or None
                content_type = (i.raw.get("type") or "").strip() or None
                description = i.raw.get("desc") or None
                create_time = _parse_platform_dt(i.raw.get("time") or i.raw.get("timestamp") or i.raw.get("create_time"))
                interact = i.raw.get("interact_info") or i.raw.get("interactInfo") or {}
                if isinstance(interact, dict):
                    liked_count = _as_int(interact.get("liked_count") or interact.get("like_count") or interact.get("digg_count"))
                    comment_count = _as_int(interact.get("comment_count"))
                    share_count = _as_int(interact.get("share_count"))
                    collected_count = _as_int(interact.get("collected_count") or interact.get("collect_count"))
            elif i.platform == "douyin":
                description = i.raw.get("desc") or description
                create_time = _parse_platform_dt(i.raw.get("create_time"))
                stats = i.raw.get("statistics") or {}
                if isinstance(stats, dict):
                    liked_count = _as_int(stats.get("digg_count") or stats.get("like_count"))
                    comment_count = _as_int(stats.get("comment_count"))
                    share_count = _as_int(stats.get("share_count"))
                    collected_count = _as_int(stats.get("collect_count"))
        content_row = None
        if existing:
            existing.media_code = i.platform
            existing.media_id = i.platform_content_id
            existing.url = i.url
            existing.title = i.title
            if description is not None:
                existing.description = description
            if content_type:
                existing.content_type = content_type
            if xsec_token:
                existing.xsec_token = xsec_token
                existing.xsec_source = xsec_source
            if model_type:
                existing.model_type = model_type
            existing.sec_uid = i.author_id
            existing.nickname = i.author_name
            existing.source = f"search:{req.keyword}"
            existing.create_time = existing.create_time or create_time or now
            if liked_count is not None:
                existing.liked_count = liked_count
            if comment_count is not None:
                existing.comment_count = comment_count
            if share_count is not None:
                existing.share_count = share_count
            if collected_count is not None:
                existing.collected_count = collected_count
            existing.raw = i.raw
            existing.raw_data = raw_data
            existing.updated_at = now
            session.add(existing)
            content_row = existing
        else:
            item = MktContent(
                platform=i.platform,
                platform_content_id=i.platform_content_id,
                media_code=i.platform,
                media_id=i.platform_content_id,
                url=i.url,
                title=i.title,
                description=description,
                xsec_token=xsec_token,
                xsec_source=xsec_source,
                model_type=model_type,
                content_type=content_type or "content",
                sec_uid=i.author_id,
                nickname=i.author_name,
                source=f"search:{req.keyword}",
                create_time=create_time or now,
                liked_count=liked_count or 0,
                comment_count=comment_count or 0,
                share_count=share_count or 0,
                collected_count=collected_count or 0,
                raw=i.raw,
                raw_data=raw_data,
                created_at=now,
                updated_at=now,
            )
            session.add(item)
            await session.flush()
            content_row = item

        if content_row and (liked_count is not None or comment_count is not None or share_count is not None or collected_count is not None):
            snap = MktContentMetricSnapshot(
                content_id=int(content_row.id),
                captured_at=datetime.utcnow(),
                view_count=None,
                like_count=liked_count,
                comment_count=comment_count,
                collect_count=collected_count,
                share_count=share_count,
                metrics={
                    "source": "search",
                    "platform": i.platform,
                    "platform_content_id": i.platform_content_id,
                },
            )
            session.add(snap)
    await session.commit()
    logger.info("search_videos done platform=%s keyword=%s results=%s", platform, req.keyword, len(items))
    return {
        "items": [
            {
                "platform": i.platform,
                "platform_content_id": i.platform_content_id,
                "url": i.url,
                "title": i.title,
                "author_name": i.author_name,
                "author_id": i.author_id,
                "author_url": i.author_url,
                "raw": i.raw,
            }
            for i in items
        ]
    }


@router.post("/search/creators")
async def search_creator_items(
    req: CreatorSearchRequest,
    _: object = Depends(require_permission("marketing.view")),
    session=Depends(get_session),
):
    from server.config import settings

    headless = bool(req.headless) if req.headless is not None else bool(getattr(settings, "marketing_playwright_headless", True))
    slow_mo_ms = int(getattr(settings, "marketing_playwright_slow_mo_ms", 0) or 0)

    platform = (req.platform or "").strip().lower()
    if platform == "xhs":
        sres = await session.exec(
            select(MktPlatformSession)
            .join(MktPlatformProfile, MktPlatformProfile.id == MktPlatformSession.profile_id)
            .where(MktPlatformProfile.platform == "xhs")
            .where(MktPlatformProfile.profile_type == "owned")
            .order_by(desc(MktPlatformSession.updated_at))
            .limit(1)
        )
        sess = sres.first()
        if not sess or not sess.session_data:
            raise HTTPException(status_code=400, detail="xhs 暂无可用会话，请先在“会话”页扫码登录")
        from server.marketing.noctua_web_api import xhs_search_notes
        from server.marketing.search import _creator_from_video

        try:
            videos = await xhs_search_notes(
                session_data=sess.session_data,
                keyword=req.keyword,
                page=req.page,
                timeout_ms=req.timeout_ms,
            )
            items = [c for c in (_creator_from_video(v) for v in videos) if c]
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
    else:
        async def new_page():
            return await _new_page_from_latest_session(platform, headless=headless, slow_mo_ms=slow_mo_ms)

        try:
            items = await search_creators(
                platform=platform,
                keyword=req.keyword,
                page=req.page,
                timeout_ms=req.timeout_ms,
                new_page=new_page,
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
    now = datetime.utcnow()
    for i in items:
        sec_uid = (i.sec_uid or i.platform_user_id or "").strip() if isinstance(i.sec_uid or i.platform_user_id, str) else (i.sec_uid or i.platform_user_id)
        sec_uid = (sec_uid or "").strip()
        if not sec_uid:
            continue
        user_link = (i.user_link or "").strip()
        if not user_link:
            user_link = (
                f"https://www.xiaohongshu.com/user/profile/{sec_uid}"
                if i.platform == "xhs"
                else f"https://www.douyin.com/user/{sec_uid}"
            )
        stmt = select(MktPlatformProfile).where(MktPlatformProfile.platform == i.platform).where(MktPlatformProfile.sec_uid == sec_uid)
        res = await session.exec(stmt)
        existing = res.first()
        raw_data = json.dumps(i.raw or {}, ensure_ascii=False)
        if existing:
            existing.profile_type = existing.profile_type or "competitor"
            existing.platform_user_id = i.platform_user_id or existing.platform_user_id
            existing.sec_uid = sec_uid
            existing.nickname = i.nickname or existing.nickname
            existing.user_link = user_link or existing.user_link
            existing.media_code = existing.media_code or i.platform
            existing.from_source = existing.from_source or 2
            existing.source_flags = existing.source_flags or 2
            existing.source = existing.source or f"search:{req.keyword}"
            existing.raw_data = raw_data
            existing.updated_at = now
            session.add(existing)
        else:
            item = MktPlatformProfile(
                platform=i.platform,
                profile_type="competitor",
                platform_user_id=i.platform_user_id,
                sec_uid=sec_uid,
                nickname=i.nickname,
                user_link=user_link,
                media_code=i.platform,
                from_source=2,
                source_flags=2,
                source=f"search:{req.keyword}",
                raw_data=raw_data,
                created_at=now,
                updated_at=now,
            )
            session.add(item)
    await session.commit()
    return {
        "items": [
            {
                "platform": i.platform,
                "platform_user_id": i.platform_user_id,
                "sec_uid": i.sec_uid or i.platform_user_id,
                "nickname": i.nickname,
                "user_link": i.user_link
                or (
                    f"https://www.xiaohongshu.com/user/profile/{(i.sec_uid or i.platform_user_id)}"
                    if i.platform == "xhs"
                    else f"https://www.douyin.com/user/{(i.sec_uid or i.platform_user_id)}"
                ),
                "raw": i.raw,
            }
            for i in items
        ]
    }


@router.get("/jobs")
async def list_jobs(
    platform: str | None = None,
    job_type: str | None = None,
    enabled: bool | None = None,
    page: int | None = 1,
    page_size: int | None = 20,
    limit: int | None = None,
    _: object = Depends(require_permission("marketing.view")),
    session=Depends(get_session),
):
    page, page_size, offset = _normalize_pagination(page=page, page_size=page_size, limit=limit)
    stmt = select(MktJob)
    if platform:
        stmt = stmt.where(MktJob.platform == platform)
    if job_type:
        stmt = stmt.where(MktJob.job_type == job_type)
    if enabled is not None:
        stmt = stmt.where(MktJob.enabled == enabled)

    count_stmt = select(func.count()).select_from(MktJob)
    if platform:
        count_stmt = count_stmt.where(MktJob.platform == platform)
    if job_type:
        count_stmt = count_stmt.where(MktJob.job_type == job_type)
    if enabled is not None:
        count_stmt = count_stmt.where(MktJob.enabled == enabled)
    total_row = (await session.exec(count_stmt)).one()
    total = int(total_row[0] if isinstance(total_row, tuple) else total_row)

    stmt = stmt.order_by(desc(MktJob.updated_at)).offset(offset).limit(page_size)
    res = await session.exec(stmt)
    return {"items": [i.model_dump() for i in res.all()], "total": total, "page": page, "page_size": page_size}


@router.post("/jobs")
async def create_job(
    req: JobCreate,
    user=Depends(require_permission("marketing.manage")),
    session=Depends(get_session),
):
    item = MktJob(**req.model_dump(), created_by_user_id=user.id)
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return {"item": item.model_dump()}


@router.post("/jobs/{job_id}/run")
async def run_job(
    job_id: int,
    _: object = Depends(require_permission("marketing.manage")),
    session=Depends(get_session),
):
    job = await session.get(MktJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="not found")

    run = MktJobRun(job_id=job_id, status="running", started_at=datetime.utcnow())
    session.add(run)
    await session.commit()
    await session.refresh(run)

    launch_job(job_id, run.id)
    return {"run": run.model_dump()}


@router.get("/job-runs")
async def list_job_runs(
    job_id: int | None = None,
    status: str | None = None,
    page: int | None = 1,
    page_size: int | None = 20,
    limit: int | None = None,
    _: object = Depends(require_permission("marketing.view")),
    session=Depends(get_session),
):
    page, page_size, offset = _normalize_pagination(page=page, page_size=page_size, limit=limit)
    stmt = select(MktJobRun)
    if job_id:
        stmt = stmt.where(MktJobRun.job_id == job_id)
    if status:
        stmt = stmt.where(MktJobRun.status == status)

    count_stmt = select(func.count()).select_from(MktJobRun)
    if job_id:
        count_stmt = count_stmt.where(MktJobRun.job_id == job_id)
    if status:
        count_stmt = count_stmt.where(MktJobRun.status == status)
    total_row = (await session.exec(count_stmt)).one()
    total = int(total_row[0] if isinstance(total_row, tuple) else total_row)

    stmt = stmt.order_by(desc(MktJobRun.started_at)).offset(offset).limit(page_size)
    res = await session.exec(stmt)
    return {"items": [i.model_dump() for i in res.all()], "total": total, "page": page, "page_size": page_size}


@router.get("/contents")
async def list_contents(
    platform: str | None = None,
    profile_id: int | None = None,
    platform_content_id: str | None = None,
    sec_uid: str | None = None,
    source: str | None = None,
    is_exported: int | None = None,
    is_comment: bool | None = None,
    keyword: str | None = None,
    page: int | None = 1,
    page_size: int | None = 20,
    limit: int | None = None,
    _: object = Depends(require_permission("marketing.view")),
    session=Depends(get_session),
):
    page, page_size, offset = _normalize_pagination(page=page, page_size=page_size, limit=limit)
    stmt = select(MktContent)
    if platform:
        stmt = stmt.where(MktContent.platform == platform)
    if profile_id:
        stmt = stmt.where(MktContent.profile_id == profile_id)
    if platform_content_id:
        stmt = stmt.where(MktContent.platform_content_id == platform_content_id)
    if sec_uid:
        stmt = stmt.where(MktContent.sec_uid == sec_uid)
    if source:
        stmt = stmt.where(MktContent.source.ilike(f"%{source.strip()}%"))
    if is_exported is not None:
        stmt = stmt.where(MktContent.is_exported == int(is_exported))
    if is_comment is not None:
        stmt = stmt.where(MktContent.is_comment == is_comment)
    if keyword and keyword.strip():
        kw = keyword.strip()
        stmt = stmt.where(
            or_(
                MktContent.title.ilike(f"%{kw}%"),
                MktContent.description.ilike(f"%{kw}%"),
                MktContent.source.ilike(f"%{kw}%"),
                MktContent.nickname.ilike(f"%{kw}%"),
            )
        )

    count_stmt = select(func.count()).select_from(MktContent)
    if platform:
        count_stmt = count_stmt.where(MktContent.platform == platform)
    if profile_id:
        count_stmt = count_stmt.where(MktContent.profile_id == profile_id)
    if platform_content_id:
        count_stmt = count_stmt.where(MktContent.platform_content_id == platform_content_id)
    if sec_uid:
        count_stmt = count_stmt.where(MktContent.sec_uid == sec_uid)
    if source:
        count_stmt = count_stmt.where(MktContent.source.ilike(f"%{source.strip()}%"))
    if is_exported is not None:
        count_stmt = count_stmt.where(MktContent.is_exported == int(is_exported))
    if is_comment is not None:
        count_stmt = count_stmt.where(MktContent.is_comment == is_comment)
    if keyword and keyword.strip():
        kw = keyword.strip()
        count_stmt = count_stmt.where(
            or_(
                MktContent.title.ilike(f"%{kw}%"),
                MktContent.description.ilike(f"%{kw}%"),
                MktContent.source.ilike(f"%{kw}%"),
                MktContent.nickname.ilike(f"%{kw}%"),
            )
        )
    total_row = (await session.exec(count_stmt)).one()
    total = int(total_row[0] if isinstance(total_row, tuple) else total_row)

    stmt = stmt.order_by(desc(MktContent.updated_at)).offset(offset).limit(page_size)
    res = await session.exec(stmt)
    return {"items": [_dump(i) for i in res.all()], "total": total, "page": page, "page_size": page_size}


@router.get("/contents/{content_id}/metrics")
async def list_content_metrics(
    content_id: int,
    page: int | None = 1,
    page_size: int | None = 20,
    limit: int | None = None,
    _: object = Depends(require_permission("marketing.view")),
    session=Depends(get_session),
):
    page, page_size, offset = _normalize_pagination(page=page, page_size=page_size, limit=limit)
    count_stmt = select(func.count()).select_from(MktContentMetricSnapshot).where(
        MktContentMetricSnapshot.content_id == content_id
    )
    total_row = (await session.exec(count_stmt)).one()
    total = int(total_row[0] if isinstance(total_row, tuple) else total_row)
    stmt = (
        select(MktContentMetricSnapshot)
        .where(MktContentMetricSnapshot.content_id == content_id)
        .order_by(desc(MktContentMetricSnapshot.captured_at))
        .offset(offset)
        .limit(page_size)
    )
    res = await session.exec(stmt)
    return {"items": [_dump(i) for i in res.all()], "total": total, "page": page, "page_size": page_size}


@router.get("/profiles/{profile_id}/metrics")
async def list_profile_metrics(
    profile_id: int,
    page: int | None = 1,
    page_size: int | None = 20,
    limit: int | None = None,
    _: object = Depends(require_permission("marketing.view")),
    session=Depends(get_session),
):
    page, page_size, offset = _normalize_pagination(page=page, page_size=page_size, limit=limit)
    count_stmt = select(func.count()).select_from(MktProfileMetricSnapshot).where(
        MktProfileMetricSnapshot.profile_id == profile_id
    )
    total_row = (await session.exec(count_stmt)).one()
    total = int(total_row[0] if isinstance(total_row, tuple) else total_row)
    stmt = (
        select(MktProfileMetricSnapshot)
        .where(MktProfileMetricSnapshot.profile_id == profile_id)
        .order_by(desc(MktProfileMetricSnapshot.captured_at))
        .offset(offset)
        .limit(page_size)
    )
    res = await session.exec(stmt)
    return {"items": [_dump(i) for i in res.all()], "total": total, "page": page, "page_size": page_size}


@router.get("/comments")
async def list_comments(
    content_id: int | None = None,
    platform: str | None = None,
    platform_comment_id: str | None = None,
    keyword: str | None = None,
    page: int | None = 1,
    page_size: int | None = 20,
    limit: int | None = None,
    _: object = Depends(require_permission("marketing.view")),
    session=Depends(get_session),
):
    page, page_size, offset = _normalize_pagination(page=page, page_size=page_size, limit=limit)
    stmt = select(MktComment)
    if content_id:
        stmt = stmt.where(MktComment.content_id == content_id)
    if platform:
        stmt = stmt.where(MktComment.platform == platform)
    if platform_comment_id:
        stmt = stmt.where(MktComment.platform_comment_id == platform_comment_id)
    if keyword and keyword.strip():
        kw = keyword.strip()
        stmt = stmt.where(or_(MktComment.nickname.ilike(f"%{kw}%"), MktComment.content.ilike(f"%{kw}%")))

    count_stmt = select(func.count()).select_from(MktComment)
    if content_id:
        count_stmt = count_stmt.where(MktComment.content_id == content_id)
    if platform:
        count_stmt = count_stmt.where(MktComment.platform == platform)
    if platform_comment_id:
        count_stmt = count_stmt.where(MktComment.platform_comment_id == platform_comment_id)
    if keyword and keyword.strip():
        kw = keyword.strip()
        count_stmt = count_stmt.where(or_(MktComment.nickname.ilike(f"%{kw}%"), MktComment.content.ilike(f"%{kw}%")))
    total_row = (await session.exec(count_stmt)).one()
    total = int(total_row[0] if isinstance(total_row, tuple) else total_row)

    stmt = stmt.order_by(desc(MktComment.created_at)).offset(offset).limit(page_size)
    res = await session.exec(stmt)
    return {"items": [_dump(i) for i in res.all()], "total": total, "page": page, "page_size": page_size}


@router.get("/track-media")
async def list_track_media(
    platform: str | None = None,
    is_comment: bool | None = None,
    status: int | None = None,
    keyword: str | None = None,
    source: str | None = None,
    url: str | None = None,
    platform_content_id: str | None = None,
    source_type: int | None = None,
    liked_min: int | None = None,
    comment_min: int | None = None,
    collected_min: int | None = None,
    page: int | None = 1,
    page_size: int | None = 20,
    limit: int | None = None,
    _: object = Depends(require_permission("marketing.view")),
    session=Depends(get_session),
):
    page, page_size, offset = _normalize_pagination(page=page, page_size=page_size, limit=limit)
    stmt = select(MktTrackMedia)
    if platform:
        stmt = stmt.where(MktTrackMedia.platform == platform)
    if is_comment is not None:
        stmt = stmt.where(MktTrackMedia.is_comment == is_comment)
    if status is not None:
        stmt = stmt.where(MktTrackMedia.status == status)
    if platform_content_id:
        stmt = stmt.where(MktTrackMedia.platform_content_id == platform_content_id)
    if source_type is not None:
        stmt = stmt.where(MktTrackMedia.source_type == int(source_type))
    if url and url.strip():
        stmt = stmt.where(MktTrackMedia.url.ilike(f"%{url.strip()}%"))
    if source and source.strip():
        stmt = stmt.where(MktTrackMedia.source.ilike(f"%{source.strip()}%"))
    if keyword and keyword.strip():
        kw = keyword.strip()
        stmt = stmt.where(or_(MktTrackMedia.title.ilike(f"%{kw}%"), MktTrackMedia.keyword.ilike(f"%{kw}%")))
    if liked_min is not None:
        stmt = stmt.where(MktTrackMedia.like_count >= int(liked_min))
    if comment_min is not None:
        stmt = stmt.where(MktTrackMedia.comment_count >= int(comment_min))
    if collected_min is not None:
        stmt = stmt.where(MktTrackMedia.collect_count >= int(collected_min))

    count_stmt = select(func.count()).select_from(MktTrackMedia)
    if platform:
        count_stmt = count_stmt.where(MktTrackMedia.platform == platform)
    if is_comment is not None:
        count_stmt = count_stmt.where(MktTrackMedia.is_comment == is_comment)
    if status is not None:
        count_stmt = count_stmt.where(MktTrackMedia.status == status)
    if platform_content_id:
        count_stmt = count_stmt.where(MktTrackMedia.platform_content_id == platform_content_id)
    if source_type is not None:
        count_stmt = count_stmt.where(MktTrackMedia.source_type == int(source_type))
    if url and url.strip():
        count_stmt = count_stmt.where(MktTrackMedia.url.ilike(f"%{url.strip()}%"))
    if source and source.strip():
        count_stmt = count_stmt.where(MktTrackMedia.source.ilike(f"%{source.strip()}%"))
    if keyword and keyword.strip():
        kw = keyword.strip()
        count_stmt = count_stmt.where(or_(MktTrackMedia.title.ilike(f"%{kw}%"), MktTrackMedia.keyword.ilike(f"%{kw}%")))
    if liked_min is not None:
        count_stmt = count_stmt.where(MktTrackMedia.like_count >= int(liked_min))
    if comment_min is not None:
        count_stmt = count_stmt.where(MktTrackMedia.comment_count >= int(comment_min))
    if collected_min is not None:
        count_stmt = count_stmt.where(MktTrackMedia.collect_count >= int(collected_min))
    total_row = (await session.exec(count_stmt)).one()
    total = int(total_row[0] if isinstance(total_row, tuple) else total_row)

    stmt = stmt.order_by(desc(MktTrackMedia.updated_at)).offset(offset).limit(page_size)
    res = await session.exec(stmt)
    return {"items": [_dump(i) for i in res.all()], "total": total, "page": page, "page_size": page_size}


@router.post("/track-media")
async def create_track_media(
    req: TrackMediaCreate,
    _: object = Depends(require_permission("marketing.manage")),
    session=Depends(get_session),
):
    data = req.model_dump()
    scope = (data.pop("source_type", None) or "external").strip().lower()
    data["source_scope"] = scope
    data["source_type"] = 1 if scope in {"internal", "1"} else 2
    data["media_code"] = data.get("platform")
    data["media_id"] = data.get("platform_content_id")
    data["platform_name"] = "xiaohongshu" if data.get("platform") == "xhs" else ("douyin" if data.get("platform") == "douyin" else None)
    if not data.get("create_time"):
        data["create_time"] = datetime.utcnow()
    data["update_time"] = datetime.utcnow()

    stmt = (
        select(MktContent)
        .where(MktContent.platform == data["platform"])
        .where(MktContent.platform_content_id == data["platform_content_id"])
    )
    res = await session.exec(stmt)
    content = res.first()
    if content:
        content.media_code = data["platform"]
        content.media_id = data["platform_content_id"]
        content.url = data.get("url") or content.url
        content.title = data.get("title") or content.title
        content.sec_uid = data.get("sec_uid") or content.sec_uid
        content.nickname = data.get("nickname") or content.nickname
        content.source = data.get("source") or content.source
        content.updated_at = datetime.utcnow()
        session.add(content)
        await session.commit()
    else:
        content = MktContent(
            platform=data["platform"],
            platform_content_id=data["platform_content_id"],
            media_code=data["platform"],
            media_id=data["platform_content_id"],
            url=data.get("url"),
            title=data.get("title"),
            sec_uid=data.get("sec_uid"),
            nickname=data.get("nickname"),
            source=data.get("source"),
            create_time=data.get("create_time"),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        session.add(content)
        await session.commit()
        await session.refresh(content)

    data["content_id"] = content.id
    stmt = (
        select(MktTrackMedia)
        .where(MktTrackMedia.platform == data["platform"])
        .where(MktTrackMedia.platform_content_id == data["platform_content_id"])
    )
    res = await session.exec(stmt)
    item = res.first()
    if item:
        for k, v in data.items():
            setattr(item, k, v)
        item.updated_at = datetime.utcnow()
        session.add(item)
        await session.commit()
        await session.refresh(item)
        return {"item": _dump(item), "upserted": True}

    item = MktTrackMedia(**data)
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return {"item": _dump(item), "upserted": False}


@router.put("/track-media/{item_id}/toggle-comment")
async def toggle_track_media_comment(
    item_id: int,
    enable: bool = True,
    _: object = Depends(require_permission("marketing.manage")),
    session=Depends(get_session),
):
    item = await session.get(MktTrackMedia, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="not found")
    item.is_comment = enable
    item.updated_at = datetime.utcnow()
    session.add(item)
    await session.commit()
    return {"item": _dump(item)}


@router.get("/track-comments")
async def list_track_comments(
    platform: str | None = None,
    track_status: int | None = None,
    is_deleted: bool | None = None,
    media_id: str | None = None,
    keyword: str | None = None,
    user_nickname: str | None = None,
    page: int | None = 1,
    page_size: int | None = 20,
    limit: int | None = None,
    _: object = Depends(require_permission("marketing.view")),
    session=Depends(get_session),
):
    page, page_size, offset = _normalize_pagination(page=page, page_size=page_size, limit=limit)
    stmt = select(MktTrackComment)
    if platform:
        stmt = stmt.where(MktTrackComment.platform == platform)
    if track_status is not None:
        stmt = stmt.where(MktTrackComment.track_status == track_status)
    if is_deleted is not None:
        stmt = stmt.where(MktTrackComment.is_deleted == is_deleted)
    if media_id:
        stmt = stmt.where(MktTrackComment.platform_content_id == media_id)
    if user_nickname and user_nickname.strip():
        stmt = stmt.where(MktTrackComment.user_nickname.ilike(f"%{user_nickname.strip()}%"))
    if keyword and keyword.strip():
        kw = keyword.strip()
        stmt = stmt.where(or_(MktTrackComment.title.ilike(f"%{kw}%"), MktTrackComment.user_nickname.ilike(f"%{kw}%")))

    count_stmt = select(func.count()).select_from(MktTrackComment)
    if platform:
        count_stmt = count_stmt.where(MktTrackComment.platform == platform)
    if track_status is not None:
        count_stmt = count_stmt.where(MktTrackComment.track_status == track_status)
    if is_deleted is not None:
        count_stmt = count_stmt.where(MktTrackComment.is_deleted == is_deleted)
    if media_id:
        count_stmt = count_stmt.where(MktTrackComment.platform_content_id == media_id)
    if user_nickname and user_nickname.strip():
        count_stmt = count_stmt.where(MktTrackComment.user_nickname.ilike(f"%{user_nickname.strip()}%"))
    if keyword and keyword.strip():
        kw = keyword.strip()
        count_stmt = count_stmt.where(or_(MktTrackComment.title.ilike(f"%{kw}%"), MktTrackComment.user_nickname.ilike(f"%{kw}%")))
    total_row = (await session.exec(count_stmt)).one()
    total = int(total_row[0] if isinstance(total_row, tuple) else total_row)

    stmt = stmt.order_by(desc(MktTrackComment.updated_at)).offset(offset).limit(page_size)
    res = await session.exec(stmt)
    return {"items": [_dump(i) for i in res.all()], "total": total, "page": page, "page_size": page_size}


@router.post("/track-comments")
async def create_track_comment(
    req: TrackCommentCreate,
    _: object = Depends(require_permission("marketing.manage")),
    session=Depends(get_session),
):
    data = req.model_dump()
    data["media_code"] = data.get("platform")
    data["media_id"] = data.get("platform_content_id")
    if not data.get("create_time"):
        data["create_time"] = datetime.utcnow()

    stmt = (
        select(MktTrackComment)
        .where(MktTrackComment.platform == data["platform"])
        .where(MktTrackComment.platform_content_id == data["platform_content_id"])
        .where(MktTrackComment.is_deleted == False)
    )
    if data.get("user_nickname"):
        stmt = stmt.where(MktTrackComment.user_nickname == data["user_nickname"])
    if data.get("title"):
        stmt = stmt.where(MktTrackComment.title == data["title"])
    res = await session.exec(stmt)
    item = res.first()
    if item:
        for k, v in data.items():
            setattr(item, k, v)
        item.updated_at = datetime.utcnow()
        session.add(item)
        await session.commit()
        await session.refresh(item)
        return {"item": _dump(item), "upserted": True}

    item = MktTrackComment(**data)
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return {"item": _dump(item), "upserted": False}


@router.delete("/track-comments/{item_id}")
async def delete_track_comment(
    item_id: int,
    _: object = Depends(require_permission("marketing.manage")),
    session=Depends(get_session),
):
    item = await session.get(MktTrackComment, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="not found")
    item.is_deleted = True
    item.updated_at = datetime.utcnow()
    session.add(item)
    await session.commit()
    return {"ok": True}


@router.get("/interaction-records")
async def list_interaction_records(
    platform: str | None = None,
    event_type: str | None = None,
    status: bool | None = None,
    keyword: str | None = None,
    page: int | None = 1,
    page_size: int | None = 20,
    limit: int | None = None,
    _: object = Depends(require_permission("marketing.view")),
    session=Depends(get_session),
):
    page, page_size, offset = _normalize_pagination(page=page, page_size=page_size, limit=limit)
    stmt = select(MktInteractionRecord)
    if platform:
        stmt = stmt.where(MktInteractionRecord.platform == platform)
    if event_type:
        stmt = stmt.where(MktInteractionRecord.event_type == event_type)
    if status is not None:
        stmt = stmt.where(MktInteractionRecord.status == status)
    if keyword and keyword.strip():
        kw = keyword.strip()
        stmt = stmt.where(or_(MktInteractionRecord.target.ilike(f"%{kw}%"), MktInteractionRecord.reason.ilike(f"%{kw}%")))

    count_stmt = select(func.count()).select_from(MktInteractionRecord)
    if platform:
        count_stmt = count_stmt.where(MktInteractionRecord.platform == platform)
    if event_type:
        count_stmt = count_stmt.where(MktInteractionRecord.event_type == event_type)
    if status is not None:
        count_stmt = count_stmt.where(MktInteractionRecord.status == status)
    if keyword and keyword.strip():
        kw = keyword.strip()
        count_stmt = count_stmt.where(or_(MktInteractionRecord.target.ilike(f"%{kw}%"), MktInteractionRecord.reason.ilike(f"%{kw}%")))
    total_row = (await session.exec(count_stmt)).one()
    total = int(total_row[0] if isinstance(total_row, tuple) else total_row)

    stmt = stmt.order_by(desc(MktInteractionRecord.created_at)).offset(offset).limit(page_size)
    res = await session.exec(stmt)
    return {"items": [i.model_dump() for i in res.all()], "total": total, "page": page, "page_size": page_size}


@router.post("/send-comment")
async def send_comment(
    req: InteractionSendCommentRequest,
    _: object = Depends(require_permission("marketing.manage")),
    session=Depends(get_session),
):
    """
    真实发送评论（Playwright UI）。
    成功/失败都会写入 mkt_interaction_records。
    """

    platform = (req.platform or "").strip().lower()
    url = (req.url or "").strip() or None
    platform_content_id = (req.platform_content_id or "").strip() or None

    track = None
    if req.track_media_id:
        track = await session.get(MktTrackMedia, req.track_media_id)
        if not track:
            raise HTTPException(status_code=404, detail="track_media not found")
        platform = (track.platform or "").strip().lower()
        url = (track.url or "").strip() or url
        platform_content_id = (track.platform_content_id or "").strip() or platform_content_id

    if platform not in {"xhs", "douyin"}:
        raise HTTPException(status_code=400, detail="platform 仅支持 xhs/douyin")
    if not url:
        raise HTTPException(status_code=400, detail="缺少 url（请在监控池里补齐 URL）")
    if not req.text or not req.text.strip():
        raise HTTPException(status_code=400, detail="text 不能为空")

    # 选取该平台最新 session（后续按账号池策略）
    res = await session.exec(
        select(MktPlatformSession.session_data)
        .join(MktPlatformProfile, MktPlatformProfile.id == MktPlatformSession.profile_id)
        .where(MktPlatformProfile.platform == platform)
        .where(MktPlatformProfile.profile_type == "owned")
        .order_by(desc(MktPlatformSession.updated_at))
        .limit(1)
    )
    row = res.first()
    if not row or not row[0]:
        raise HTTPException(status_code=400, detail="未找到可用 session，请先导入会话")

    from server.marketing.interactions_playwright import send_comment_douyin, send_comment_xhs

    if platform == "xhs":
        result = await send_comment_xhs(
            url=url,
            session_data=row[0],
            text=req.text,
            headless=req.headless,
            slow_mo_ms=req.slow_mo_ms,
        )
    else:
        result = await send_comment_douyin(
            url=url,
            session_data=row[0],
            text=req.text,
            headless=req.headless,
            slow_mo_ms=req.slow_mo_ms,
        )

    record = MktInteractionRecord(
        platform=platform,
        event_type="send_comment",
        account_profile_id=req.account_profile_id,
        target=platform_content_id or url,
        payload=req.text,
        source=track.title if track and track.title else None,
        status=bool(result.ok),
        reason=None if result.ok else (result.detail or "failed"),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    session.add(record)
    await session.commit()

    return {"ok": result.ok, "detail": result.detail, "record": record.model_dump()}

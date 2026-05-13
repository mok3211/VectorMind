from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc
from sqlmodel import select

from server.auth.deps import require_permission
from server.db import get_session
from server.marketing.models import (
    MktComment,
    MktContent,
    MktContentMetricSnapshot,
    MktInteractionRecord,
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
)


router = APIRouter(prefix="/api/marketing", tags=["marketing"])


@router.get("/profiles")
async def list_profiles(
    platform: str | None = None,
    profile_type: str | None = None,
    limit: int = 200,
    _: object = Depends(require_permission("marketing.view")),
    session=Depends(get_session),
):
    stmt = select(MktPlatformProfile).order_by(desc(MktPlatformProfile.updated_at)).limit(min(limit, 500))
    if platform:
        stmt = stmt.where(MktPlatformProfile.platform == platform)
    if profile_type:
        stmt = stmt.where(MktPlatformProfile.profile_type == profile_type)
    res = await session.exec(stmt)
    return {"items": [i.model_dump() for i in res.all()]}


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
    return {"item": item.model_dump()}


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
    return {"item": item.model_dump()}


@router.get("/sessions")
async def list_sessions(
    profile_id: int | None = None,
    limit: int = 200,
    _: object = Depends(require_permission("marketing.view")),
    session=Depends(get_session),
):
    stmt = select(MktPlatformSession).order_by(desc(MktPlatformSession.updated_at)).limit(min(limit, 500))
    if profile_id:
        stmt = stmt.where(MktPlatformSession.profile_id == profile_id)
    res = await session.exec(stmt)
    return {"items": [i.model_dump() for i in res.all()]}


@router.post("/sessions/import")
async def import_session(
    req: SessionImport,
    _: object = Depends(require_permission("marketing.manage")),
    session=Depends(get_session),
):
    profile = await session.get(MktPlatformProfile, req.profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="profile not found")

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
    return {"item": item.model_dump(), "warnings": normalized.warnings, "format": "MarketingSession v1"}


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

        pw, browser, context = await new_context_from_marketing_session(
            session_data=item.session_data or {},
            headless=bool(getattr(settings, "marketing_playwright_headless", True)),
            slow_mo_ms=int(getattr(settings, "marketing_playwright_slow_mo_ms", 0) or 0),
        )
        try:
            page = await context.new_page()
            url = "https://www.xiaohongshu.com/explore" if profile.platform == "xhs" else "https://www.douyin.com/"
            await page.goto(url, wait_until="domcontentloaded", timeout=60_000)
            html = (await page.content()).lower()
            # 极简判断：出现“登录”且没有明显用户入口时，视为可能未登录（不保证 100%）
            maybe_logged_in = "登录" not in html
        finally:
            await context.close()
            await browser.close()
            await pw.stop()
    except Exception as e:
        item.status = "invalid"
        item.last_error = str(e)
        item.last_validated_at = datetime.utcnow()
        item.updated_at = datetime.utcnow()
        session.add(item)
        await session.commit()
        return {"item": item.model_dump(), "validated": False, "detail": str(e)}

    item.status = "valid" if maybe_logged_in else "expired"
    item.last_error = None if maybe_logged_in else "可能未登录（页面包含登录提示）"
    item.last_validated_at = datetime.utcnow()
    item.updated_at = datetime.utcnow()
    session.add(item)
    await session.commit()
    return {"item": item.model_dump(), "validated": maybe_logged_in, "detail": "playwright"}


@router.get("/jobs")
async def list_jobs(
    platform: str | None = None,
    enabled: bool | None = None,
    limit: int = 200,
    _: object = Depends(require_permission("marketing.view")),
    session=Depends(get_session),
):
    stmt = select(MktJob).order_by(desc(MktJob.updated_at)).limit(min(limit, 500))
    if platform:
        stmt = stmt.where(MktJob.platform == platform)
    if enabled is not None:
        stmt = stmt.where(MktJob.enabled == enabled)
    res = await session.exec(stmt)
    return {"items": [i.model_dump() for i in res.all()]}


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
    limit: int = 200,
    _: object = Depends(require_permission("marketing.view")),
    session=Depends(get_session),
):
    stmt = select(MktJobRun).order_by(desc(MktJobRun.started_at)).limit(min(limit, 500))
    if job_id:
        stmt = stmt.where(MktJobRun.job_id == job_id)
    res = await session.exec(stmt)
    return {"items": [i.model_dump() for i in res.all()]}


@router.get("/contents")
async def list_contents(
    platform: str | None = None,
    profile_id: int | None = None,
    limit: int = 200,
    _: object = Depends(require_permission("marketing.view")),
    session=Depends(get_session),
):
    stmt = select(MktContent).order_by(desc(MktContent.updated_at)).limit(min(limit, 500))
    if platform:
        stmt = stmt.where(MktContent.platform == platform)
    if profile_id:
        stmt = stmt.where(MktContent.profile_id == profile_id)
    res = await session.exec(stmt)
    return {"items": [i.model_dump() for i in res.all()]}


@router.get("/contents/{content_id}/metrics")
async def list_content_metrics(
    content_id: int,
    limit: int = 200,
    _: object = Depends(require_permission("marketing.view")),
    session=Depends(get_session),
):
    stmt = (
        select(MktContentMetricSnapshot)
        .where(MktContentMetricSnapshot.content_id == content_id)
        .order_by(desc(MktContentMetricSnapshot.captured_at))
        .limit(min(limit, 500))
    )
    res = await session.exec(stmt)
    return {"items": [i.model_dump() for i in res.all()]}


@router.get("/profiles/{profile_id}/metrics")
async def list_profile_metrics(
    profile_id: int,
    limit: int = 200,
    _: object = Depends(require_permission("marketing.view")),
    session=Depends(get_session),
):
    stmt = (
        select(MktProfileMetricSnapshot)
        .where(MktProfileMetricSnapshot.profile_id == profile_id)
        .order_by(desc(MktProfileMetricSnapshot.captured_at))
        .limit(min(limit, 500))
    )
    res = await session.exec(stmt)
    return {"items": [i.model_dump() for i in res.all()]}


@router.get("/comments")
async def list_comments(
    content_id: int | None = None,
    limit: int = 200,
    _: object = Depends(require_permission("marketing.view")),
    session=Depends(get_session),
):
    stmt = select(MktComment).order_by(desc(MktComment.created_at)).limit(min(limit, 500))
    if content_id:
        stmt = stmt.where(MktComment.content_id == content_id)
    res = await session.exec(stmt)
    return {"items": [i.model_dump() for i in res.all()]}


@router.get("/track-media")
async def list_track_media(
    platform: str | None = None,
    is_comment: bool | None = None,
    status: int | None = None,
    limit: int = 200,
    _: object = Depends(require_permission("marketing.view")),
    session=Depends(get_session),
):
    stmt = select(MktTrackMedia).order_by(desc(MktTrackMedia.updated_at)).limit(min(limit, 500))
    if platform:
        stmt = stmt.where(MktTrackMedia.platform == platform)
    if is_comment is not None:
        stmt = stmt.where(MktTrackMedia.is_comment == is_comment)
    if status is not None:
        stmt = stmt.where(MktTrackMedia.status == status)
    res = await session.exec(stmt)
    return {"items": [i.model_dump() for i in res.all()]}


@router.post("/track-media")
async def create_track_media(
    req: TrackMediaCreate,
    _: object = Depends(require_permission("marketing.manage")),
    session=Depends(get_session),
):
    item = MktTrackMedia(**req.model_dump())
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return {"item": item.model_dump()}


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
    return {"item": item.model_dump()}


@router.get("/track-comments")
async def list_track_comments(
    platform: str | None = None,
    track_status: int | None = None,
    is_deleted: bool | None = None,
    limit: int = 200,
    _: object = Depends(require_permission("marketing.view")),
    session=Depends(get_session),
):
    stmt = select(MktTrackComment).order_by(desc(MktTrackComment.updated_at)).limit(min(limit, 500))
    if platform:
        stmt = stmt.where(MktTrackComment.platform == platform)
    if track_status is not None:
        stmt = stmt.where(MktTrackComment.track_status == track_status)
    if is_deleted is not None:
        stmt = stmt.where(MktTrackComment.is_deleted == is_deleted)
    res = await session.exec(stmt)
    return {"items": [i.model_dump() for i in res.all()]}


@router.post("/track-comments")
async def create_track_comment(
    req: TrackCommentCreate,
    _: object = Depends(require_permission("marketing.manage")),
    session=Depends(get_session),
):
    item = MktTrackComment(**req.model_dump())
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return {"item": item.model_dump()}


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
    limit: int = 200,
    _: object = Depends(require_permission("marketing.view")),
    session=Depends(get_session),
):
    stmt = select(MktInteractionRecord).order_by(desc(MktInteractionRecord.created_at)).limit(min(limit, 500))
    if platform:
        stmt = stmt.where(MktInteractionRecord.platform == platform)
    if event_type:
        stmt = stmt.where(MktInteractionRecord.event_type == event_type)
    if status is not None:
        stmt = stmt.where(MktInteractionRecord.status == status)
    res = await session.exec(stmt)
    return {"items": [i.model_dump() for i in res.all()]}


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

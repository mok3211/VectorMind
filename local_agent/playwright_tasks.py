from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from playwright.async_api import async_playwright

from local_agent.platform_id import extract_platform_content_id


async def _extract_int(text: str) -> int | None:
    s = (text or "").strip().replace(",", "").replace(" ", "")
    if not s:
        return None
    if s.endswith(("w", "W")):
        try:
            return int(float(s[:-1]) * 10000)
        except Exception:
            return None
    digits = "".join([ch for ch in s if ch.isdigit()])
    if not digits:
        return None
    try:
        return int(digits)
    except Exception:
        return None


async def collect_content_metrics(
    *,
    platform: str,
    url: str,
    title: str | None,
    user_data_dir: str,
    headless: bool,
    slow_mo_ms: int,
) -> dict[str, Any]:
    """
    真实采集（本机登录态）：
    - 通过 persistent context 复用用户本机登录状态
    - 指标解析目前走 UI 文本（后续可按你测试反馈改成抓网络 JSON）
    """

    now = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    platform_content_id = extract_platform_content_id(platform, url) or url

    async with async_playwright() as p:
        video_dir = Path("./.agent_artifacts/videos")
        video_dir.mkdir(parents=True, exist_ok=True)
        context = await p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=headless,
            slow_mo=slow_mo_ms if slow_mo_ms > 0 else None,
            record_video_dir=str(video_dir),
        )
        try:
            page = await context.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=60_000)
            await page.wait_for_timeout(1200)

            metrics: dict[str, Any] = {}
            if platform == "xhs":
                mapping = {
                    "like_count": ["text=赞", "text=点赞"],
                    "collect_count": ["text=收藏"],
                    "comment_count": ["text=评论"],
                }
            else:
                mapping = {
                    "like_count": ["text=赞", "text=点赞"],
                    "comment_count": ["text=评论"],
                    "collect_count": ["text=收藏"],
                    "share_count": ["text=分享"],
                }

            for key, sels in mapping.items():
                for sel in sels:
                    try:
                        loc = page.locator(sel).first
                        if await loc.count() > 0:
                            txt = await loc.inner_text()
                            v = await _extract_int(txt)
                            if v is not None:
                                metrics[key] = v
                                break
                    except Exception:
                        continue

            shot_dir = Path("./.agent_artifacts/screenshots")
            shot_dir.mkdir(parents=True, exist_ok=True)
            shot_path = shot_dir / f"{platform}_{platform_content_id}_{int(datetime.utcnow().timestamp())}.png"
            try:
                await page.screenshot(path=str(shot_path), full_page=True)
            except Exception:
                shot_path = None  # type: ignore[assignment]

            video_path = None
            try:
                if page.video:
                    video_path = await page.video.path()
            except Exception:
                video_path = None

            return {
                "contents": [
                    {
                        "platform": platform,
                        "platform_content_id": platform_content_id,
                        "content_type": "note" if platform == "xhs" else "video",
                        "url": url,
                        "title": title or (await page.title()),
                        "description": None,
                        "published_at": now,
                        "source": "chrome_extension",
                    }
                ],
                "content_snapshots": [
                    {
                        "platform_content_id": platform_content_id,
                        "captured_at": now,
                        **metrics,
                    }
                ],
                "comments": [],
                "artifacts": [
                    a
                    for a in [
                        {"kind": "screenshot", "path": str(shot_path)} if shot_path else None,
                        {"kind": "video", "path": str(video_path)} if video_path else None,
                    ]
                    if a
                ],
            }
        finally:
            await context.close()

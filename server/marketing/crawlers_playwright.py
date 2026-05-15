from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

import json
import re
from playwright.async_api import Page

from server.marketing.crawlers import CrawlResult, Crawler
from server.marketing.playwright_client import PlaywrightSessionError, new_context_from_marketing_session


async def _extract_int(text: str) -> int | None:
    s = (text or "").strip()
    if not s:
        return None
    s = s.replace(",", "").replace(" ", "")
    # 兼容 1.2w
    if s.endswith(("w", "W")):
        try:
            return int(float(s[:-1]) * 10000)
        except Exception:
            return None
    try:
        return int("".join([ch for ch in s if ch.isdigit()]) or "0")
    except Exception:
        return None


async def _parse_xhs_metrics(page: Page) -> dict[str, Any]:
    """
    不依赖签名，走“页面解析”方式。
    注意：选择器在平台更新时可能会变，后续你测试反馈我再修。
    """
    # 尝试读取常见的计数按钮
    await page.wait_for_timeout(800)
    candidates = [
        ("like_count", ["text=赞", "text=点赞"]),
        ("collect_count", ["text=收藏"]),
        ("comment_count", ["text=评论"]),
    ]
    out: dict[str, Any] = {}
    for key, sels in candidates:
        val = None
        for sel in sels:
            try:
                loc = page.locator(sel).first
                if await loc.count() > 0:
                    txt = await loc.inner_text()
                    v = await _extract_int(txt)
                    if v is not None and v > 0:
                        val = v
                        break
            except Exception:
                continue
        if val is not None:
            out[key] = val
    # view_count 小红书不一定能直接拿到，留空
    return out


async def _parse_douyin_metrics(page: Page) -> dict[str, Any]:
    await page.wait_for_timeout(800)
    out: dict[str, Any] = {}
    # 抖音页面上一般有点赞/评论/收藏/分享等按钮文本，选择器也可能变化
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
                    if v is not None and v > 0:
                        out[key] = v
                        break
            except Exception:
                continue
    return out


def _match_json_response(url: str, patterns: list[str]) -> bool:
    u = (url or "").lower()
    return any(p in u for p in patterns)


async def _collect_network_json(page: Page, patterns: list[str], timeout_ms: int = 8000) -> list[dict[str, Any]]:
    """
    监听网络响应，抓取可能包含指标/评论的 JSON。
    """
    collected: list[dict[str, Any]] = []

    async def on_response(resp):
        try:
            url = resp.url
            if not _match_json_response(url, patterns):
                return
            ctype = (resp.headers.get("content-type") or "").lower()
            if "json" not in ctype and "text" not in ctype:
                return
            body = await resp.text()
            if not body or len(body) > 5_000_000:
                return
            obj = json.loads(body)
            if isinstance(obj, dict):
                obj["_url"] = url
                collected.append(obj)
        except Exception:
            return

    page.on("response", on_response)
    await page.wait_for_timeout(timeout_ms)
    try:
        page.off("response", on_response)
    except Exception:
        pass
    return collected


@dataclass(slots=True)
class _Target:
    platform_content_id: str
    url: str | None
    title: str | None
    source: str | None


def _targets_from_params(params: dict[str, Any]) -> list[_Target]:
    targets = params.get("targets")
    out: list[_Target] = []
    if isinstance(targets, list):
        for t in targets:
            if not isinstance(t, dict):
                continue
            pid = str(t.get("platform_content_id") or "").strip()
            if not pid:
                continue
            out.append(
                _Target(
                    platform_content_id=pid,
                    url=(str(t.get("url")).strip() if t.get("url") else None),
                    title=(str(t.get("title")).strip() if t.get("title") else None),
                    source=(str(t.get("source")).strip() if t.get("source") else None),
                )
            )
    if out:
        return out
    # fallback: 只有 ids，没有 url
    ids = params.get("platform_content_ids") or []
    if isinstance(ids, str):
        ids = [s.strip() for s in ids.split(",") if s.strip()]
    if isinstance(ids, list):
        for i in ids:
            pid = str(i).strip()
            if pid:
                out.append(_Target(platform_content_id=pid, url=None, title=None, source=None))
    return out


class BasePlaywrightCrawler:
    platform: str

    def __init__(self, platform: str):
        self.platform = platform

    async def run(self, *, job_type: str, params: dict[str, Any] | None = None) -> CrawlResult:
        raise NotImplementedError


class XhsPlaywrightCrawler(BasePlaywrightCrawler):
    def __init__(self):
        super().__init__("xhs")

    async def run(self, *, job_type: str, params: dict[str, Any] | None = None) -> CrawlResult:
        params = params or {}
        session_data = params.get("session_data")
        if not isinstance(session_data, dict):
            raise PlaywrightSessionError("缺少 session_data（请先导入会话）")

        targets = _targets_from_params(params)
        if not targets:
            return CrawlResult(raw={"mode": "playwright", "detail": "no targets"})

        pw, browser, context = await new_context_from_marketing_session(
            session_data=session_data,
            headless=bool(params.get("headless", True)),
            slow_mo_ms=int(params.get("slow_mo_ms", 0) or 0),
        )
        try:
            page = await context.new_page()
            now = datetime.utcnow().replace(microsecond=0)
            contents: list[dict[str, Any]] = []
            snapshots: list[dict[str, Any]] = []
            comments: list[dict[str, Any]] = []
            for t in targets[:20]:
                if not t.url:
                    t = _Target(
                        platform_content_id=t.platform_content_id,
                        url=f"https://www.xiaohongshu.com/explore/{t.platform_content_id}",
                        title=t.title,
                        source=t.source,
                    )
                # 监听常见评论接口，便于 comment_sync 时提取
                network = await _collect_network_json(
                    page,
                    patterns=[
                        "/api/sns/web/v2/comment/page",
                        "/api/sns/web/v2/comment/sub/page",
                        "/api/sns/web/v1/feed",
                        "/api/sns/web/v2/feed",
                    ],
                    timeout_ms=10,  # 先注册监听
                )
                await page.goto(t.url, wait_until="domcontentloaded", timeout=60_000)
                # 指标优先：页面解析；后续可根据你测试反馈改为网络 JSON 优先
                m = await _parse_xhs_metrics(page)
                # 若需要同步评论：尝试从网络响应提取
                if job_type == "comment_sync":
                    network = await _collect_network_json(
                        page,
                        patterns=["/api/sns/web/v2/comment/page", "/api/sns/web/v2/comment/sub/page"],
                        timeout_ms=int(params.get("network_wait_ms", 3500) or 3500),
                    )
                    for obj in network:
                        data = obj.get("data") or {}
                        items = data.get("comments") or data.get("items") or []
                        if not isinstance(items, list):
                            continue
                        for it in items[:200]:
                            if not isinstance(it, dict):
                                continue
                            cid = str(it.get("id") or it.get("comment_id") or "").strip()
                            if not cid:
                                continue
                            comments.append(
                                {
                                    "platform_content_id": t.platform_content_id,
                                    "platform_comment_id": cid,
                                    "parent_comment_id": it.get("parent_comment_id") or it.get("parent_id"),
                                    "user_sec_uid": (it.get("user_info") or {}).get("user_id"),
                                    "nickname": (it.get("user_info") or {}).get("nickname"),
                                    "content": it.get("content") or it.get("text"),
                                    "like_count": (it.get("like_info") or {}).get("like_count") or it.get("like_count"),
                                    "sub_comment_count": it.get("sub_comment_count"),
                                    "raw": it,
                                }
                            )
                contents.append(
                    {
                        "platform": "xhs",
                        "platform_content_id": t.platform_content_id,
                        "content_type": "note",
                        "url": t.url,
                        "title": t.title or (await page.title()),
                        "description": None,
                        "published_at": now.isoformat() + "Z",
                        "source": t.source,
                    }
                )
                snapshots.append({"platform_content_id": t.platform_content_id, "captured_at": now.isoformat() + "Z", **m})

            return CrawlResult(
                contents_upserted=len(contents),
                content_snapshots=len(snapshots),
                comments_upserted=len(comments),
                raw={
                    "mode": "playwright",
                    "platform": "xhs",
                    "job_type": job_type,
                    "contents": contents,
                    "content_snapshots": snapshots,
                    "comments": comments,
                },
            )
        finally:
            await context.close()
            await browser.close()
            await pw.stop()


class DouyinPlaywrightCrawler(BasePlaywrightCrawler):
    def __init__(self):
        super().__init__("douyin")

    async def run(self, *, job_type: str, params: dict[str, Any] | None = None) -> CrawlResult:
        params = params or {}
        session_data = params.get("session_data")
        if not isinstance(session_data, dict):
            raise PlaywrightSessionError("缺少 session_data（请先导入会话）")

        targets = _targets_from_params(params)
        if not targets:
            return CrawlResult(raw={"mode": "playwright", "detail": "no targets"})

        pw, browser, context = await new_context_from_marketing_session(
            session_data=session_data,
            headless=bool(params.get("headless", True)),
            slow_mo_ms=int(params.get("slow_mo_ms", 0) or 0),
        )
        try:
            page = await context.new_page()
            now = datetime.utcnow().replace(microsecond=0)
            contents: list[dict[str, Any]] = []
            snapshots: list[dict[str, Any]] = []
            comments: list[dict[str, Any]] = []
            for t in targets[:20]:
                if not t.url:
                    t = _Target(
                        platform_content_id=t.platform_content_id,
                        url=f"https://www.douyin.com/video/{t.platform_content_id}",
                        title=t.title,
                        source=t.source,
                    )
                await page.goto(t.url, wait_until="domcontentloaded", timeout=60_000)
                # 监听常见评论/详情接口（若能抓到 JSON 则更稳定）
                if job_type == "comment_sync":
                    network = await _collect_network_json(
                        page,
                        patterns=["comment/list", "aweme/v1/web/comment", "aweme/v1/web/aweme/detail"],
                        timeout_ms=int(params.get("network_wait_ms", 3500) or 3500),
                    )
                    for obj in network:
                        # 兼容 aweme 评论返回结构差异
                        cmts = obj.get("comments") or (obj.get("comment_list") if isinstance(obj.get("comment_list"), list) else None) or []
                        if isinstance(cmts, dict):
                            cmts = cmts.get("comments") or []
                        if not isinstance(cmts, list):
                            continue
                        for it in cmts[:200]:
                            if not isinstance(it, dict):
                                continue
                            cid = str(it.get("cid") or it.get("comment_id") or "").strip()
                            if not cid:
                                continue
                            user = it.get("user") or {}
                            comments.append(
                                {
                                    "platform_content_id": t.platform_content_id,
                                    "platform_comment_id": cid,
                                    "parent_comment_id": it.get("reply_id"),
                                    "user_sec_uid": user.get("sec_uid"),
                                    "nickname": user.get("nickname"),
                                    "content": it.get("text"),
                                    "like_count": it.get("digg_count"),
                                    "raw": it,
                                }
                            )

                m = await _parse_douyin_metrics(page)
                contents.append(
                    {
                        "platform": "douyin",
                        "platform_content_id": t.platform_content_id,
                        "content_type": "video",
                        "url": t.url,
                        "title": t.title or (await page.title()),
                        "description": None,
                        "published_at": now.isoformat() + "Z",
                        "source": t.source,
                    }
                )
                snapshots.append({"platform_content_id": t.platform_content_id, "captured_at": now.isoformat() + "Z", **m})

            return CrawlResult(
                contents_upserted=len(contents),
                content_snapshots=len(snapshots),
                comments_upserted=len(comments),
                raw={
                    "mode": "playwright",
                    "platform": "douyin",
                    "job_type": job_type,
                    "contents": contents,
                    "content_snapshots": snapshots,
                    "comments": comments,
                },
            )
        finally:
            await context.close()
            await browser.close()
            await pw.stop()


def get_playwright_crawler(platform: str) -> Crawler:
    p = (platform or "").strip().lower()
    if p in {"xhs", "xiaohongshu"}:
        return XhsPlaywrightCrawler()
    if p in {"douyin", "dy"}:
        return DouyinPlaywrightCrawler()
    raise ValueError(f"unsupported platform: {platform}")

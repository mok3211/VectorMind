from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Callable
from urllib.parse import quote

from playwright.async_api import Page


@dataclass(slots=True)
class VideoItem:
    platform: str
    platform_content_id: str
    url: str | None
    title: str | None
    author_name: str | None
    author_id: str | None
    author_url: str | None
    raw: dict[str, Any]


@dataclass(slots=True)
class CreatorItem:
    platform: str
    platform_user_id: str | None
    sec_uid: str | None
    nickname: str | None
    user_link: str | None
    raw: dict[str, Any]


async def _wait_json_response(page: Page, *, match: Callable[[str, str], bool], timeout_ms: int = 60_000) -> dict[str, Any]:
    async with page.expect_response(lambda r: match(r.url, r.request.method), timeout=timeout_ms) as rinfo:
        resp = await rinfo.value
    try:
        return await resp.json()
    except Exception:
        txt = ""
        try:
            txt = await resp.text()
        except Exception:
            txt = ""
        raise ValueError(f"response 不是 JSON：{resp.status} {resp.url} body={txt[:400]}")


async def _scroll_until(
    page: Page,
    *,
    predicate: Callable[[], bool],
    max_rounds: int = 12,
    wait_ms: int = 800,
) -> None:
    for _ in range(max_rounds):
        if predicate():
            return
        await page.mouse.wheel(0, 1600)
        await page.wait_for_timeout(wait_ms)


def _extract_xhs_note_items(data: dict[str, Any]) -> list[dict[str, Any]]:
    items = (
        data.get("data", {})
        .get("items", [])
    )
    out: list[dict[str, Any]] = []
    for it in items:
        if not isinstance(it, dict):
            continue
        note = it.get("note_card") or it.get("noteCard") or {}
        if isinstance(note, dict) and note:
            if "id" not in note and it.get("id"):
                note = dict(note)
                note["id"] = it.get("id")
            if "xsec_token" not in note and it.get("xsec_token"):
                note = dict(note)
                note["xsec_token"] = it.get("xsec_token")
            if "model_type" not in note and it.get("model_type"):
                note = dict(note)
                note["model_type"] = it.get("model_type")
            out.append(note)
    return out


def _xhs_note_to_video(note: dict[str, Any]) -> VideoItem | None:
    note_id = str(note.get("note_id") or note.get("noteId") or note.get("id") or "").strip()
    if not note_id:
        return None
    title = note.get("title") or note.get("display_title") or note.get("desc") or None
    user = note.get("user") or {}
    user_id = str(user.get("user_id") or user.get("userId") or "").strip() or None
    nickname = user.get("nickname") or user.get("nick_name") or user.get("nickName") or None
    xsec_token = str(note.get("xsec_token") or "").strip()
    if xsec_token:
        url = f"https://www.xiaohongshu.com/explore/{note_id}?xsec_token={quote(xsec_token)}&xsec_source=pc_search"
    else:
        url = f"https://www.xiaohongshu.com/explore/{note_id}"
    author_url = f"https://www.xiaohongshu.com/user/profile/{user_id}" if user_id else None
    return VideoItem(
        platform="xhs",
        platform_content_id=note_id,
        url=url,
        title=title,
        author_name=nickname,
        author_id=user_id,
        author_url=author_url,
        raw=note,
    )


def _extract_douyin_items(data: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not isinstance(data, dict):
        return out
    items = data.get("data") or data.get("aweme_list") or data.get("awemeList") or []
    if isinstance(items, list) and items:
        for it in items:
            if isinstance(it, dict):
                out.append(it)
        return out
    resp = data.get("data") or {}
    if isinstance(resp, dict):
        items = resp.get("aweme_list") or resp.get("awemeList") or resp.get("items") or []
        if isinstance(items, list):
            for it in items:
                if isinstance(it, dict):
                    out.append(it)
    return out


def _douyin_aweme_to_video(aweme: dict[str, Any]) -> VideoItem | None:
    aweme_id = str(aweme.get("aweme_id") or aweme.get("awemeId") or "").strip()
    if not aweme_id:
        return None
    desc = aweme.get("desc") or None
    author = aweme.get("author") or {}
    sec_uid = str(author.get("sec_uid") or "").strip() or None
    uid = str(author.get("uid") or "").strip() or None
    nickname = author.get("nickname") or None
    url = f"https://www.douyin.com/video/{aweme_id}"
    author_url = f"https://www.douyin.com/user/{sec_uid}" if sec_uid else None
    return VideoItem(
        platform="douyin",
        platform_content_id=aweme_id,
        url=url,
        title=desc,
        author_name=nickname,
        author_id=uid or sec_uid,
        author_url=author_url,
        raw=aweme,
    )


def _creator_from_video(v: VideoItem) -> CreatorItem | None:
    if v.platform == "xhs":
        if not v.author_id and not v.author_name:
            return None
        return CreatorItem(
            platform="xhs",
            platform_user_id=v.author_id,
            sec_uid=v.author_id,
            nickname=v.author_name,
            user_link=v.author_url,
            raw={"from": "video_search", "author_id": v.author_id, "author_name": v.author_name},
        )
    if v.platform == "douyin":
        if not v.author_id and not v.author_name:
            return None
        return CreatorItem(
            platform="douyin",
            platform_user_id=v.author_id,
            sec_uid=v.author_id,
            nickname=v.author_name,
            user_link=v.author_url,
            raw={"from": "video_search", "author_id": v.author_id, "author_name": v.author_name},
        )
    return None


async def search_videos_with_page(
    *,
    platform: str,
    keyword: str,
    page: int = 1,
    timeout_ms: int = 60_000,
    headless_hint: bool = True,
    new_page: Callable[[], Any],
) -> list[VideoItem]:
    keyword = (keyword or "").strip()
    if not keyword:
        return []
    platform = (platform or "").strip().lower()
    if platform not in {"xhs", "douyin"}:
        raise ValueError("platform 仅支持 xhs / douyin")
    page = max(1, int(page or 1))

    page_obj = await new_page()
    try:
        if platform == "xhs":
            url = f"https://www.xiaohongshu.com/search_result?keyword={quote(keyword)}"
            await page_obj.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)

            seen: set[str] = set()
            results: list[VideoItem] = []

            def has_enough() -> bool:
                return len(results) >= page * 20

            while True:
                data = await _wait_json_response(
                    page_obj,
                    match=lambda u, m: (m == "POST" and "api/sns/web/v1/search/notes" in u),
                    timeout_ms=timeout_ms,
                )
                notes = _extract_xhs_note_items(data)
                for n in notes:
                    v = _xhs_note_to_video(n)
                    if not v:
                        continue
                    if v.platform_content_id in seen:
                        continue
                    seen.add(v.platform_content_id)
                    results.append(v)
                if has_enough():
                    break
                await _scroll_until(page_obj, predicate=has_enough, max_rounds=6, wait_ms=800)
                if has_enough():
                    break
                await asyncio.sleep(0.2)

            return results[: page * 20]

        url = f"https://www.douyin.com/search/{quote(keyword)}"
        await page_obj.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)

        seen: set[str] = set()
        results: list[VideoItem] = []

        def has_enough() -> bool:
            return len(results) >= page * 20

        while True:
            data = await _wait_json_response(
                page_obj,
                    match=lambda u, m: (
                        m == "GET"
                        and (
                            "/aweme/v1/web/search/item" in u
                            or "/aweme/v1/web/general/search/single" in u
                            or "/aweme/v1/web/general/search" in u
                        )
                    ),
                timeout_ms=timeout_ms,
            )
            items = _extract_douyin_items(data)
            for it in items:
                v = _douyin_aweme_to_video(it)
                if not v:
                    continue
                if v.platform_content_id in seen:
                    continue
                seen.add(v.platform_content_id)
                results.append(v)
            if has_enough():
                break
            await _scroll_until(page_obj, predicate=has_enough, max_rounds=6, wait_ms=900)
            if has_enough():
                break
            await asyncio.sleep(0.2)

        return results[: page * 20]
    finally:
        await page_obj.close()


async def search_creators(
    *,
    platform: str,
    keyword: str,
    page: int = 1,
    timeout_ms: int = 60_000,
    new_page: Callable[[], Any],
) -> list[CreatorItem]:
    videos = await search_videos_with_page(
        platform=platform,
        keyword=keyword,
        page=page,
        timeout_ms=timeout_ms,
        new_page=new_page,
    )
    out: list[CreatorItem] = []
    seen: set[str] = set()
    for v in videos:
        c = _creator_from_video(v)
        if not c:
            continue
        k = (c.sec_uid or c.platform_user_id or c.nickname or "").strip()
        if not k or k in seen:
            continue
        seen.add(k)
        out.append(c)
    return out

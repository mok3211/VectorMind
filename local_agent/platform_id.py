from __future__ import annotations

import re


XHS_PATTERNS: list[re.Pattern] = [
    # https://www.xiaohongshu.com/explore/<id>
    re.compile(r"xiaohongshu\.com/(?:explore|discovery/item)/(?P<id>[a-zA-Z0-9]+)"),
    # 有些分享会带 note_id=<id>
    re.compile(r"[?&](?:note_id|itemId|item_id)=(?P<id>[a-zA-Z0-9]+)"),
]

DOUYIN_PATTERNS: list[re.Pattern] = [
    # https://www.douyin.com/video/<aweme_id>
    re.compile(r"douyin\.com/(?:video|share/video)/(?P<id>\d+)"),
    # share/?modal_id=xxx 或 item_id=xxx
    re.compile(r"[?&](?:modal_id|item_id|aweme_id)=(?P<id>\d+)"),
]


def guess_platform(url: str) -> str:
    u = (url or "").lower()
    if "xiaohongshu.com" in u:
        return "xhs"
    if "douyin.com" in u:
        return "douyin"
    return "unknown"


def extract_platform_content_id(platform: str, url: str) -> str | None:
    platform = (platform or "").strip().lower()
    url = (url or "").strip()
    if not url:
        return None

    patterns = XHS_PATTERNS if platform == "xhs" else DOUYIN_PATTERNS if platform == "douyin" else []
    for p in patterns:
        m = p.search(url)
        if m and m.groupdict().get("id"):
            return m.group("id")
    return None


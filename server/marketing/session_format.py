from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


class SessionFormatError(ValueError):
    pass


@dataclass(slots=True)
class NormalizedSession:
    platform: str
    user_agent: str | None
    session_data: dict[str, Any]
    warnings: list[str]


def _norm_platform(p: str | None) -> str:
    p = (p or "").strip().lower()
    if p in {"xiaohongshu"}:
        return "xhs"
    if p in {"dy"}:
        return "douyin"
    return p


def normalize_marketing_session_v1(
    raw: dict[str, Any],
    *,
    fallback_platform: str | None = None,
    fallback_user_agent: str | None = None,
) -> NormalizedSession:
    """
    MarketingSession v1：
    - version: 1
    - platform: xhs/douyin
    - auth.cookies: list[{name,value,domain?,path?,expires? ...}]
    - client.user_agent: str (建议)
    """

    if not isinstance(raw, dict):
        raise SessionFormatError("session_data 必须是 JSON object")

    warnings: list[str] = []

    version = raw.get("version", 1)
    if version != 1:
        raise SessionFormatError("仅支持 MarketingSession v1（version=1）")

    platform = _norm_platform(raw.get("platform") or fallback_platform)
    if platform not in {"xhs", "douyin"}:
        raise SessionFormatError("platform 仅支持 xhs / douyin")

    default_cookie_domain = ".xiaohongshu.com" if platform == "xhs" else ".douyin.com"

    auth = raw.get("auth") or {}
    cookies = auth.get("cookies")
    if not isinstance(cookies, list) or len(cookies) == 0:
        raise SessionFormatError("auth.cookies 不能为空（需要至少一个 cookie）")

    norm_cookies: list[dict[str, Any]] = []
    for idx, c in enumerate(cookies):
        if not isinstance(c, dict):
            raise SessionFormatError(f"auth.cookies[{idx}] 必须是 object")
        name = (c.get("name") or "").strip()
        value = c.get("value")
        if not name or value is None:
            raise SessionFormatError(f"auth.cookies[{idx}] 必须包含 name/value")
        out = dict(c)
        out["name"] = name
        out["value"] = value
        # domain/path/expires 可选，但建议提供以提升稳定性
        if not out.get("domain"):
            out["domain"] = default_cookie_domain
            warnings.append(f"cookie {name} 缺少 domain，已自动补齐为 {default_cookie_domain}")
        if not out.get("path"):
            out["path"] = "/"
            warnings.append(f"cookie {name} 缺少 path，已自动补齐为 /")
        norm_cookies.append(out)

    client = raw.get("client") or {}
    user_agent = (client.get("user_agent") or fallback_user_agent or "").strip() or None
    if not user_agent:
        warnings.append("client.user_agent 为空（建议填写，平台风控与签名通常依赖 UA）")

    # 标准化写回
    raw = dict(raw)
    raw["version"] = 1
    raw["platform"] = platform
    raw.setdefault("auth", {})
    raw["auth"] = dict(raw["auth"])
    raw["auth"]["cookies"] = norm_cookies
    raw.setdefault("client", {})
    raw["client"] = dict(raw["client"])
    if user_agent:
        raw["client"]["user_agent"] = user_agent
    raw.setdefault("created_at", datetime.utcnow().isoformat() + "Z")

    return NormalizedSession(platform=platform, user_agent=user_agent, session_data=raw, warnings=warnings)

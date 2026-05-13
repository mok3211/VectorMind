from __future__ import annotations

from typing import Any

from playwright.async_api import Browser, BrowserContext, async_playwright


class PlaywrightSessionError(RuntimeError):
    pass


def _cookie_to_playwright(c: dict[str, Any]) -> dict[str, Any]:
    name = (c.get("name") or "").strip()
    value = c.get("value")
    domain = (c.get("domain") or "").strip()
    path = (c.get("path") or "").strip() or "/"
    if not name or value is None:
        raise PlaywrightSessionError("cookie 缺少 name/value")
    if not domain:
        # Playwright add_cookies 必须有 domain 或 url
        raise PlaywrightSessionError(f"cookie {name} 缺少 domain（请补齐）")
    out: dict[str, Any] = {"name": name, "value": value, "domain": domain, "path": path}
    for k in ("expires", "httpOnly", "secure", "sameSite"):
        if k in c and c.get(k) is not None:
            out[k] = c.get(k)
    return out


async def new_context_from_marketing_session(
    *,
    session_data: dict[str, Any],
    headless: bool = True,
    slow_mo_ms: int = 0,
) -> tuple[Any, Browser, BrowserContext]:
    """
    返回 (playwright, browser, context)，由调用方负责关闭：
    await context.close(); await browser.close(); await playwright.stop()
    """

    auth = session_data.get("auth") or {}
    cookies = auth.get("cookies") or []
    if not isinstance(cookies, list) or len(cookies) == 0:
        raise PlaywrightSessionError("session_data.auth.cookies 为空")

    client = session_data.get("client") or {}
    user_agent = (client.get("user_agent") or "").strip() or None

    proxy = session_data.get("proxy") or {}
    proxy_url = None
    if isinstance(proxy, dict) and proxy.get("enabled") and proxy.get("url"):
        proxy_url = str(proxy.get("url")).strip() or None

    pw = await async_playwright().start()
    launch_kwargs: dict[str, Any] = {"headless": headless}
    if proxy_url:
        launch_kwargs["proxy"] = {"server": proxy_url}
    if slow_mo_ms and slow_mo_ms > 0:
        launch_kwargs["slow_mo"] = int(slow_mo_ms)
    browser = await pw.chromium.launch(**launch_kwargs)

    context_kwargs: dict[str, Any] = {}
    if user_agent:
        context_kwargs["user_agent"] = user_agent
    context = await browser.new_context(**context_kwargs)

    pw_cookies = [_cookie_to_playwright(c) for c in cookies]
    await context.add_cookies(pw_cookies)
    return pw, browser, context

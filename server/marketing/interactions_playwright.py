from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from playwright.async_api import Page

from server.config import settings
from server.marketing.playwright_client import PlaywrightSessionError, new_context_from_marketing_session


@dataclass(slots=True)
class SendResult:
    ok: bool
    detail: str = ""
    raw: dict[str, Any] | None = None


async def _try_click(page: Page, selectors: list[str], *, timeout_ms: int = 1500) -> bool:
    for sel in selectors:
        try:
            loc = page.locator(sel).first
            if await loc.count() > 0:
                await loc.click(timeout=timeout_ms)
                return True
        except Exception:
            continue
    return False


async def _try_fill(page: Page, selectors: list[str], text: str, *, timeout_ms: int = 1500) -> bool:
    for sel in selectors:
        try:
            loc = page.locator(sel).first
            if await loc.count() > 0:
                await loc.click(timeout=timeout_ms)
                await loc.fill(text, timeout=timeout_ms)
                return True
        except Exception:
            continue
    return False


async def _detect_login_prompt(page: Page) -> bool:
    html = (await page.content()).lower()
    # 非严格：出现登录字样/按钮，可能未登录
    return ("登录" in html) or ("login" in html)


async def send_comment_xhs(
    *,
    url: str,
    session_data: dict[str, Any],
    text: str,
    headless: bool | None = None,
    slow_mo_ms: int | None = None,
) -> SendResult:
    if not url:
        return SendResult(ok=False, detail="url 为空")
    if not isinstance(session_data, dict):
        return SendResult(ok=False, detail="session_data 为空")
    if not text.strip():
        return SendResult(ok=False, detail="评论内容为空")

    headless = bool(settings.marketing_playwright_headless) if headless is None else bool(headless)
    slow_mo_ms = int(settings.marketing_playwright_slow_mo_ms) if slow_mo_ms is None else int(slow_mo_ms)

    pw, browser, context = await new_context_from_marketing_session(
        session_data=session_data, headless=headless, slow_mo_ms=slow_mo_ms
    )
    try:
        page = await context.new_page()
        await page.goto(url, wait_until="domcontentloaded", timeout=60_000)
        await page.wait_for_timeout(800)

        if await _detect_login_prompt(page):
            # 不是 100% 准确，但用于提示
            return SendResult(ok=False, detail="可能未登录（页面包含登录提示）")

        # 尝试打开评论输入框
        await _try_click(
            page,
            selectors=[
                'text=评论',
                '[placeholder*="说点什么"]',
                '[placeholder*="发条友善的评论"]',
                'textarea',
                '[contenteditable="true"]',
            ],
            timeout_ms=2000,
        )

        filled = await _try_fill(
            page,
            selectors=[
                'textarea[placeholder*="说点什么"]',
                'textarea',
                '[contenteditable="true"]',
            ],
            text=text.strip(),
            timeout_ms=3000,
        )
        if not filled:
            return SendResult(ok=False, detail="未找到评论输入框（选择器可能需要调整）")

        # 提交按钮
        clicked = await _try_click(
            page,
            selectors=[
                'button:has-text("发送")',
                'button:has-text("发布")',
                'text=发送',
                'text=发布',
            ],
            timeout_ms=3000,
        )
        if not clicked:
            # 有些站点是 Enter 发送
            try:
                await page.keyboard.press("Enter")
                clicked = True
            except Exception:
                clicked = False
        await page.wait_for_timeout(1200)

        # 这里没法 100% 判断成功，先按“未报错 + 已点击提交”认为成功
        if clicked:
            return SendResult(ok=True, detail="submitted", raw={"ts": datetime.utcnow().isoformat() + "Z"})
        return SendResult(ok=False, detail="未能触发提交（按钮选择器可能需要调整）")
    except Exception as e:
        return SendResult(ok=False, detail=str(e))
    finally:
        await context.close()
        await browser.close()
        await pw.stop()


async def send_comment_douyin(
    *,
    url: str,
    session_data: dict[str, Any],
    text: str,
    headless: bool | None = None,
    slow_mo_ms: int | None = None,
) -> SendResult:
    if not url:
        return SendResult(ok=False, detail="url 为空")
    if not isinstance(session_data, dict):
        return SendResult(ok=False, detail="session_data 为空")
    if not text.strip():
        return SendResult(ok=False, detail="评论内容为空")

    headless = bool(settings.marketing_playwright_headless) if headless is None else bool(headless)
    slow_mo_ms = int(settings.marketing_playwright_slow_mo_ms) if slow_mo_ms is None else int(slow_mo_ms)

    pw, browser, context = await new_context_from_marketing_session(
        session_data=session_data, headless=headless, slow_mo_ms=slow_mo_ms
    )
    try:
        page = await context.new_page()
        await page.goto(url, wait_until="domcontentloaded", timeout=60_000)
        await page.wait_for_timeout(800)

        if await _detect_login_prompt(page):
            return SendResult(ok=False, detail="可能未登录（页面包含登录提示）")

        # 打开评论区
        await _try_click(
            page,
            selectors=[
                'text=评论',
                'button:has-text("评论")',
                '[aria-label*="评论"]',
            ],
            timeout_ms=2500,
        )

        filled = await _try_fill(
            page,
            selectors=[
                'textarea',
                '[contenteditable="true"]',
                '[placeholder*="友善"]',
                '[placeholder*="评论"]',
            ],
            text=text.strip(),
            timeout_ms=3000,
        )
        if not filled:
            return SendResult(ok=False, detail="未找到评论输入框（选择器可能需要调整）")

        clicked = await _try_click(
            page,
            selectors=[
                'button:has-text("发送")',
                'text=发送',
            ],
            timeout_ms=3000,
        )
        if not clicked:
            try:
                await page.keyboard.press("Enter")
                clicked = True
            except Exception:
                clicked = False
        await page.wait_for_timeout(1200)
        if clicked:
            return SendResult(ok=True, detail="submitted", raw={"ts": datetime.utcnow().isoformat() + "Z"})
        return SendResult(ok=False, detail="未能触发提交（按钮选择器可能需要调整）")
    except Exception as e:
        return SendResult(ok=False, detail=str(e))
    finally:
        await context.close()
        await browser.close()
        await pw.stop()


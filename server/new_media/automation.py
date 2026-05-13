from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from server.new_media.fingerprint_store import FingerprintRecord, FingerprintStore
from server.publishers.base import PublishPayload

try:
    from playwright.async_api import async_playwright
except Exception:  # pragma: no cover - 仅在未安装 playwright 时触发
    async_playwright = None  # type: ignore[assignment]


@dataclass(slots=True)
class LoginResult:
    ok: bool
    status: str
    detail: str
    fingerprint: dict[str, Any] | None = None


@dataclass(slots=True)
class PublishResult:
    ok: bool
    status: str
    detail: str
    platform: str
    mode: str
    preview: str | None = None


class BasePlatformAutomator:
    platform: str
    login_url: str
    creator_url: str

    def __init__(self, *, store: FingerprintStore, account_id: int) -> None:
        self.store = store
        self.account_id = account_id

    async def connect_qr(self, *, timeout_sec: int = 180, headless: bool = False) -> LoginResult:
        if async_playwright is None:
            return LoginResult(
                ok=False,
                status="missing_dependency",
                detail="playwright 未安装，请先执行：uv add playwright && uv run playwright install chromium",
            )

        rec = self.store.create_record(platform=self.platform, account_id=self.account_id)
        async with async_playwright() as p:
            context = await p.chromium.launch_persistent_context(
                user_data_dir=str(rec.profile_dir),
                headless=headless,
            )
            try:
                page = context.pages[0] if context.pages else await context.new_page()
                await page.goto(self.login_url, wait_until="domcontentloaded")
                deadline = asyncio.get_running_loop().time() + timeout_sec
                logged_in = False
                while asyncio.get_running_loop().time() < deadline:
                    cookies = await context.cookies()
                    if any(c.get("name") for c in cookies):
                        logged_in = True
                        break
                    await asyncio.sleep(2)

                if not logged_in:
                    return LoginResult(
                        ok=False,
                        status="timeout",
                        detail="登录超时，请在弹出的浏览器完成扫码后重试。",
                    )

                await context.storage_state(path=str(rec.state_file))
                ua = await page.evaluate("navigator.userAgent")
                fp = rec.to_json()
                return LoginResult(
                    ok=True,
                    status="connected",
                    detail="扫码登录成功，已保存会话指纹。",
                    fingerprint={"raw": fp, "user_agent": ua},
                )
            finally:
                await context.close()

    async def publish(self, *, payload: PublishPayload, dry_run: bool = False) -> PublishResult:
        if async_playwright is None:
            return PublishResult(
                ok=False,
                status="missing_dependency",
                detail="playwright 未安装，请先执行：uv add playwright && uv run playwright install chromium",
                platform=self.platform,
                mode="auto",
            )

        rec = self.store.create_record(platform=self.platform, account_id=self.account_id)
        if not rec.profile_dir.exists():
            return PublishResult(
                ok=False,
                status="not_connected",
                detail="该账号尚未建立会话，请先扫码登录。",
                platform=self.platform,
                mode="auto",
            )

        text = payload.text.strip()
        if payload.tags:
            text = f"{text}\n" + " ".join([f"#{t}" for t in payload.tags])

        async with async_playwright() as p:
            context = await p.chromium.launch_persistent_context(
                user_data_dir=str(rec.profile_dir),
                headless=False,
            )
            try:
                page = context.pages[0] if context.pages else await context.new_page()
                await page.goto(self.creator_url, wait_until="domcontentloaded")

                if dry_run:
                    return PublishResult(
                        ok=True,
                        status="dry_run",
                        detail="已打开发布页并复用登录态，可人工确认后发布。",
                        platform=self.platform,
                        mode="assist",
                        preview=f"{payload.title}\n{text}"[:240],
                    )

                ok = await self._try_fill_and_publish(page=page, title=payload.title, text=text)
                if ok:
                    await context.storage_state(path=str(rec.state_file))
                    return PublishResult(
                        ok=True,
                        status="published",
                        detail="自动发布已执行（若平台弹二次确认，请在页面继续确认）。",
                        platform=self.platform,
                        mode="auto",
                    )
                return PublishResult(
                    ok=False,
                    status="needs_manual_action",
                    detail="已打开发布页面，但未定位到稳定输入控件，请人工补充后点击发布。",
                    platform=self.platform,
                    mode="assist",
                    preview=f"{payload.title}\n{text}"[:240],
                )
            finally:
                await context.close()

    async def _try_fill_and_publish(self, *, page: Any, title: str, text: str) -> bool:
        # 通用兜底选择器，平台页面变更较频繁，失败时会回落到 assist 模式
        title_selectors = ["input[placeholder*='标题']", "textarea[placeholder*='标题']"]
        content_selectors = [
            "textarea[placeholder*='正文']",
            "textarea[placeholder*='内容']",
            "[contenteditable='true']",
        ]
        publish_selectors = ["button:has-text('发布')", "button:has-text('立即发布')"]

        title_ok = await self._fill_first(page=page, selectors=title_selectors, value=title)
        content_ok = await self._fill_first(page=page, selectors=content_selectors, value=text)
        if not (title_ok and content_ok):
            return False

        for selector in publish_selectors:
            loc = page.locator(selector)
            if await loc.count():
                await loc.first.click()
                await asyncio.sleep(1)
                return True
        return False

    async def _fill_first(self, *, page: Any, selectors: list[str], value: str) -> bool:
        for selector in selectors:
            loc = page.locator(selector)
            if await loc.count():
                el = loc.first
                await el.click()
                try:
                    await el.fill(value)
                except Exception:
                    await page.keyboard.type(value, delay=10)
                return True
        return False


class XHSAutomator(BasePlatformAutomator):
    platform = "xhs"
    login_url = "https://www.xiaohongshu.com/explore"
    creator_url = "https://creator.xiaohongshu.com/publish/publish"


class DouyinAutomator(BasePlatformAutomator):
    platform = "douyin"
    login_url = "https://www.douyin.com/"
    creator_url = "https://creator.douyin.com/creator-micro/content/upload"


def build_automator(*, platform: str, account_id: int, root: Path) -> BasePlatformAutomator:
    store = FingerprintStore(root_dir=root)
    if platform == "xhs":
        return XHSAutomator(store=store, account_id=account_id)
    if platform == "douyin":
        return DouyinAutomator(store=store, account_id=account_id)
    raise ValueError(f"unsupported platform: {platform}")


def now_iso() -> str:
    return datetime.utcnow().isoformat()

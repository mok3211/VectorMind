from __future__ import annotations

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlmodel import select

from server import db
from server.logging_utils import get_logger
from server.marketing.models import MktLoginRun, MktPlatformProfile, MktPlatformSession
from server.marketing.session_format import normalize_marketing_session_v1

logger = get_logger(__name__)


def _login_url(platform: str) -> str:
    if platform == "xhs":
        return "https://www.xiaohongshu.com/explore"
    return "https://www.douyin.com/"


async def detect_logged_in(platform: str, *, page: Any, context: Any) -> tuple[bool, dict[str, Any]]:
    platform = (platform or "").strip().lower()
    if platform == "xhs":
        me_text = ""
        try:
            me_text = await page.evaluate(
                """async () => {
                  try {
                    const r = await fetch('https://edith.xiaohongshu.com/api/sns/web/v2/user/me', { method: 'GET', credentials: 'include' })
                    return await r.text()
                  } catch (e) {
                    return ''
                  }
                }"""
            )
        except Exception:
            me_text = ""

        if me_text:
            try:
                me = json.loads(me_text)
            except Exception:
                me = None
            if isinstance(me, dict):
                success = bool(me.get("success") is True)
                code = me.get("code")
                data = me.get("data") if isinstance(me.get("data"), dict) else {}
                uid = str(
                    data.get("user_id")
                    or data.get("userId")
                    or data.get("userid")
                    or data.get("userID")
                    or data.get("UserID")
                    or ""
                ).strip()
                nickname = str(data.get("nickname") or data.get("nick_name") or data.get("Nickname") or "").strip()
                guest = data.get("guest") if "guest" in data else data.get("Guest")
                guest_ok = True
                if isinstance(guest, bool):
                    guest_ok = guest is False
                elif isinstance(guest, (int, float)):
                    guest_ok = int(guest) == 0
                elif isinstance(guest, str):
                    guest_ok = guest.strip().lower() in {"", "0", "false", "no", "none"}
                elif guest is None:
                    guest_ok = True
                else:
                    guest_ok = False
                if success and code == 0 and uid and nickname and guest_ok:
                    return True, {"source": "api_me", "uid": uid, "nickname": nickname}

        try:
            info = await page.evaluate(
                """() => {
                  try {
                    const keys = ['userInfo','user_info','user','userProfile','xhs_user','red_user_info','USER_INFO']
                    for (const k of keys) {
                      const v = localStorage.getItem(k)
                      if (!v) continue
                      try {
                        const o = JSON.parse(v)
                        const uid = o.userId || o.user_id || o.uid || o.id || o.userid || o.userID
                        const name = o.nickname || o.nick_name || o.name || o.nickName
                        if (uid && name) return { key: k, raw: v, uid: String(uid), nickname: String(name) }
                      } catch (e) {}
                    }
                    return null
                  } catch (e) {
                    return null
                  }
                }"""
            )
        except Exception:
            info = None

        if isinstance(info, dict):
            uid = str(info.get("uid") or "").strip()
            nickname = str(info.get("nickname") or "").strip()
            if uid and nickname:
                return True, {"source": "local_storage", **info}
        return False, {"source": "none"}

    if platform == "douyin":
        try:
            cookies = await context.cookies()
        except Exception:
            cookies = []
        has_passport = any((c.get("name") or "") == "passport_assist_user" for c in cookies if isinstance(c, dict))
        if not has_passport:
            return False, {"source": "missing_passport_cookie"}

        try:
            user_info = await page.evaluate(
                """() => {
                  try {
                    const raw = localStorage.getItem('user_info') || ''
                    const o = raw ? JSON.parse(raw) : {}
                    const uid = o.UID || o.uid || o.user_id || o.userId || ''
                    const nickname = o.nickname || o.Nickname || o.nick_name || o.name || ''
                    return { raw, uid: uid ? String(uid) : '', nickname: nickname ? String(nickname) : '' }
                  } catch (e) {
                    return { raw: '', uid: '', nickname: '' }
                  }
                }"""
            )
        except Exception:
            user_info = None

        if isinstance(user_info, dict) and str(user_info.get("uid") or "").strip():
            return True, {"source": "user_info_and_cookie", **user_info}
        return True, {"source": "passport_cookie_only"}

    return False, {"source": "unsupported", "platform": platform}


async def _run_qr_login(login_run_id: int, *, timeout_sec: int = 300) -> None:
    async with db.AsyncSessionLocal() as session:
        run = await session.get(MktLoginRun, login_run_id)
        if not run:
            return
        logger.info("qr login start run_id=%s profile_id=%s", login_run_id, getattr(run, "profile_id", None))
        profile = await session.get(MktPlatformProfile, run.profile_id)
        if not profile:
            run.status = "failed"
            run.finished_at = datetime.utcnow()
            run.error = "profile not found"
            session.add(run)
            await session.commit()
            logger.error("qr login failed run_id=%s reason=profile not found", login_run_id)
            return

        platform = (profile.platform or "").strip().lower()
        user_data_dir = Path("./data/marketing/login") / str(profile.id)
        user_data_dir.mkdir(parents=True, exist_ok=True)

        try:
            from playwright.async_api import async_playwright

            pw = await async_playwright().start()
            context = await pw.chromium.launch_persistent_context(
                user_data_dir=str(user_data_dir),
                headless=False,
            )
            try:
                page = await context.new_page()
                await page.goto(_login_url(platform), wait_until="domcontentloaded", timeout=60_000)

                start = asyncio.get_running_loop().time()
                logged_in = False
                cookies: list[dict[str, Any]] = []
                auth_meta: dict[str, Any] = {}
                last_probe_error: str | None = None
                while asyncio.get_running_loop().time() - start < float(timeout_sec):
                    try:
                        ok, meta = await detect_logged_in(platform, page=page, context=context)
                        auth_meta = meta if isinstance(meta, dict) else {}
                        last_probe_error = None
                    except Exception as e:
                        ok = False
                        last_probe_error = str(e)
                        auth_meta = {"source": "probe_error", "error": last_probe_error}

                    if ok:
                        try:
                            await asyncio.sleep(1)
                            state = await context.storage_state()
                            cookies = (state.get("cookies") or []) if isinstance(state, dict) else []
                            try:
                                cookies2 = await context.cookies(_login_url(platform))
                                if isinstance(cookies2, list) and cookies2:
                                    merged: dict[tuple[str, str, str], dict[str, Any]] = {}
                                    for c in cookies:
                                        if not isinstance(c, dict):
                                            continue
                                        k = (str(c.get("name") or ""), str(c.get("domain") or ""), str(c.get("path") or ""))
                                        merged[k] = c
                                    for c in cookies2:
                                        if not isinstance(c, dict):
                                            continue
                                        k = (str(c.get("name") or ""), str(c.get("domain") or ""), str(c.get("path") or ""))
                                        merged[k] = c
                                    cookies = list(merged.values())
                            except Exception:
                                pass
                            if isinstance(auth_meta, dict):
                                auth_meta = dict(auth_meta)
                                auth_meta["storage_state"] = {"cookie_count": len(cookies)}
                        except Exception as e:
                            last_probe_error = str(e)
                            cookies = []

                        if len(cookies) > 0:
                            logged_in = True
                            break
                    await asyncio.sleep(2)

                if not logged_in:
                    msg = "等待扫码登录超时"
                    if last_probe_error:
                        msg = f"{msg}: {last_probe_error}"
                    raise TimeoutError(msg)

                ua = await page.evaluate("() => navigator.userAgent")
                raw = {
                    "version": 1,
                    "platform": platform,
                    "auth": {"cookies": cookies},
                    "client": {"user_agent": ua},
                    "storage": {"user_data_dir": str(user_data_dir)},
                    "account": auth_meta,
                    "notes": "qr_login",
                }
                normalized = normalize_marketing_session_v1(raw, fallback_platform=platform, fallback_user_agent=ua)

                res = await session.exec(
                    select(MktPlatformSession).where(MktPlatformSession.profile_id == profile.id).order_by(MktPlatformSession.updated_at.desc()).limit(1)
                )
                item = res.first()
                if item:
                    item.status = "valid"
                    item.user_agent = normalized.user_agent
                    item.session_data = normalized.session_data
                    item.expires_at = None
                    item.last_error = None
                    item.last_validated_at = datetime.utcnow()
                    item.updated_at = datetime.utcnow()
                else:
                    item = MktPlatformSession(
                        profile_id=profile.id,
                        status="valid",
                        user_agent=normalized.user_agent,
                        session_data=normalized.session_data,
                        expires_at=None,
                        last_validated_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                    )
                    session.add(item)

                if isinstance(auth_meta, dict):
                    uid = str(auth_meta.get("uid") or "").strip()
                    nickname = str(auth_meta.get("nickname") or "").strip()
                    if uid and uid != (profile.platform_user_id or "").strip():
                        profile.platform_user_id = uid
                        session.add(profile)
                    if nickname and nickname != (profile.nickname or "").strip():
                        profile.nickname = nickname
                        session.add(profile)

                await session.commit()
                await session.refresh(item)

                try:
                    from server.models import MediaAccount

                    acc_res = await session.exec(
                        select(MediaAccount)
                        .where(MediaAccount.profile_id == profile.id)
                        .order_by(MediaAccount.updated_at.desc())
                        .limit(1)
                    )
                    acc = acc_res.first()
                    if acc:
                        acc.latest_session_id = item.id
                        acc.status = "connected"
                        if isinstance(auth_meta, dict):
                            nn = str(auth_meta.get("nickname") or "").strip()
                            if nn and nn != (acc.nickname or "").strip():
                                acc.nickname = nn
                        try:
                            acc.auth_json = json.dumps({"cookies": cookies}, ensure_ascii=False)
                        except Exception:
                            acc.auth_json = None
                        acc.updated_at = datetime.utcnow()
                        session.add(acc)
                        await session.commit()
                except Exception:
                    pass

                run.status = "success"
                run.session_id = item.id
                run.error = None
                run.meta = {"user_data_dir": str(user_data_dir)}
                run.finished_at = datetime.utcnow()
                session.add(run)
                await session.commit()
                logger.info("qr login success run_id=%s platform=%s session_id=%s", login_run_id, platform, item.id)
            finally:
                await context.close()
                await pw.stop()
        except Exception as e:
            run.status = "timeout" if isinstance(e, TimeoutError) else "failed"
            run.finished_at = datetime.utcnow()
            run.error = str(e)
            session.add(run)
            await session.commit()
            logger.exception("qr login failed run_id=%s", login_run_id)


async def create_qr_login(profile_id: int, *, timeout_sec: int = 300) -> MktLoginRun:
    async with db.AsyncSessionLocal() as session:
        run = MktLoginRun(profile_id=profile_id, status="running", meta={"timeout_sec": int(timeout_sec)})
        session.add(run)
        await session.commit()
        await session.refresh(run)
    asyncio.create_task(_run_qr_login(run.id, timeout_sec=timeout_sec))
    return run


async def get_latest_login_run(profile_id: int) -> MktLoginRun | None:
    async with db.AsyncSessionLocal() as session:
        res = await session.exec(
            select(MktLoginRun).where(MktLoginRun.profile_id == profile_id).order_by(MktLoginRun.started_at.desc()).limit(1)
        )
        return res.first()

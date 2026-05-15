from __future__ import annotations

import asyncio
import json
import random
import os
import subprocess
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx

from server.marketing.search import VideoItem, _extract_xhs_note_items, _xhs_note_to_video


def _hex_id(n: int) -> str:
    alphabet = "0123456789abcdef"
    return "".join(random.choice(alphabet) for _ in range(int(n)))


def _cookies_to_header(cookies: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for c in cookies:
        if not isinstance(c, dict):
            continue
        name = str(c.get("name") or "").strip()
        value = c.get("value")
        if not name or value is None:
            continue
        parts.append(f"{name}={value}")
    return "; ".join(parts)


def _cookie_value(cookies: list[dict[str, Any]], name: str) -> str | None:
    name = (name or "").strip()
    for c in cookies:
        if not isinstance(c, dict):
            continue
        if str(c.get("name") or "").strip() == name:
            v = c.get("value")
            return str(v) if v is not None else None
    return None


def _node_json_last_line(stdout: str) -> dict[str, Any]:
    for line in reversed([x.strip() for x in (stdout or "").splitlines() if x.strip()]):
        if line.startswith("{") and line.endswith("}"):
            return json.loads(line)
    raise RuntimeError("node 输出中未找到 JSON")


def _node_last_line(stdout: str) -> str:
    for line in reversed([x.strip() for x in (stdout or "").splitlines() if x.strip()]):
        return line
    return ""


def _run_node(*, cwd: Path, code: str, args: list[str], timeout_sec: int) -> str:
    p = subprocess.run(
        ["node", "-e", code, *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=float(timeout_sec),
        env=os.environ.copy(),
    )
    out = (p.stdout or "").strip()
    err = (p.stderr or "").strip()
    if p.returncode != 0:
        raise RuntimeError(err or out or f"node exit={p.returncode}")
    return out or err


async def xhs_search_notes(
    *,
    session_data: dict[str, Any],
    keyword: str,
    page: int,
    timeout_ms: int,
) -> list[VideoItem]:
    keyword = (keyword or "").strip()
    if not keyword:
        return []
    page = max(1, int(page or 1))

    auth = session_data.get("auth") if isinstance(session_data, dict) else None
    cookies = (auth.get("cookies") if isinstance(auth, dict) else None) or []
    if not isinstance(cookies, list) or len(cookies) == 0:
        raise ValueError("会话 cookies 为空，请先扫码登录")

    a1 = _cookie_value(cookies, "a1")
    if not a1:
        raise ValueError("会话缺少 a1 cookie，请重新扫码登录小红书")

    client = session_data.get("client") if isinstance(session_data, dict) else None
    user_agent = (client.get("user_agent") if isinstance(client, dict) else None) or ""
    user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"

    api = "/api/sns/web/v1/search/notes"
    body: dict[str, Any] = {
        "keyword": keyword,
        "page": page,
        "page_size": 20,
        "search_id": _hex_id(21),
        "sort": "general",
        "note_type": 0,
        "ext_flags": [],
        "filters": [],
        "geo": "",
        "image_formats": ["jpg", "webp", "avif"],
    }

    noctua_api_dir = Path(__file__).resolve().parents[2] / "xiaots" / "project" / "noctua_api"
    xs_code = """
      const mod = require('./static/xhs_xs_xsc_56.js');
      const api = process.argv[1];
      const data = JSON.parse(process.argv[2]);
      const a1 = process.argv[3];
      const method = process.argv[4];
      const r = mod.get_request_headers_params(api, data, a1, method);
      console.log(JSON.stringify(r));
    """.strip()
    trace_code = """
      require('./static/xhs_xray.js');
      console.log(traceId());
    """.strip()

    xs_out = await asyncio.to_thread(
        _run_node,
        cwd=noctua_api_dir,
        code=xs_code,
        args=[api, json.dumps(body, ensure_ascii=True), a1, "POST"],
        timeout_sec=max(5, int(timeout_ms / 1000)),
    )
    sig = _node_json_last_line(xs_out)
    xray_out = await asyncio.to_thread(
        _run_node,
        cwd=noctua_api_dir,
        code=trace_code,
        args=[],
        timeout_sec=max(5, int(timeout_ms / 1000)),
    )
    x_xray_traceid = _node_last_line(xray_out)

    cookie_header = _cookies_to_header(cookies)
    kw_q = quote(keyword)
    headers = {
        "authority": "edith.xiaohongshu.com",
        "accept": "application/json, text/plain, */*",
        "accept-language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
        "cache-control": "no-cache",
        "content-type": "application/json;charset=UTF-8",
        "origin": "https://www.xiaohongshu.com",
        "pragma": "no-cache",
        "referer": f"https://www.xiaohongshu.com/search_result?keyword={kw_q}",
        "sec-ch-ua": "\"Not A(Brand\";v=\"99\", \"Chromium\";v=\"122\", \"Google Chrome\";v=\"122\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "\"Mac OS\"",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-site",
        "user-agent": user_agent,
        "cookie": cookie_header,
        "x-s": str(sig.get("xs") or ""),
        "x-t": str(sig.get("xt") or ""),
        "x-s-common": str(sig.get("xs_common") or sig.get("xsCommon") or ""),
        "x-b3-traceid": _hex_id(16),
        "x-mns": "unload",
        "x-xray-traceid": x_xray_traceid,
    }

    url = "https://edith.xiaohongshu.com" + api
    async with httpx.AsyncClient(timeout=httpx.Timeout(timeout_ms / 1000), trust_env=False) as client:
        r = await client.post(url, headers=headers, content=json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
        r.raise_for_status()
        data = r.json()

    if isinstance(data, dict) and data.get("success") is not True:
        code = data.get("code")
        msg = data.get("msg") or data.get("message") or "xhs 请求失败"
        raise ValueError(f"xhs 请求失败: code={code} msg={msg}")

    notes = _extract_xhs_note_items(data)
    out: list[VideoItem] = []
    for n in notes:
        v = _xhs_note_to_video(n)
        if v:
            out.append(v)
    return out

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from local_agent.playwright_tasks import collect_content_metrics
from local_agent.platform_id import guess_platform
from local_agent.task_queue import TaskQueue


def _env(name: str, default: str | None = None) -> str | None:
    v = os.getenv(name)
    if v is None:
        return default
    v = v.strip()
    return v or default


@dataclass(slots=True)
class AgentConfig:
    server_base_url: str
    executor_token: str
    user_data_dir: str
    headless: bool
    slow_mo_ms: int
    concurrency: int


def load_config() -> AgentConfig:
    server_base_url = _env("AGENT_SERVER_BASE_URL", "http://127.0.0.1:8000")  # 你的 server
    executor_token = _env("AGENT_EXECUTOR_TOKEN", "") or ""
    user_data_dir = _env("AGENT_USER_DATA_DIR", "./.agent_profile") or "./.agent_profile"
    headless = (_env("AGENT_HEADLESS", "false") or "false").lower() in {"1", "true", "yes"}
    slow_mo_ms = int(_env("AGENT_SLOW_MO_MS", "200") or "200")
    concurrency = int(_env("AGENT_CONCURRENCY", "1") or "1")
    if not executor_token:
        raise RuntimeError("缺少 AGENT_EXECUTOR_TOKEN（先在 Server 后台创建 executor 并复制 token）")
    return AgentConfig(
        server_base_url=server_base_url.rstrip("/"),
        executor_token=executor_token,
        user_data_dir=user_data_dir,
        headless=headless,
        slow_mo_ms=slow_mo_ms,
        concurrency=max(1, concurrency),
    )


cfg = load_config()
app = FastAPI(title="VectorMind Local Agent", version="0.1.0")
queue = TaskQueue(concurrency=cfg.concurrency)
queue.start()


@app.get("/health")
async def health():
    return {"ok": True, "ts": datetime.utcnow().isoformat() + "Z"}


class ChromeCollectReq(BaseModel):
    url: str
    title: str | None = None


@app.post("/api/chrome/collect")
async def chrome_collect(req: ChromeCollectReq):
    url = (req.url or "").strip()
    if not url:
        raise HTTPException(status_code=400, detail="url 不能为空")
    platform = guess_platform(url)
    if platform not in {"xhs", "douyin"}:
        raise HTTPException(status_code=400, detail="仅支持小红书/抖音页面")

    async def run_once() -> dict:
        payload = await collect_content_metrics(
            platform=platform,
            url=url,
            title=req.title,
            user_data_dir=cfg.user_data_dir,
            headless=cfg.headless,
            slow_mo_ms=cfg.slow_mo_ms,
        )
        # 先上传 artifacts（截图/录像），再入库
        artifacts = payload.pop("artifacts", []) or []
        uploaded: list[dict] = []
        async with httpx.AsyncClient(timeout=90) as client:
            for a in artifacts:
                try:
                    path = a.get("path")
                    kind = a.get("kind")
                    if not path or not kind:
                        continue
                    with open(path, "rb") as f:
                        rr = await client.post(
                            f"{cfg.server_base_url}/api/executors/artifacts",
                            headers={"X-Executor-Token": cfg.executor_token},
                            data={"kind": kind, "filename": os.path.basename(path)},
                            files={"file": (os.path.basename(path), f, "application/octet-stream")},
                        )
                    if rr.status_code < 400:
                        uploaded.append(rr.json())
                except Exception:
                    continue

            r = await client.post(
                f"{cfg.server_base_url}/api/marketing/ingest",
                json={"platform": platform, "payload": payload, "ensure_track_media": True},
                headers={"X-Executor-Token": cfg.executor_token},
            )
            if r.status_code >= 400:
                raise RuntimeError(f"server ingest failed: {r.status_code} {r.text}")
            return {"platform": platform, "ingest": r.json(), "artifacts": uploaded}

    task_id = queue.submit(run_once)
    return {"ok": True, "task_id": task_id}


@app.get("/api/tasks/{task_id}")
async def get_task(task_id: str):
    state = queue.get(task_id)
    if not state:
        raise HTTPException(status_code=404, detail="task not found")
    return {
        "id": state.id,
        "status": state.status,
        "created_at": state.created_at,
        "started_at": state.started_at,
        "finished_at": state.finished_at,
        "result": state.result,
        "error": state.error,
    }

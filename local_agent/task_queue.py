from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Awaitable, Callable, Dict, Optional


@dataclass(slots=True)
class TaskState:
    id: str
    status: str = "queued"  # queued/running/success/failed
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    started_at: str | None = None
    finished_at: str | None = None
    result: dict | None = None
    error: str | None = None


class TaskQueue:
    def __init__(self, *, concurrency: int = 1):
        self._queue: asyncio.Queue[tuple[str, Callable[[], Awaitable[dict]]]] = asyncio.Queue()
        self._tasks: Dict[str, TaskState] = {}
        self._sem = asyncio.Semaphore(max(1, int(concurrency)))
        self._workers: list[asyncio.Task] = []
        self._started = False

    def start(self, worker_count: int | None = None) -> None:
        if self._started:
            return
        self._started = True
        wc = worker_count or max(1, self._sem._value)  # noqa: SLF001
        for _ in range(max(1, wc)):
            self._workers.append(asyncio.create_task(self._worker()))

    def submit(self, fn: Callable[[], Awaitable[dict]]) -> str:
        task_id = uuid.uuid4().hex
        self._tasks[task_id] = TaskState(id=task_id)
        self._queue.put_nowait((task_id, fn))
        return task_id

    def get(self, task_id: str) -> Optional[TaskState]:
        return self._tasks.get(task_id)

    async def _worker(self) -> None:
        while True:
            task_id, fn = await self._queue.get()
            state = self._tasks.get(task_id)
            if not state:
                continue
            async with self._sem:
                state.status = "running"
                state.started_at = datetime.utcnow().isoformat() + "Z"
                try:
                    res = await fn()
                    state.status = "success"
                    state.result = res
                except Exception as e:  # noqa: BLE001
                    state.status = "failed"
                    state.error = str(e)
                finally:
                    state.finished_at = datetime.utcnow().isoformat() + "Z"
                    self._queue.task_done()


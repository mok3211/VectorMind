from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from book_recommendation.router import router as book_router
from deeplegacy.router import router as history_router
from morning_radio.router import router as radio_router
from travel_planner.router import router as travel_router

from server.config import settings
from server.api.media_accounts import router as media_accounts_router
from server.api.media_publish import router as media_publish_router
from server.api.prompts import router as prompts_router
from server.api.runs import router as runs_router
from server.api.skills import router as skills_router
from server.api.marketing import router as marketing_router
from server.api.marketing_ingest import router as marketing_ingest_router
from server.api.workflows import router as workflows_router
from server.api.executors import router as executors_router
from server.api.executor_artifacts import router as executor_artifacts_router
from server.api.rbac import router as rbac_router
from server.auth.router import router as auth_router
from server.auth.bootstrap import ensure_builtin_admin
from server.auth.rbac import ensure_rbac_defaults, ensure_user_has_role
from server.db import init_db
from server.db import AsyncSessionLocal
from server.publishers.registry import publisher_registry
from server.skills import register_builtin_skills
from server.workflows import register_workflows


@asynccontextmanager
async def lifespan(_: FastAPI):
    register_builtin_skills()
    register_workflows()
    await init_db()
    await ensure_builtin_admin()
    async with AsyncSessionLocal() as session:
        # RBAC/套餐初始化：若迁移未跑，不阻塞服务启动
        try:
            await ensure_rbac_defaults(session)
            from sqlalchemy import select
            from server.models import User

            res = await session.execute(select(User).where(User.is_admin == True).limit(1))  # noqa: E712
            admin_user = res.scalars().first()
            if admin_user:
                await ensure_user_has_role(session, user=admin_user, role_code="admin")
        except Exception:
            pass
    yield


app = FastAPI(title="AI 创意工作流", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"ok": True}


@app.get("/publishers")
async def list_publishers():
    return {"publishers": publisher_registry.list()}


app.include_router(radio_router)
app.include_router(book_router)
app.include_router(travel_router)
app.include_router(history_router)
app.include_router(auth_router)
app.include_router(runs_router)
app.include_router(media_accounts_router)
app.include_router(media_publish_router)
app.include_router(workflows_router)
app.include_router(skills_router)
app.include_router(prompts_router)
app.include_router(marketing_router)
app.include_router(marketing_ingest_router)
app.include_router(executors_router)
app.include_router(executor_artifacts_router)
app.include_router(rbac_router)

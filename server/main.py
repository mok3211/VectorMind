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
from server.api.marketing import router as marketing_router
from server.api.rbac import router as rbac_router
from server.api.llm import router as llm_router
from server.api.prompts import router as prompts_router
from server.api.runs import router as runs_router
from server.api.skills import router as skills_router
from server.api.workflows import router as workflows_router
from server.auth.router import router as auth_router
from server.auth.bootstrap import ensure_builtin_admin, ensure_builtin_menus
from server.db import init_db
from server.logging_utils import configure_logging, get_logger
from server.publishers.registry import publisher_registry
from server.skills import register_builtin_skills
from server.workflows import register_workflows

configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("service starting")
    register_builtin_skills()
    register_workflows()
    await init_db()
    await ensure_builtin_admin()
    await ensure_builtin_menus()
    logger.info("service startup complete")
    yield
    logger.info("service shutting down")


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
app.include_router(marketing_router)
app.include_router(rbac_router)
app.include_router(llm_router)
app.include_router(workflows_router)
app.include_router(skills_router)
app.include_router(prompts_router)

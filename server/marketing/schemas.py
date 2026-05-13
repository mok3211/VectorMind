from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ProfileCreate(BaseModel):
    platform: str = Field(..., description="xhs / douyin")
    profile_type: str = Field(default="owned", description="owned / competitor")
    platform_user_id: str | None = None
    sec_uid: str | None = None
    user_link: str | None = None
    nickname: str | None = None
    avatar_url: str | None = None
    signature: str | None = None
    location: str | None = None
    verify_type: int | None = 0
    verify_name: str | None = None
    status: str = "active"
    risk_status: str = "normal"
    meta: dict[str, Any] | None = None


class ProfileUpdate(BaseModel):
    platform_user_id: str | None = None
    sec_uid: str | None = None
    user_link: str | None = None
    nickname: str | None = None
    avatar_url: str | None = None
    signature: str | None = None
    location: str | None = None
    verify_type: int | None = None
    verify_name: str | None = None
    status: str | None = None
    risk_status: str | None = None
    meta: dict[str, Any] | None = None


class SessionImport(BaseModel):
    profile_id: int
    user_agent: str | None = Field(default=None, description="兼容字段；优先使用 session_data.client.user_agent")
    session_data: dict[str, Any] = Field(..., description="MarketingSession v1（自定义格式）")
    expires_at: datetime | None = None


class JobCreate(BaseModel):
    name: str
    platform: str
    job_type: str
    profile_id: int | None = None
    content_id: int | None = None
    params: dict[str, Any] | None = None
    cron: str | None = None
    enabled: bool = True


class TrackMediaCreate(BaseModel):
    platform: str
    platform_content_id: str
    url: str | None = None
    title: str | None = None
    sec_uid: str | None = None
    nickname: str | None = None
    source: str | None = None
    source_type: str = "external"
    create_user: str | None = None
    is_comment: bool = False
    meta: dict[str, Any] | None = None


class TrackCommentCreate(BaseModel):
    platform: str
    platform_content_id: str
    url: str | None = None
    title: str | None = None
    user_nickname: str | None = None
    create_user: str | None = None
    raw: dict[str, Any] | None = None


class InteractionSendCommentRequest(BaseModel):
    """
    真实发送评论（Playwright UI 操作）：
    - target：优先用 track_media_id，其次 url+platform_content_id
    - text：要发送的评论内容
    """

    platform: str
    text: str
    track_media_id: int | None = None
    url: str | None = None
    platform_content_id: str | None = None
    account_profile_id: int | None = None
    headless: bool | None = None
    slow_mo_ms: int | None = None

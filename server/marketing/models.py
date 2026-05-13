from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


class MktPlatformProfile(SQLModel, table=True):
    """
    平台账号/作者（owned/competitor 统一）。
    """

    __tablename__ = "mkt_platform_profiles"

    id: Optional[int] = Field(default=None, primary_key=True)

    platform: str = Field(index=True)  # xhs / douyin / ...
    profile_type: str = Field(default="owned", index=True)  # owned / competitor

    # 平台侧用户标识（不同平台可能不同）
    platform_user_id: str | None = Field(default=None, index=True)
    sec_uid: str | None = Field(default=None, index=True)

    user_link: str | None = Field(default=None, index=True)
    nickname: str | None = None
    avatar_url: str | None = None
    signature: str | None = Field(default=None, sa_column=Column(Text))
    location: str | None = None

    verify_type: int | None = Field(default=0)
    verify_name: str | None = None

    status: str = Field(default="active", index=True)  # active/disabled
    risk_status: str = Field(default="normal", index=True)  # normal/captcha/blocked/limited/unknown

    meta: dict | None = Field(default=None, sa_column=Column(JSONB))

    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime, nullable=False))
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime, nullable=False))


class MktPlatformSession(SQLModel, table=True):
    """
    登录会话（cookies + ua + device/verify 参数等）。
    注意：生产环境建议对 session_data 做应用层加密后再存。
    """

    __tablename__ = "mkt_platform_sessions"

    id: Optional[int] = Field(default=None, primary_key=True)
    profile_id: int = Field(sa_column=Column(Integer, ForeignKey("mkt_platform_profiles.id"), nullable=False, index=True))

    status: str = Field(default="valid", index=True)  # valid/expired/invalid
    last_validated_at: datetime | None = None
    expires_at: datetime | None = None

    user_agent: str | None = Field(default=None, sa_column=Column(Text))
    session_data: dict | None = Field(default=None, sa_column=Column(JSONB))

    last_error: str | None = Field(default=None, sa_column=Column(Text))

    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime, nullable=False))
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime, nullable=False))


class MktContent(SQLModel, table=True):
    """
    内容主表：小红书笔记 / 抖音视频。
    """

    __tablename__ = "mkt_contents"

    id: Optional[int] = Field(default=None, primary_key=True)

    platform: str = Field(index=True)
    profile_id: int | None = Field(default=None, sa_column=Column(Integer, ForeignKey("mkt_platform_profiles.id"), index=True))
    platform_content_id: str = Field(index=True)

    content_type: str = Field(default="content", index=True)  # note/video/...
    url: str | None = Field(default=None, sa_column=Column(String(512)))
    title: str | None = Field(default=None, sa_column=Column(String(1024)))
    description: str | None = Field(default=None, sa_column=Column(Text))
    published_at: datetime | None = Field(default=None, sa_column=Column(DateTime))

    source: str | None = Field(default=None, index=True)  # 来源关键词/榜单等
    tags: list[str] | None = Field(default=None, sa_column=Column(JSONB))
    raw: dict | None = Field(default=None, sa_column=Column(JSONB))

    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime, nullable=False))
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime, nullable=False))

    __table_args__ = (
        Index("ux_mkt_contents_platform_content_id", "platform", "platform_content_id", unique=True),
    )


class MktContentMetricSnapshot(SQLModel, table=True):
    """
    内容指标快照（时序）。
    """

    __tablename__ = "mkt_content_metric_snapshots"

    id: Optional[int] = Field(default=None, primary_key=True)
    content_id: int = Field(sa_column=Column(Integer, ForeignKey("mkt_contents.id"), nullable=False, index=True))
    captured_at: datetime = Field(sa_column=Column(DateTime, nullable=False, index=True))

    view_count: int | None = Field(default=None)
    like_count: int | None = Field(default=None)
    comment_count: int | None = Field(default=None)
    collect_count: int | None = Field(default=None)
    share_count: int | None = Field(default=None)

    metrics: dict | None = Field(default=None, sa_column=Column(JSONB))

    __table_args__ = (
        Index("ux_mkt_content_metric_snapshots", "content_id", "captured_at", unique=True),
    )


class MktProfileMetricSnapshot(SQLModel, table=True):
    """
    账号指标快照（时序）。
    """

    __tablename__ = "mkt_profile_metric_snapshots"

    id: Optional[int] = Field(default=None, primary_key=True)
    profile_id: int = Field(sa_column=Column(Integer, ForeignKey("mkt_platform_profiles.id"), nullable=False, index=True))
    captured_at: datetime = Field(sa_column=Column(DateTime, nullable=False, index=True))

    fans: int | None = Field(default=None)
    follows: int | None = Field(default=None)
    interaction: int | None = Field(default=None)
    contents_count: int | None = Field(default=None)

    metrics: dict | None = Field(default=None, sa_column=Column(JSONB))

    __table_args__ = (
        Index("ux_mkt_profile_metric_snapshots", "profile_id", "captured_at", unique=True),
    )


class MktComment(SQLModel, table=True):
    __tablename__ = "mkt_comments"

    id: Optional[int] = Field(default=None, primary_key=True)
    platform: str = Field(index=True)
    content_id: int = Field(sa_column=Column(Integer, ForeignKey("mkt_contents.id"), nullable=False, index=True))
    platform_comment_id: str = Field(index=True)

    parent_comment_id: str | None = Field(default=None, index=True)
    user_sec_uid: str | None = Field(default=None, index=True)
    nickname: str | None = None
    location: str | None = None
    content: str | None = Field(default=None, sa_column=Column(Text))
    like_count: int | None = None
    sub_comment_count: int | None = None
    pictures: list[str] | None = Field(default=None, sa_column=Column(JSONB))
    created_at_platform: datetime | None = Field(default=None, sa_column=Column(DateTime))

    raw: dict | None = Field(default=None, sa_column=Column(JSONB))

    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime, nullable=False))
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime, nullable=False))

    __table_args__ = (
        Index("ux_mkt_comments_platform_comment_id", "platform", "platform_comment_id", unique=True),
    )


class MktJob(SQLModel, table=True):
    """
    采集任务定义（支持定时/手动触发）。
    """

    __tablename__ = "mkt_jobs"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    platform: str = Field(index=True)
    job_type: str = Field(index=True)  # profile_sync/content_search/content_metrics/comment_sync/keyword_snapshot/...

    # 目标对象（可空：关键词/榜单任务）
    profile_id: int | None = Field(default=None, sa_column=Column(Integer, ForeignKey("mkt_platform_profiles.id"), index=True))
    content_id: int | None = Field(default=None, sa_column=Column(Integer, ForeignKey("mkt_contents.id"), index=True))

    params: dict | None = Field(default=None, sa_column=Column(JSONB))
    cron: str | None = None  # 仅存 cron 表达式（执行由调度器/外部触发）
    enabled: bool = Field(default=True, index=True)

    created_by_user_id: int | None = Field(default=None, sa_column=Column(Integer, ForeignKey("users.id"), index=True))

    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime, nullable=False))
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime, nullable=False))


class MktJobRun(SQLModel, table=True):
    __tablename__ = "mkt_job_runs"

    id: Optional[int] = Field(default=None, primary_key=True)
    job_id: int = Field(sa_column=Column(Integer, ForeignKey("mkt_jobs.id"), nullable=False, index=True))

    status: str = Field(default="running", index=True)  # running/success/failed
    started_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime, nullable=False, index=True))
    finished_at: datetime | None = Field(default=None, sa_column=Column(DateTime, index=True))

    error: str | None = Field(default=None, sa_column=Column(Text))
    stats: dict | None = Field(default=None, sa_column=Column(JSONB))


class MktTrackMedia(SQLModel, table=True):
    """
    内容监控池（对齐 noctua: track_media 的“待更新/定期刷新/重要内容/评论维护”语义）。
    说明：
    - 不是 raw 抓取结果（raw 抓取结果在 mkt_contents / snapshots / comments）
    - 这里是“运营动作入口 + 追踪状态机”
    """

    __tablename__ = "mkt_track_media"

    id: Optional[int] = Field(default=None, primary_key=True)
    platform: str = Field(index=True)

    # 对齐 noctua 的 media_id（平台内容id）；为了独立于 mkt_contents，也保留一份
    platform_content_id: str = Field(index=True)
    content_id: int | None = Field(default=None, sa_column=Column(Integer, ForeignKey("mkt_contents.id"), index=True))

    url: str | None = Field(default=None, sa_column=Column(String(512)))
    title: str | None = Field(default=None, sa_column=Column(String(1024)))
    sec_uid: str | None = Field(default=None, index=True)  # 作者 sec_uid（如可得）
    nickname: str | None = None

    source: str | None = Field(default=None, index=True)  # 来源关键词/榜单/导入批次等
    source_type: str = Field(default="external", index=True)  # external/internal
    create_user: str | None = Field(default=None, index=True)

    # 评论维护开关（noctua: is_comment）
    is_comment: bool = Field(default=False, index=True)

    # 追踪状态（noctua: status 0/1/2）
    status: int = Field(default=0, index=True)  # 0 pending, 1 updated, 2 failed
    last_track_at: datetime | None = Field(default=None, sa_column=Column(DateTime, index=True))
    last_error: str | None = Field(default=None, sa_column=Column(Text))

    # 最新一份指标冗余（便于列表排序/筛选）
    like_count: int | None = Field(default=None, index=True)
    comment_count: int | None = Field(default=None, index=True)
    share_count: int | None = Field(default=None, index=True)
    collect_count: int | None = Field(default=None, index=True)

    # 额外字段（用于对齐 noctua 的 input_payload/payment_amount 等扩展）
    meta: dict | None = Field(default=None, sa_column=Column(JSONB))

    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime, nullable=False))
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime, nullable=False))

    __table_args__ = (
        Index("ux_mkt_track_media_platform_content_id", "platform", "platform_content_id", unique=True),
    )


class MktTrackComment(SQLModel, table=True):
    """
    评论监控池（对齐 noctua: track_comment 的语义）。
    """

    __tablename__ = "mkt_track_comments"

    id: Optional[int] = Field(default=None, primary_key=True)
    platform: str = Field(index=True)

    platform_content_id: str = Field(index=True)  # media_id
    content_id: int | None = Field(default=None, sa_column=Column(Integer, ForeignKey("mkt_contents.id"), index=True))
    url: str | None = Field(default=None, sa_column=Column(String(512)))
    title: str | None = Field(default=None, sa_column=Column(String(1024)))

    user_nickname: str | None = Field(default=None, index=True)
    create_user: str | None = Field(default=None, index=True)

    track_status: int = Field(default=0, index=True)  # 0 pending 1 updated 2 failed
    last_track_at: datetime | None = Field(default=None, sa_column=Column(DateTime, index=True))
    last_error: str | None = Field(default=None, sa_column=Column(Text))
    is_deleted: bool = Field(default=False, index=True)

    raw: dict | None = Field(default=None, sa_column=Column(JSONB))

    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime, nullable=False))
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime, nullable=False))

    __table_args__ = (
        Index("ix_mkt_track_comments_platform_content_id", "platform", "platform_content_id", unique=False),
    )


class MktInteractionRecord(SQLModel, table=True):
    """
    互动审计表（对齐 noctua: interaction_record）。
    用于记录：评论/私信/点赞等动作的结果、原因、执行账号等。
    """

    __tablename__ = "mkt_interaction_records"

    id: Optional[int] = Field(default=None, primary_key=True)
    platform: str = Field(index=True)
    event_type: str = Field(index=True)  # send_comment / send_message / like / ...

    # 使用哪个自有账号执行（可空：由平台自动挑选或外部执行器执行）
    account_profile_id: int | None = Field(default=None, sa_column=Column(Integer, ForeignKey("mkt_platform_profiles.id"), index=True))

    target: str = Field(index=True)  # 目标id（media_id / sec_uid / comment_id）
    payload: str = Field(sa_column=Column(Text))  # 发出去的内容/参数
    source: str | None = Field(default=None, sa_column=Column(Text))  # 来源（标题/关键词/任务）

    status: bool = Field(default=False, index=True)
    reason: str | None = Field(default=None, sa_column=Column(Text))

    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime, nullable=False, index=True))
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime, nullable=False))


class MktInteractionJob(SQLModel, table=True):
    """
    互动任务（对齐 noctua 的“发送队列/批量执行”能力）。
    """

    __tablename__ = "mkt_interaction_jobs"

    id: Optional[int] = Field(default=None, primary_key=True)
    platform: str = Field(index=True)
    event_type: str = Field(index=True)  # send_comment / send_message / ...
    status: str = Field(default="pending", index=True)  # pending/running/success/failed

    # 执行账号（可空：后续做账号池选择策略）
    account_profile_id: int | None = Field(default=None, sa_column=Column(Integer, ForeignKey("mkt_platform_profiles.id"), index=True))

    # 目标（可批量）
    targets: list[dict] = Field(default_factory=list, sa_column=Column(JSONB))
    payload: dict | None = Field(default=None, sa_column=Column(JSONB))  # 例如评论文本模板、topic 等

    stats: dict | None = Field(default=None, sa_column=Column(JSONB))
    error: str | None = Field(default=None, sa_column=Column(Text))

    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime, nullable=False, index=True))
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(DateTime, nullable=False))

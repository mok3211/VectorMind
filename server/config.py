from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    全局配置：用环境变量驱动，做到“切换模型/切换提示词版本”无需改代码。
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # 数据库
    database_url: str | None = None

    # JWT
    jwt_secret: str = "please_change_me"
    jwt_expire_minutes: int = 60 * 24 * 7  # 7 天

    # CORS
    cors_origins: str = "http://127.0.0.1:5173"

    # 默认模型（LiteLLM model string）
    llm_model_default: str = "gpt-4o-mini"

    # agent 覆盖模型（可选）
    morning_radio_model: str | None = None
    book_recommendation_model: str | None = None
    travel_planner_model: str | None = None
    morning_history_model: str | None = None

    # prompt 版本（可选）
    morning_radio_prompt_version: str = "v1"
    book_recommendation_prompt_version: str = "v1"
    travel_planner_prompt_version: str = "v1"
    morning_history_prompt_version: str = "v1"


settings = Settings()

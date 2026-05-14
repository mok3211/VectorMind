from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    全局配置：用环境变量驱动，做到“切换模型/切换提示词版本”无需改代码。
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # 数据库
    database_url: str = "sqlite+aiosqlite:///./dev.db"

    # JWT
    jwt_secret: str = "please_change_me"
    jwt_expire_minutes: int = 60 * 24 * 7  # 7 天

    # CORS
    cors_origins: str = "http://127.0.0.1:5173"

    # NVIDIA NIM API Key（LiteLLM: NVIDIA_NIM_API_KEY）
    nvidia_nim_api_key: str | None = None

    # 兼容字段：若你习惯用 NVIDIA_API_KEY，这里也可以填（会映射到 NVIDIA_NIM_API_KEY）
    nvidia_api_key: str | None = None

    # 默认模型（LiteLLM model string）
    llm_model_default: str = "meta/llama-3.1-70b-instruct"

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

    bootstrap_admin_enabled: bool = True
    bootstrap_admin_identifier: str = "zhangchi"
    bootstrap_admin_password: str = "zhangchi2026"
    bootstrap_admin_force_reset: bool = False


settings = Settings()

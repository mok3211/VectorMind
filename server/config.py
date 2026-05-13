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

    # NVIDIA API（LangChain ChatNVIDIA）
    nvidia_api_key: str | None = None

    # 默认模型（NVIDIA NIM model string）
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

    # 新媒体自动化发布
    media_profile_root: str = ".media_profiles"

    # 启动时自动创建内置管理员（仅当 users 表为空）
    bootstrap_admin_enabled: bool = True
    bootstrap_admin_identifier: str = "zhangchi"
    bootstrap_admin_password: str = "zhangchi2026"
    # 若为 true：启动时会强制重置内置管理员密码（仅用于开发环境）
    # 为了避免“库里已有旧账号/旧 hash 导致一直登录失败”，这里默认开启。
    bootstrap_admin_force_reset: bool = True

    # Marketing crawler mode: playwright / mock（不建议）
    marketing_crawler_mode: str = "playwright"

    # Playwright 运行参数（真实抓取）
    marketing_playwright_headless: bool = True
    marketing_playwright_slow_mo_ms: int = 0


settings = Settings()

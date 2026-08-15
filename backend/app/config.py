from functools import lru_cache
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Research Data Platform"
    environment: str = "development"
    secret_key: str = ""
    jwt_expire_minutes: int = 1440
    database_url: str = "sqlite:///./research.db"
    redis_url: str = "redis://localhost:6379/0"
    storage_root: str = "./storage"
    max_upload_bytes: int = 200 * 1024 * 1024
    run_tasks_inline: bool = True
    default_llm: str = "mock"
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_api_key: str = ""
    deepseek_model: str = "deepseek-chat"
    qwen_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    qwen_api_key: str = ""
    qwen_model: str = "qwen-plus"
    kimi_base_url: str = "https://api.moonshot.cn/v1"
    kimi_api_key: str = ""
    kimi_model: str = "moonshot-v1-8k"
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "research-platform@localhost"
    agent_token: str = ""
    backup_root: str = "./storage/backups"
    backup_retention_days: int = 14
    ocr_enabled: bool = False
    grobid_url: str = "http://localhost:8070"
    grobid_enabled: bool = False
    supplement_download_enabled: bool = True
    outbound_allowed_hosts: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    @model_validator(mode="after")
    def validate_secrets(self):
        if len(self.secret_key) < 32 or self.secret_key.startswith(("change-me", "local-development", "generate-")):
            raise ValueError("SECRET_KEY must be a configured random value of at least 32 characters")
        if len(self.agent_token) < 24 or self.agent_token.startswith(("change-me", "local-development", "generate-")):
            raise ValueError("AGENT_TOKEN must be a configured random value of at least 24 characters")
        return self

    @property
    def storage_path(self) -> Path:
        path = Path(self.storage_root)
        path.mkdir(parents=True, exist_ok=True)
        for child in ("uploads", "converted", "parsed", "exports", "code", "reviews", "logs", "backups"):
            (path / child).mkdir(parents=True, exist_ok=True)
        return path


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

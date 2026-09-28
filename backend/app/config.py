from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://checker:checker@postgres:5432/checker"
    storage_dir: str = "/app/storage"
    redis_url: str = "redis://redis:6379/0"
    dev_auto_create_tables: bool = False

    gigachat_client_id: str = ""
    gigachat_client_secret: str = ""
    gigachat_auth_key: str = ""
    gigachat_scope: str = "GIGACHAT_API_CORP"
    gigachat_model: str = "GigaChat-2-Max"
    gigachat_verify_ssl_certs: bool = False

    bot_notify_url: str = "http://bot:3001/internal/notify"

    max_bot_token: str = ""

    @property
    def gigachat_credentials(self) -> str:
        if self.gigachat_auth_key:
            return self.gigachat_auth_key
        if self.gigachat_client_id and self.gigachat_client_secret:
            import base64
            raw = f"{self.gigachat_client_id}:{self.gigachat_client_secret}"
            return base64.b64encode(raw.encode()).decode()
        return ""


settings = Settings()

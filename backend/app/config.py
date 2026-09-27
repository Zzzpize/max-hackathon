from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://checker:checker@postgres:5432/checker"
    storage_dir: str = "/app/storage"

    gigachat_auth_key: str = ""
    gigachat_scope: str = "GIGACHAT_API_CORP"
    gigachat_model: str = "GigaChat-2-Max"
    gigachat_verify_ssl_certs: bool = False


settings = Settings()

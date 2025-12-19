from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "dev"
    service_name: str = "service"
    host: str = "0.0.0.0"
    port: int = 8000

    cors_allow_origins: str = "*"
    jwt_secret: str = "dev-secret-change-me"
    jwt_issuer: str = "micro-task"
    jwt_audience: str = "micro-task-users"
    jwt_exp_minutes: int = 60

    # tracing
    otel_exporter_otlp_endpoint: str | None = None  # e.g. http://jaeger:4318
    otel_service_namespace: str = "micro-task"

    # DB
    database_url: str = "sqlite:///./app.db"

    # gateway upstreams
    users_service_url: str = "http://service_users:8001"
    orders_service_url: str = "http://service_orders:8002"

    # rate limit
    rate_limit: str = "60/minute"  # default for gateway

    disable_user_check: bool = False

settings = Settings()

"""Application configuration using Pydantic settings."""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = Field(default="SmartTodo", description="Application name")
    debug: bool = Field(default=False, description="Debug mode")
    environment: Literal["development", "production", "test"] = Field(
        default="development", description="Environment"
    )

    # Server
    host: str = Field(default="0.0.0.0", description="Host to bind to")
    port: int = Field(default=8000, description="Port to bind to")
    reload: bool = Field(default=False, description="Auto-reload on code changes")

    # Database
    database_url: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/smart_todo",
        description="Database connection URL (PostgreSQL or SQLite)",
    )
    db_pool_size: int = Field(default=10, description="Database connection pool size")
    db_max_overflow: int = Field(default=20, description="Database max overflow connections")
    db_echo: bool = Field(default=False, description="Echo SQL statements")

    # Security
    secret_key: str = Field(
        default="your-secret-key-change-this-in-production-at-least-32-chars-long",
        description="Secret key for signing tokens (64+ chars recommended)",
        min_length=32,
    )
    algorithm: str = Field(default="HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(
        default=30, description="Access token expiration in minutes"
    )
    session_token_expire_days: int = Field(
        default=14, description="Session token expiration in days"
    )
    session_token_rotation_days: int = Field(
        default=7, description="Days before session token rotation"
    )
    password_min_length: int = Field(default=12, description="Minimum password length")
    password_max_length: int = Field(default=72, description="Maximum password length")

    # CORS
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        description="Allowed CORS origins",
    )

    # LLM Configuration
    llm_provider: Literal["openrouter", "openai"] = Field(
        default="openrouter", description="LLM provider"
    )
    llm_base_url: str = Field(
        default="https://openrouter.ai/api/v1", description="LLM API base URL"
    )
    llm_api_key: str = Field(default="", description="LLM API key")
    llm_model: str = Field(default="anthropic/claude-3.5-sonnet", description="LLM model to use")
    llm_timeout: int = Field(default=600, description="LLM request timeout in seconds")
    llm_max_retries: int = Field(default=3, description="Maximum LLM request retries")
    llm_temperature: float = Field(default=0.7, description="LLM temperature")

    # OpenRouter specific
    openrouter_app_name: str = Field(default="SmartTodo", description="App name for OpenRouter")
    openrouter_site_url: str = Field(
        default="https://github.com/yourusername/smart-todo",
        description="Site URL for OpenRouter",
    )

    # State Machine
    max_conversation_rounds: int = Field(default=20, description="Max conversation rounds with LLM")
    max_command_errors: int = Field(
        default=3, description="Max command errors before session termination"
    )

    # OpenTelemetry
    otel_enabled: bool = Field(default=True, description="Enable OpenTelemetry")
    otel_service_name: str = Field(default="smart-todo", description="Service name for traces")
    otel_exporter_otlp_endpoint: str = Field(
        default="http://localhost:4318", description="OTLP exporter endpoint"
    )
    otel_exporter_otlp_protocol: Literal["grpc", "http/protobuf"] = Field(
        default="http/protobuf", description="OTLP protocol"
    )
    otel_exporter_otlp_headers: str = Field(
        default="", description="OTLP headers (comma-separated key=value pairs)"
    )
    otel_resource_attributes: str = Field(
        default="", description="Resource attributes (comma-separated key=value pairs)"
    )
    otel_traces_exporter: Literal["otlp", "console", "none"] = Field(
        default="otlp", description="Traces exporter"
    )
    otel_metrics_exporter: Literal["otlp", "console", "none"] = Field(
        default="otlp", description="Metrics exporter"
    )
    otel_logs_exporter: Literal["otlp", "console", "none"] = Field(
        default="otlp", description="Logs exporter"
    )

    # Phoenix-specific (legacy compatibility)
    phoenix_api_key: str = Field(default="", description="Phoenix API key")
    phoenix_collector_endpoint: str = Field(default="", description="Phoenix collector endpoint")

    def get_otlp_headers(self) -> dict[str, str]:
        """Parse OTLP headers from comma-separated string."""
        if not self.otel_exporter_otlp_headers:
            headers = {}
        else:
            headers = dict(
                item.split("=", 1)
                for item in self.otel_exporter_otlp_headers.split(",")
                if "=" in item
            )

        # Add Phoenix API key if provided
        if self.phoenix_api_key:
            headers["Authorization"] = f"Bearer {self.phoenix_api_key}"

        return headers

    def get_resource_attributes(self) -> dict[str, str]:
        """Parse resource attributes from comma-separated string."""
        if not self.otel_resource_attributes:
            return {}
        return dict(
            item.split("=", 1) for item in self.otel_resource_attributes.split(",") if "=" in item
        )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

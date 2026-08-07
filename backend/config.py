from __future__ import annotations

from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_ROOT = Path(__file__).resolve().parent
DEFAULT_SCOPES = (
    "openid "
    "dpv:RequestedServiceProvision#quality-on-demand:sessions:create "
    "dpv:FraudPreventionAndDetection#number-verification:verify"
)


class Settings(BaseSettings):
    opengw_api_root: str = Field(
        default="https://opengateway.turkcell.com.tr",
        validation_alias=AliasChoices("OPENGW_API_ROOT", "OGW_API_GATEWAY_URL"),
    )
    opengw_client_id: str = Field(
        default="", validation_alias=AliasChoices("OPENGW_CLIENT_ID", "OGW_CLIENT_ID", "CLIENT_ID")
    )
    opengw_client_secret: str = Field(
        default="",
        validation_alias=AliasChoices("OPENGW_CLIENT_SECRET", "OGW_CLIENT_SECRET", "CLIENT_SECRET"),
    )
    opengw_redirect_uri: str = Field(
        default="http://localhost:8000/api/auth/callback",
        validation_alias=AliasChoices("OPENGW_REDIRECT_URI", "BACKEND_CALLBACK_URL"),
    )
    opengw_scopes: str = Field(default=DEFAULT_SCOPES, validation_alias="OPENGW_SCOPES")
    opengw_qos_profile: str = Field(
        default="teknofest2026", validation_alias="OPENGW_QOS_PROFILE"
    )
    opengw_timeout_seconds: float = Field(default=15.0, validation_alias="OPENGW_TIMEOUT_SECONDS")

    final_ai_image: str = Field(
        default="teknofest-2026/qode-final:2026.08-p4",
        validation_alias=AliasChoices("FINAL_AI_IMAGE", "DOCKER_IMAGE_NAME"),
    )
    final_job_root: Path = Field(
        default=PROJECT_ROOT / "data" / "jobs", validation_alias="FINAL_JOB_ROOT"
    )
    use_gpu: bool = Field(default=False, validation_alias="USE_GPU")
    container_timeout_seconds: int = Field(default=570, validation_alias="CONTAINER_TIMEOUT_SECONDS")
    max_upload_bytes: int = Field(default=1_500_000_000, validation_alias="MAX_UPLOAD_BYTES")
    max_job_disk_bytes: int = Field(default=10_000_000_000, validation_alias="MAX_JOB_DISK_BYTES")
    job_ttl_seconds: int = Field(default=86_400, validation_alias="JOB_TTL_SECONDS")
    auth_state_ttl_seconds: int = Field(default=300, validation_alias="AUTH_STATE_TTL_SECONDS")
    session_ttl_seconds: int = Field(default=3600, validation_alias="SESSION_TTL_SECONDS")
    allowed_origins: str = Field(
        default="http://localhost,http://127.0.0.1", validation_alias="ALLOWED_ORIGINS"
    )

    model_config = SettingsConfigDict(
        env_file=(PROJECT_ROOT / ".env", BACKEND_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    @property
    def cors_origins(self) -> list[str]:
        return [value.strip() for value in self.allowed_origins.split(",") if value.strip()]

    def require_gateway_config(self) -> None:
        missing = [
            name
            for name, value in (
                ("OPENGW_CLIENT_ID", self.opengw_client_id),
                ("OPENGW_CLIENT_SECRET", self.opengw_client_secret),
                ("OPENGW_REDIRECT_URI", self.opengw_redirect_uri),
                ("OPENGW_SCOPES", self.opengw_scopes),
                ("OPENGW_QOS_PROFILE", self.opengw_qos_profile),
            )
            if not str(value).strip()
        ]
        if missing:
            raise RuntimeError(f"Open Gateway configuration is incomplete: {', '.join(missing)}")


settings = Settings()

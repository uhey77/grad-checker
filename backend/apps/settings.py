"""起動時に読み込む環境設定。"""

from pathlib import Path
from urllib.parse import urlsplit

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_DATABASE_PATH = Path(__file__).resolve().parents[1] / "data" / "grad_checker.db"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        frozen=True, case_sensitive=True, populate_by_name=True
    )

    # 起動ディレクトリにかかわらずbackend/dataへ保存する。
    database_url: str = Field(
        default=f"sqlite:///{DEFAULT_DATABASE_PATH}",
        validation_alias="DATABASE_URL",
    )
    direct_database_url: str | None = Field(
        default=None, validation_alias="DIRECT_DATABASE_URL"
    )
    auth_session_hours: int = Field(
        default=24, ge=1, validation_alias="AUTH_SESSION_HOURS"
    )
    auth_password_min_length: int = Field(
        default=12, ge=12, validation_alias="AUTH_PASSWORD_MIN_LENGTH"
    )
    auth_password_max_length: int = Field(
        default=128, le=1024, validation_alias="AUTH_PASSWORD_MAX_LENGTH"
    )
    auth_attempt_window_minutes: int = Field(
        default=15, ge=1, validation_alias="AUTH_ATTEMPT_WINDOW_MINUTES"
    )
    auth_attempt_limit: int = Field(
        default=5, ge=1, validation_alias="AUTH_ATTEMPT_LIMIT"
    )
    public_origin: str = Field(
        default="http://127.0.0.1:5173", validation_alias="PUBLIC_ORIGIN"
    )

    @model_validator(mode="after")
    def validate_auth_configuration(self) -> Settings:
        origin = urlsplit(self.public_origin)
        local_hosts = {"127.0.0.1", "localhost", "::1"}
        if (
            origin.scheme not in {"http", "https"}
            or not origin.hostname
            or origin.username
            or origin.password
            or origin.path
            or origin.query
            or origin.fragment
        ):
            raise ValueError(
                "PUBLIC_ORIGIN must be an http/https origin without a path"
            )
        if origin.scheme != "https" and origin.hostname not in local_hosts:
            raise ValueError("PUBLIC_ORIGIN requires HTTPS outside localhost")
        if self.auth_password_min_length > self.auth_password_max_length:
            raise ValueError("Invalid password length range")
        return self

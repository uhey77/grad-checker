"""起動時に読み込む環境設定。"""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        frozen=True, case_sensitive=True, populate_by_name=True
    )

    # 起動ディレクトリにかかわらずbackend/dataへ保存する。
    database_url: str = Field(
        default=f"sqlite:///{Path(__file__).resolve().parents[1] / 'data' / 'grad_checker.db'}",
        validation_alias="DATABASE_URL",
    )

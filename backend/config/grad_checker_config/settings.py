"""起動時に読み込む環境設定。"""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_DATABASE_PATH = Path(__file__).resolve().parents[2] / "data" / "grad_checker.db"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        frozen=True, case_sensitive=True, populate_by_name=True
    )

    # 起動ディレクトリにかかわらずbackend/dataへ保存する。
    database_url: str = Field(
        default=f"sqlite:///{DEFAULT_DATABASE_PATH}",
        validation_alias="DATABASE_URL",
    )

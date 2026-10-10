"""起動時に読み込む環境設定。"""

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    database_url: str

    @classmethod
    def from_env(cls) -> Settings:
        # 起動ディレクトリにかかわらずbackend/dataへ保存する。
        database_path = Path(__file__).resolve().parents[1] / "data" / "grad_checker.db"
        return cls(
            database_url=os.environ.get("DATABASE_URL", f"sqlite:///{database_path}")
        )

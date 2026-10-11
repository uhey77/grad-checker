"""SQLiteエンジンと、課程・科目データのスキーマの生成。"""

from pathlib import Path
from sqlite3 import Connection

from sqlalchemy import Engine, event
from sqlalchemy.engine import make_url
from sqlmodel import SQLModel, create_engine

from modules.subjects.grad_checker_subjects.infrastructure.subject_models import (
    SUBJECT_TABLES,
)


def create_database_engine(database_url: str) -> Engine:
    url = make_url(database_url)
    if url.get_backend_name() != "sqlite":
        raise ValueError("現在対応しているデータベースはSQLiteのみです。")

    if url.database and url.database != ":memory:":
        Path(url.database).parent.mkdir(parents=True, exist_ok=True)

    engine = create_engine(url, connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection: Connection, _connection_record: object) -> None:
        # SQLiteの外部キー設定は接続ごとに必要。
        cursor = connection.cursor()
        try:
            cursor.execute("PRAGMA foreign_keys=ON")
        finally:
            cursor.close()

    return engine


def create_database_schema(engine: Engine) -> None:
    SQLModel.metadata.create_all(engine, tables=SUBJECT_TABLES)

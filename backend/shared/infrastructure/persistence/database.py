"""SQLite / PostgreSQL接続の生成。接続文字列はログへ出さない。"""

from pathlib import Path
from sqlite3 import Connection

from sqlalchemy import Engine, event
from sqlalchemy.engine import make_url
from sqlmodel import create_engine


def create_database_engine(database_url: str) -> Engine:
    url = make_url(database_url)
    if url.get_backend_name() == "postgresql":
        # Neonが渡す通常のpostgresql URLも、既存の同期SQLModelで利用する。
        return create_engine(
            url.set(drivername="postgresql+psycopg"),
            pool_pre_ping=True,
            isolation_level="READ COMMITTED",
            connect_args={"connect_timeout": 10, "prepare_threshold": None},
            hide_parameters=True,
        )
    if url.get_backend_name() != "sqlite":
        raise ValueError("対応データベースはSQLiteとPostgreSQLです。")

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

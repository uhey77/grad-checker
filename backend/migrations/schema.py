"""空のPostgreSQLへの初期スキーマ作成。データ移行・Seedは実行しない。"""

import argparse

from sqlalchemy import create_mock_engine, inspect, text
from sqlmodel import SQLModel

from apps.settings import Settings
from migrations.postgres import TABLES
from modules.requirements.infrastructure.persistence.schema import (
    POSTGRES_CHECK_TRIGGER,
    install_check_trigger,
)
from shared.infrastructure.persistence.database import create_database_engine
from shared.infrastructure.persistence.unit_of_work import lock_postgres_writes


def initialize_schema(engine, *, apply=False):
    if engine.dialect.name != "postgresql" or "-pooler" in (engine.url.host or ""):
        raise ValueError("PostgreSQLの直接接続を指定してください。")
    with engine.begin() as connection:
        if apply:
            lock_postgres_writes(connection)
        else:
            connection.execute(text("SET TRANSACTION READ ONLY"))
        inspector = inspect(connection)
        if inspector.get_table_names() or inspector.get_view_names():
            raise RuntimeError("既存のスキーマがあります。自動変更は行いません。")
        if apply:
            SQLModel.metadata.create_all(connection, tables=TABLES)
            install_check_trigger(connection)
    return [table.name for table in TABLES]


def schema_sql() -> str:
    statements = []

    def collect(statement, *_args, **_kwargs):
        statements.append(
            str(
                statement.compile(
                    dialect=engine.dialect, compile_kwargs={"literal_binds": True}
                )
            ).strip()
            + ";"
        )

    engine = create_mock_engine("postgresql+psycopg://", collect)
    SQLModel.metadata.create_all(engine, tables=TABLES, checkfirst=False)
    statements.extend(statement + ";" for statement in POSTGRES_CHECK_TRIGGER)
    return "\n\n".join(statements)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument(
        "--sql", action="store_true", help="接続せずレビュー用DDLを表示"
    )
    args = parser.parse_args()
    if args.sql:
        if args.apply:
            parser.error("--sqlと--applyは同時に指定できません。")
        print(schema_sql())
        return 0
    engine = None
    try:
        url = Settings().direct_database_url
        if not url:
            raise ValueError("Direct接続が必要です。")
        engine = create_database_engine(url)
        tables = initialize_schema(engine, apply=args.apply)
        print(
            f"schema {'applied' if args.apply else 'plan'}: "
            f"{len(tables)} tables; no seed/data import"
        )
        return 0
    except Exception:
        print("Schema initialization failed; 接続・移行先の空状態を確認してください。")
        return 1
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())

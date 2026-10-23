"""設定済みDBへの接続とスキーマを、書込みなしで確認する。"""

import argparse

from sqlalchemy import text

from apps.settings import Settings
from migrations.postgres import validate_database_schema
from shared.infrastructure.persistence.database import create_database_engine


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--connection-only", action="store_true")
    args = parser.parse_args()
    engine = None
    try:
        engine = create_database_engine(Settings().database_url)
        with engine.connect() as connection:
            if engine.dialect.name == "postgresql":
                connection.execute(text("SET TRANSACTION READ ONLY"))
            else:
                connection.exec_driver_sql("PRAGMA query_only=ON")
            assert connection.execute(text("SELECT 1")).scalar_one() == 1
            if not args.connection_only:
                validate_database_schema(connection)
        print(
            "DB connection OK (read only)"
            if args.connection_only
            else "DB connection OK; schema OK (read only)"
        )
        return 0
    except Exception:
        print(
            "DB connection/schema check failed; 接続設定と移行状態を確認してください。"
        )
        return 1
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())

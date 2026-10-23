"""設定済みDBへの接続とスキーマを、書込みなしで確認する。"""

from sqlalchemy import text

from apps.settings import Settings
from migrations.postgres import validate_database_schema
from shared.infrastructure.persistence.database import create_database_engine


def main() -> int:
    engine = None
    try:
        engine = create_database_engine(Settings().database_url)
        with engine.connect() as connection:
            if engine.dialect.name == "postgresql":
                connection.execute(text("SET TRANSACTION READ ONLY"))
            else:
                connection.exec_driver_sql("PRAGMA query_only=ON")
            assert connection.execute(text("SELECT 1")).scalar_one() == 1
            validate_database_schema(connection)
        print("DB connection OK; schema OK (read only)")
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

"""公開前の接続先・TLS・移行済み件数を、接続情報を出力せず読み取り確認する。"""

import argparse
import json
import os
import subprocess

from sqlalchemy import func, inspect, select, text
from sqlalchemy.engine import make_url

from migrations.postgres import TABLES, validate_database_schema
from shared.infrastructure.persistence.database import create_database_engine

DIRECT_HOST = "ep-silent-bird-a1iyza45.ap-southeast-1.aws.neon.tech"
POOLED_HOST = "ep-silent-bird-a1iyza45-pooler.ap-southeast-1.aws.neon.tech"
EXPECTED_ROWS = {
    "academic_programs": 6,
    "curricula": 4,
    "classifications": 68,
    "courses": 131,
    "course_offerings": 161,
    "curriculum_courses": 498,
    "students": 1,
    "student_credentials": 1,
    "auth_sessions": 1,
    "auth_attempts": 4,
    "grade_attempts": 6,
    "graduation_requirements": 80,
    "requirement_scopes": 492,
    "credit_rules": 16,
    "credit_rule_courses": 265,
    "credit_rule_limits": 4,
    "completion_policies": 0,
    "check_results": 0,
}


def validate_target(value: str, *, direct: bool) -> None:
    url = make_url(value)
    if (
        url.get_backend_name() != "postgresql"
        or url.host != (DIRECT_HOST if direct else POOLED_HOST)
        or url.port not in (None, 5432)
        or url.database != "grad-checker"
        or not url.username
        or url.query.get("sslmode") not in ("require", "verify-full")
        or set(url.query) - {"sslmode", "channel_binding", "connect_timeout"}
    ):
        # options/service/search_path等による接続先やスキーマの変更も許可しない。
        raise ValueError("Unexpected production target")


def inspect_target(value: str, *, direct: bool) -> None:
    validate_target(value, direct=direct)
    engine = create_database_engine(value)
    try:
        with engine.connect().execution_options(
            isolation_level="REPEATABLE READ"
        ) as connection:
            connection.execute(text("SET TRANSACTION READ ONLY"))
            driver = connection.connection.driver_connection
            if driver is None or not driver.pgconn.ssl_in_use:
                raise ValueError("TLS required")
            if connection.execute(
                text("SELECT current_database(), current_schema()")
            ).one() != ("grad-checker", "public"):
                raise ValueError("Unexpected database")
            validate_database_schema(connection)
            if set(inspect(connection).get_table_names()) != set(EXPECTED_ROWS):
                raise ValueError("Unexpected tables")
            rows = {
                table.name: connection.execute(
                    select(func.count()).select_from(table)
                ).scalar_one()
                for table in TABLES
            }
            if rows != EXPECTED_ROWS:
                raise ValueError("Unexpected migrated row counts")
    finally:
        engine.dispose()


def secret_manager_value(secret: str) -> str:
    # 認証済みCloud Shell等で実行する。Secret値はメモリ内だけに保持する。
    result = subprocess.run(
        [
            "gcloud",
            "secrets",
            "versions",
            "access",
            "1",
            "--project=grad-checker-512505",
            f"--secret={secret}",
            "--quiet",
        ],
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    return result.stdout.strip()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--secret-manager", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.secret_manager:
            pooled = secret_manager_value("grad-checker-database-url")
            direct = secret_manager_value("grad-checker-direct-database-url")
        else:
            pooled = os.environ["DATABASE_URL"]
            direct = os.environ["DIRECT_DATABASE_URL"]
        # 両方の接続先を先に確認する。どちらもDDL・移行・Seedを呼ばない。
        validate_target(pooled, direct=False)
        validate_target(direct, direct=True)
        inspect_target(pooled, direct=False)
        inspect_target(direct, direct=True)
    except Exception:
        # SQL・入力値・例外メッセージ・gcloudのstdout/stderrは出力しない。
        print("Production DB audit failed; target, TLS, schema or counts differ")
        return 1
    print(
        json.dumps(
            {
                "source": "secret-manager" if args.secret_manager else "github-secrets",
                "production_target_verified": True,
                "tables": len(EXPECTED_ROWS),
                "rows": sum(EXPECTED_ROWS.values()),
                "read_only": True,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

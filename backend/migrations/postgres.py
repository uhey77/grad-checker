"""SQLiteを読み取り専用で開き、空のPostgreSQLへ全件を原子的にコピーする。"""

import argparse
import json
import sqlite3
from datetime import datetime
from pathlib import Path

from sqlalchemy import Connection, Engine, create_engine, inspect, select, text
from sqlmodel import SQLModel

from apps.settings import Settings

# 全テーブルをメタデータへ登録する。通常の起動時のデータ改訂は呼び出さない。
from modules.accounts.infrastructure.persistence.models.models import ACCOUNT_TABLES
from modules.grades.infrastructure.persistence.models.models import GRADE_TABLES
from modules.requirements.infrastructure.persistence.models.check_models import (
    CHECK_TABLES,
)
from modules.requirements.infrastructure.persistence.models.models import (
    REQUIREMENT_TABLES,
)
from modules.subjects.infrastructure.persistence.models.subject_models import (
    SUBJECT_TABLES,
)
from shared.infrastructure.persistence.database import create_database_engine
from shared.infrastructure.persistence.unit_of_work import lock_postgres_writes

TABLES = (
    SUBJECT_TABLES + ACCOUNT_TABLES + GRADE_TABLES + REQUIREMENT_TABLES + CHECK_TABLES
)


def validate_database_schema(connection: Connection) -> None:
    inspector = inspect(connection)
    if not {table.name for table in TABLES}.issubset(inspector.get_table_names()):
        raise RuntimeError("DBのスキーマが未作成です。移行手順を確認してください。")
    for table in TABLES:
        if {c.name for c in table.columns} != {
            c["name"] for c in inspector.get_columns(table.name)
        }:
            raise RuntimeError("DBのカラムが現行スキーマと一致しません。")
    if connection.dialect.name == "postgresql":
        if not connection.execute(
            text(
                "SELECT EXISTS (SELECT 1 FROM pg_trigger "
                "WHERE tgrelid = 'check_results'::regclass "
                "AND tgname = 'check_results_immutable' AND tgenabled = 'O')"
            )
        ).scalar_one():
            raise RuntimeError("判定履歴の更新禁止トリガーが未設定です。")


def read_rows(connection: Connection, table) -> list[dict]:
    return [dict(row) for row in connection.execute(select(table)).mappings()]


def comparable(rows: list[dict]) -> list[str]:
    # 日時・Boolean・JSONはSQLAlchemyで型を復元して比較する。
    def encode(value):
        if isinstance(value, datetime):
            return value.isoformat()
        raise TypeError("比較できないDB値です。")

    return sorted(
        json.dumps(row, sort_keys=True, ensure_ascii=False, default=encode)
        for row in rows
    )


def parent_first(rows: list[dict]) -> list[dict]:
    if not rows or "parent_id" not in rows[0]:
        return rows
    result = []
    remaining = list(rows)
    inserted = set()
    while remaining:
        ready = [
            r for r in remaining if r["parent_id"] is None or r["parent_id"] in inserted
        ]
        if not ready:
            raise RuntimeError("親子参照が循環しているか、親が存在しません。")
        for row in ready:
            result.append(row)
            inserted.add(row["id"])
            remaining.remove(row)
    return result


def migrate(source: Path, target: Engine, *, apply: bool = False) -> dict[str, int]:
    if target.dialect.name != "postgresql":
        raise ValueError("移行先にはPostgreSQLが必要です。")
    if "-pooler" in (target.url.host or ""):
        raise ValueError("移行にはDIRECT_DATABASE_URLの直接接続を使用してください。")
    if not source.is_file():
        raise ValueError("移行元のSQLiteファイルが存在しません。")
    source_engine = create_engine(
        "sqlite://",
        creator=lambda: sqlite3.connect(
            source.resolve().as_uri() + "?mode=ro", uri=True
        ),
    )
    try:
        with source_engine.connect() as origin, target.begin() as destination:
            origin.exec_driver_sql("BEGIN")
            if apply:
                lock_postgres_writes(destination)
            else:
                destination.execute(text("SET TRANSACTION READ ONLY"))
            validate_database_schema(destination)
            # スキーマ作成は別コマンド。既存行への上書き・追記はしない。
            for table in TABLES:
                if destination.execute(select(table).limit(1)).first() is not None:
                    raise RuntimeError(
                        "移行先に既存データがあります。空のDBを指定してください。"
                    )
            if set(inspect(origin).get_table_names()) != {t.name for t in TABLES}:
                raise RuntimeError("移行元のテーブルが現行スキーマと一致しません。")
            validate_database_schema(origin)
            if origin.exec_driver_sql("PRAGMA foreign_key_check").first() is not None:
                raise RuntimeError("移行元の外部キー整合性を確認してください。")
            rows = {t.name: parent_first(read_rows(origin, t)) for t in TABLES}
            if apply:
                for table in SQLModel.metadata.sorted_tables:
                    if table not in TABLES:
                        continue
                    # 自己参照を含め、親のINSERT後に子を保存する。
                    for row in rows[table.name]:
                        destination.execute(table.insert().values(**row))
                for table in TABLES:
                    if comparable(rows[table.name]) != comparable(
                        read_rows(destination, table)
                    ):
                        raise RuntimeError(
                            "移行後のデータ照合に失敗しました。全体を取り消します。"
                        )
            return {name: len(records) for name, records in rows.items()}
    finally:
        source_engine.dispose()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--apply", action="store_true", help="省略時は読み取り確認のみ")
    args = parser.parse_args()
    url = Settings().direct_database_url
    if not url:
        print("DIRECT_DATABASE_URLを設定してください。")
        return 1
    engine = None
    try:
        engine = create_database_engine(url)
        counts = migrate(args.source, engine, apply=args.apply)
        print(json.dumps({"applied": args.apply, "rows": counts}, ensure_ascii=False))
        return 0
    except Exception:
        # DB例外にはSQLパラメーターや接続情報が含まれ得るため、そのまま出さない。
        print(
            "移行できませんでした。接続・空の移行先・移行元の形式を確認してください。"
        )
        return 1
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())

"""SQLite backup APIでWALを含む整合した読取り専用スナップショットを保存する。"""

import argparse
import os
import sqlite3
from contextlib import closing
from pathlib import Path


def verify_integrity(connection: sqlite3.Connection) -> None:
    if connection.execute("PRAGMA quick_check").fetchall() != [("ok",)]:
        raise RuntimeError("SQLite integrity check failed")
    if connection.execute("PRAGMA foreign_key_check").fetchone() is not None:
        raise RuntimeError("SQLite foreign key check failed")


def backup_sqlite(source: Path, destination: Path) -> None:
    # mode=roは存在しない移行元の自動作成と、元DBへの書込みを防ぐ。
    with closing(
        sqlite3.connect(source.resolve().as_uri() + "?mode=ro", uri=True)
    ) as origin:
        try:
            origin.execute("BEGIN")
            verify_integrity(origin)
            # O_EXCLにより既存バックアップを上書きしない。個人情報を含み得る。
            descriptor = os.open(
                destination, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600
            )
            os.close(descriptor)
            try:
                with closing(sqlite3.connect(destination)) as copied:
                    origin.backup(copied)
                    verify_integrity(copied)
            except Exception:
                destination.unlink(missing_ok=True)
                raise
        finally:
            origin.rollback()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    try:
        backup_sqlite(args.source, args.destination)
        print("SQLite backup OK; integrity and foreign keys OK")
        return 0
    except Exception:
        print("SQLite backup failed; check source integrity and unused destination")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

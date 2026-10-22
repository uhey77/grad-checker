from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from shared.infrastructure.persistence.database import create_database_engine


def test_foreign_keys_are_enforced_on_each_connection(tmp_path: Path) -> None:
    engine = create_database_engine(f"sqlite:///{tmp_path / 'test.db'}")
    try:
        with engine.begin() as connection:
            connection.execute(text("CREATE TABLE parents (id INTEGER PRIMARY KEY)"))
            connection.execute(
                text("CREATE TABLE children (parent_id INTEGER REFERENCES parents(id))")
            )
            connection.execute(text("INSERT INTO parents (id) VALUES (1)"))
            connection.execute(text("INSERT INTO children (parent_id) VALUES (1)"))

        # 同時に2接続を確保して、新規接続でも設定されることを確認する。
        with engine.connect() as first, engine.connect() as second:
            for connection in (first, second):
                assert connection.execute(text("PRAGMA foreign_keys")).scalar_one() == 1
                with pytest.raises(IntegrityError):
                    connection.execute(
                        text("INSERT INTO children (parent_id) VALUES (99)")
                    )
                connection.rollback()

        with engine.begin() as connection:
            with pytest.raises(IntegrityError):
                connection.execute(text("DELETE FROM parents WHERE id = 1"))
    finally:
        engine.dispose()


def test_independent_engines_do_not_share_database(tmp_path: Path) -> None:
    first = create_database_engine(f"sqlite:///{tmp_path / 'first.db'}")
    second = create_database_engine(f"sqlite:///{tmp_path / 'second.db'}")
    try:
        with first.begin() as connection:
            connection.execute(text("CREATE TABLE records (id INTEGER PRIMARY KEY)"))
        with second.connect() as connection:
            assert (
                connection.execute(
                    text("SELECT count(*) FROM sqlite_master WHERE name = 'records'")
                ).scalar_one()
                == 0
            )
    finally:
        first.dispose()
        second.dispose()


def test_unsupported_database_is_rejected() -> None:
    with pytest.raises(ValueError, match="SQLite"):
        create_database_engine("postgresql://localhost/grad_checker")

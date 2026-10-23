import sqlite3
from pathlib import Path

import pytest

from scripts.backup_sqlite import backup_sqlite


def test_backup_includes_committed_wal_without_changing_source(tmp_path):
    source, destination = tmp_path / "source.db", tmp_path / "backup.db"
    with sqlite3.connect(source) as writer:
        writer.execute("PRAGMA journal_mode=WAL")
        writer.execute("CREATE TABLE sample (id INTEGER PRIMARY KEY, value TEXT)")
        writer.execute("INSERT INTO sample VALUES (1, 'committed-in-wal')")
        writer.commit()
        before = source.read_bytes(), Path(str(source) + "-wal").read_bytes()
        backup_sqlite(source, destination)
        assert before == (source.read_bytes(), Path(str(source) + "-wal").read_bytes())
        with sqlite3.connect(destination) as copied:
            assert copied.execute("SELECT value FROM sample").fetchone() == (
                "committed-in-wal",
            )
    assert destination.stat().st_mode & 0o777 == 0o600


def test_backup_refuses_to_overwrite_existing_destination(tmp_path):
    source, destination = tmp_path / "source.db", tmp_path / "backup.db"
    with sqlite3.connect(source) as connection:
        connection.execute("CREATE TABLE sample (id INTEGER)")
    destination.write_bytes(b"preserve-existing-backup")
    with pytest.raises(FileExistsError):
        backup_sqlite(source, destination)
    assert destination.read_bytes() == b"preserve-existing-backup"


def test_backup_missing_source_does_not_create_database_files(tmp_path):
    source, destination = tmp_path / "missing.db", tmp_path / "backup.db"
    with pytest.raises(sqlite3.OperationalError):
        backup_sqlite(source, destination)
    assert not source.exists()
    assert not destination.exists()


def test_backup_rejects_foreign_key_violation(tmp_path):
    source, destination = tmp_path / "broken.db", tmp_path / "backup.db"
    with sqlite3.connect(source) as connection:
        connection.execute("CREATE TABLE parent (id INTEGER PRIMARY KEY)")
        connection.execute(
            "CREATE TABLE child (parent_id INTEGER REFERENCES parent(id))"
        )
        connection.execute("INSERT INTO child VALUES (42)")
    with pytest.raises(RuntimeError, match="foreign key"):
        backup_sqlite(source, destination)
    assert not destination.exists()

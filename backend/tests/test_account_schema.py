"""旧DBを破壊せずに新しい認証方式へ移行する境界。"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect, text

from api.api_service.main import create_app
from config.settings import Settings


def test_empty_legacy_schema_migrates_idempotently(tmp_path: Path):
    settings = Settings(database_url=f"sqlite:///{tmp_path / 'legacy.db'}")
    app = create_app(settings)
    with TestClient(app):
        with app.state.database_engine.begin() as db:
            db.execute(
                text(
                    "ALTER TABLE students RENAME COLUMN created_at TO email_verified_at"
                )
            )
            db.execute(
                text("ALTER TABLE student_credentials DROP COLUMN recovery_code_hash")
            )
            db.execute(
                text(
                    "CREATE TABLE email_verifications "
                    "(token_hash TEXT PRIMARY KEY, email TEXT)"
                )
            )
    for _ in range(2):
        migrated = create_app(settings)
        with TestClient(migrated):
            inspector = inspect(migrated.state.database_engine)
            assert "created_at" in {
                c["name"] for c in inspector.get_columns("students")
            }
            assert "recovery_code_hash" in {
                c["name"] for c in inspector.get_columns("student_credentials")
            }
            assert inspector.has_table("email_verifications")
    with TestClient(create_app(settings)) as client:
        response = client.post(
            "/internal/auth",
            json={
                "operation": "register",
                "login_name": "student_01",
                "password": "application-password",
                "client_key": "127.0.0.1",
            },
        ).json()
        assert response["data"]["registered"]


def test_nonempty_legacy_schema_stops_without_modification(tmp_path: Path):
    settings = Settings(database_url=f"sqlite:///{tmp_path / 'legacy.db'}")
    app = create_app(settings)
    with TestClient(app) as client:
        assert client.post(
            "/internal/auth",
            json={
                "operation": "register",
                "login_name": "student_01",
                "password": "application-password",
                "client_key": "127.0.0.1",
            },
        ).json()["data"]["registered"]
        with app.state.database_engine.begin() as db:
            db.execute(
                text(
                    "ALTER TABLE students RENAME COLUMN created_at TO email_verified_at"
                )
            )
            db.execute(
                text("ALTER TABLE student_credentials DROP COLUMN recovery_code_hash")
            )
    with pytest.raises(RuntimeError, match="旧メール認証のアカウントが存在"):
        with TestClient(create_app(settings)):
            pass
    # 起動を拒否したDBの行・列が維持される。
    with app.state.database_engine.connect() as db:
        assert db.execute(text("SELECT COUNT(*) FROM students")).scalar_one() == 1
        assert "email_verified_at" in {
            c["name"] for c in inspect(db).get_columns("students")
        }
        assert "recovery_code_hash" not in {
            c["name"] for c in inspect(db).get_columns("student_credentials")
        }

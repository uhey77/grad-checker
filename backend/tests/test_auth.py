"""ユーザー名登録・復旧・失効・原子的保存を一時SQLiteで検証する。"""

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from api.api_service.main import create_app
from config.settings import Settings
from modules.accounts.grad_checker_accounts.application.auth import digest
from modules.accounts.grad_checker_accounts.application.errors.auth import AuthError
from modules.accounts.grad_checker_accounts.infrastructure.models import (
    AuthSession,
    Credential,
    Student,
)
from modules.accounts.grad_checker_accounts.infrastructure.repository import (
    SqliteAccountUnitOfWork,
)

USERNAME = "student_01"
PASSWORD = "app-only-password-123"
NEW_PASSWORD = "new-application-password"


@pytest.fixture
def auth(tmp_path: Path):
    app = create_app(Settings(database_url=f"sqlite:///{tmp_path / 'auth.db'}"))
    with TestClient(app) as client:
        yield app, client


def call(client, operation, **fields):
    if operation in {"register", "recover", "login"}:
        fields.setdefault("client_key", "127.0.0.1")
    return client.post("/bridge/auth", json={"operation": operation, **fields}).json()


def register(client, username=USERNAME):
    result = call(client, "register", login_name=username, password=PASSWORD)["data"]
    assert result["registered"] is True
    assert len(result["recovery_code"]) == 43
    return result["recovery_code"]


def login(client, username=USERNAME, password=PASSWORD):
    return call(client, "login", login_name=username, password=password)["data"]


def test_registration_login_session_logout(auth):
    app, client = auth
    recovery = register(client, "Student_01")
    result = login(client)
    assert result["student"]["login_name"] == USERNAME
    raw = result.pop("session_token")
    assert call(client, "session", token=raw)["data"] == result
    with Session(app.state.database_engine) as db:
        credential = db.exec(select(Credential)).one()
        assert credential.password_hash.startswith("$argon2id$")
        assert credential.recovery_code_hash == digest(recovery)
        session = db.exec(select(AuthSession)).one()
        assert session.token_hash == digest(raw)
        assert session.csrf_token_hash == digest(result["csrf_token"])
        assert recovery not in str(credential)
    assert (
        call(client, "logout", token=raw, csrf="wrong")["error"]["code"]
        == "invalid_csrf"
    )
    assert (
        call(client, "logout", token=raw, csrf=result["csrf_token"])["data"][
            "authenticated"
        ]
        is False
    )
    assert call(client, "session", token=raw)["error"]["code"] == "invalid_credentials"


def test_duplicate_registration_does_not_overwrite_credentials(auth):
    app, client = auth
    recovery = register(client)
    assert (
        call(client, "register", login_name="STUDENT_01", password=NEW_PASSWORD)[
            "error"
        ]["code"]
        == "registration_conflict"
    )
    assert login(client)["authenticated"]
    with Session(app.state.database_engine) as db:
        assert len(db.exec(select(Student)).all()) == 1
        assert db.exec(select(Credential)).one().recovery_code_hash == digest(recovery)


def test_invalid_username_password_and_legacy_requests(auth):
    app, client = auth
    assert (
        call(client, "register", login_name="x@y.jp", password=PASSWORD)["error"][
            "code"
        ]
        == "invalid_username"
    )
    assert (
        call(client, "register", login_name=USERNAME, password="short")["error"]["code"]
        == "invalid_password"
    )
    assert (
        call(client, "register", email="x@edu.teu.ac.jp")["error"]["code"]
        == "invalid_request"
    )
    assert (
        call(client, "verify", token="old-token", password=PASSWORD)["error"]["code"]
        == "invalid_request"
    )
    with Session(app.state.database_engine) as db:
        assert not db.exec(select(Student)).all()


def test_recovery_rotates_code_revokes_all_sessions_and_preserves_account(auth):
    app, client = auth
    recovery = register(client)
    sessions = [login(client) for _ in range(2)]
    student_id = sessions[0]["student"]["id"]
    for name, code in ((USERNAME, "x" * 43), ("missing", recovery)):
        assert (
            call(
                client,
                "recover",
                login_name=name,
                recovery_code=code,
                password=NEW_PASSWORD,
            )["error"]["code"]
            == "invalid_recovery"
        )
    assert (
        call(
            client,
            "recover",
            login_name=USERNAME,
            recovery_code=recovery,
            password="short",
        )["error"]["code"]
        == "invalid_password"
    )
    result = call(
        client,
        "recover",
        login_name="STUDENT_01",
        recovery_code=recovery,
        password=NEW_PASSWORD,
    )["data"]
    assert result["recovered"]
    replacement = result["recovery_code"]
    assert replacement != recovery
    for session in sessions:
        assert (
            call(client, "session", token=session["session_token"])["error"]["code"]
            == "invalid_credentials"
        )
    assert (
        call(client, "login", login_name=USERNAME, password=PASSWORD)["error"]["code"]
        == "invalid_credentials"
    )
    assert login(client, password=NEW_PASSWORD)["student"]["id"] == student_id
    assert (
        call(
            client,
            "recover",
            login_name=USERNAME,
            recovery_code=recovery,
            password=PASSWORD,
        )["error"]["code"]
        == "invalid_recovery"
    )
    # 回数制限は別のテストで検証。新コードでの再復旧をここで確認する。
    uow = SqliteAccountUnitOfWork(app.state.database_engine)
    with uow.write():
        assert uow.accounts.reset_credentials(
            USERNAME,
            digest(replacement),
            app.state.passwords.hash(PASSWORD),
            digest("next-code"),
            datetime.now(UTC),
        )
    with Session(app.state.database_engine) as db:
        assert db.exec(select(Credential)).one().recovery_code_hash == digest(
            "next-code"
        )


@pytest.mark.parametrize("operation", ["login", "recover", "register"])
def test_rate_limits_persist_and_are_shared_by_username(auth, operation):
    app, client = auth
    for number in range(5):
        fields = dict(
            login_name="STUDENT_01" if number % 2 else USERNAME,
            password=PASSWORD,
            client_key=f"192.0.2.{number}",
        )
        if operation == "recover":
            fields["recovery_code"] = "x" * 43
        assert (
            call(client, operation, **fields).get("error", {}).get("code")
            != "rate_limited"
        )
    fields["client_key"] = "192.0.2.99"
    assert call(client, operation, **fields)["error"]["code"] == "rate_limited"
    # 同じDBを開き直しても制限を維持する。
    with TestClient(create_app(app.state.settings)) as restarted:
        assert call(restarted, operation, **fields)["error"]["code"] == "rate_limited"


def test_expired_and_disabled_sessions(auth):
    app, client = auth
    register(client)
    raw = login(client)["session_token"]
    with Session(app.state.database_engine) as db:
        record = db.exec(select(AuthSession)).one()
        record.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        db.add(record)
        db.commit()
    assert call(client, "session", token=raw)["error"]["code"] == "invalid_credentials"
    raw = login(client)["session_token"]
    with Session(app.state.database_engine) as db:
        credential = db.exec(select(Credential)).one()
        credential.is_active = False
        db.add(credential)
        db.commit()
    assert call(client, "session", token=raw)["error"]["code"] == "invalid_credentials"


def test_concurrent_registration_creates_one_account(auth):
    app, _ = auth
    hashed = app.state.passwords.hash(PASSWORD)

    def attempt(_):
        uow = SqliteAccountUnitOfWork(app.state.database_engine)
        try:
            with uow.write():
                uow.accounts.register(
                    USERNAME, hashed, digest("code"), datetime.now(UTC)
                )
            return "ok"
        except AuthError as error:
            return error.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(attempt, range(2))) == ["ok", "registration_conflict"]
    with Session(app.state.database_engine) as db:
        assert len(db.exec(select(Student)).all()) == 1
        assert len(db.exec(select(Credential)).all()) == 1


def test_recovery_is_single_use_and_stale_password_cannot_create_session(auth):
    app, client = auth
    recovery = register(client)
    uow = SqliteAccountUnitOfWork(app.state.database_engine)
    with uow.read():
        credentials = uow.accounts.credentials(USERNAME)
    assert credentials is not None
    account, old_hash = credentials
    hashed = app.state.passwords.hash(NEW_PASSWORD)

    def attempt(_):
        # 照合とセッション失効は同じ書込みで行い、同じコードは一度だけ成功する。
        uow = SqliteAccountUnitOfWork(app.state.database_engine)
        with uow.write():
            student_id = uow.accounts.reset_credentials(
                USERNAME,
                digest(recovery),
                hashed,
                digest("replacement"),
                datetime.now(UTC),
            )
            if student_id is None:
                return "invalid_recovery"
            uow.accounts.revoke_sessions(student_id, datetime.now(UTC))
            return "ok"

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(attempt, range(2))) == ["invalid_recovery", "ok"]
    with uow.write():
        assert not uow.accounts.save_session(
            account,
            digest("token"),
            "csrf",
            datetime.now(UTC) + timedelta(hours=1),
            old_hash,
        )

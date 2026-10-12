"""確認リンク・認証・失効・原子的登録を一時SQLiteで検証する。"""

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from api.api_service.main import create_app
from config.settings import Settings
from modules.accounts.grad_checker_accounts.application.auth import AuthError, digest
from modules.accounts.grad_checker_accounts.infrastructure.models import (
    AuthSession,
    Credential,
    Student,
    Verification,
)
from modules.accounts.grad_checker_accounts.infrastructure.repository import (
    SqliteAccountRepository,
)

EMAIL = "student@edu.teu.ac.jp"
PASSWORD = "app-only-password-123"


class Mailbox:
    def __init__(self):
        self.messages: list[tuple[str, str]] = []
        self.fail = False

    def send(self, email: str, token: str) -> None:
        if self.fail:
            raise AuthError("mail_unavailable")
        self.messages.append((email, token))


@pytest.fixture
def auth(tmp_path: Path):
    app = create_app(Settings(database_url=f"sqlite:///{tmp_path / 'auth.db'}"))
    with TestClient(app) as client:
        box = Mailbox()
        app.state.verification_mailer = box
        yield app, client, box


def call(client, operation, **fields):
    if operation in {"register", "verify", "login"}:
        fields.setdefault("client_key", "127.0.0.1")
    return client.post("/internal/auth", json={"operation": operation, **fields}).json()


def register(client, box, email=EMAIL):
    assert call(client, "register", email=email) == {"data": {"accepted": True}}
    return box.messages[-1][1]


def complete(client, box, email=EMAIL):
    token = register(client, box, email)
    assert call(client, "verify", token=token, password=PASSWORD) == {
        "data": {"verified": True}
    }
    return token


def test_registration_verification_login_session_logout(auth):
    app, client, box = auth
    token = register(client, box)
    assert box.messages[-1][0] == EMAIL
    assert (
        call(client, "login", email=EMAIL, password=PASSWORD)["error"]["code"]
        == "invalid_credentials"
    )
    with Session(app.state.database_engine) as db:
        assert db.exec(select(Student)).all() == []
        assert token not in str(db.exec(select(Verification)).all())
    assert call(client, "verify", token=token, password=PASSWORD)["data"]["verified"]
    assert (
        call(client, "verify", token=token, password=PASSWORD)["error"]["code"]
        == "invalid_verification"
    )
    result = call(client, "login", email=EMAIL, password=PASSWORD)["data"]
    raw = result.pop("session_token")
    assert call(client, "session", token=raw)["data"] == result
    with Session(app.state.database_engine) as db:
        credential = db.exec(select(Credential)).one()
        assert credential.password_hash.startswith("$argon2id$")
        session = db.exec(select(AuthSession)).one()
        assert session.token_hash == digest(raw)
        assert session.csrf_token_hash == digest(result["csrf_token"])
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


def test_expired_links_do_not_create_account(auth):
    app, client, box = auth
    token = register(client, box)
    with Session(app.state.database_engine) as db:
        record = db.get(Verification, digest(token))
        assert record
        record.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        db.add(record)
        db.commit()
    assert (
        call(client, "verify", token=token, password=PASSWORD)["error"]["code"]
        == "invalid_verification"
    )
    with Session(app.state.database_engine) as db:
        assert not db.exec(select(Student)).all()


def test_resend_and_preset_password_cannot_hijack_account(auth):
    app, client, box = auth
    first = register(client, box)
    second = register(client, box)
    assert call(client, "verify", token=second, password=PASSWORD)["data"]["verified"]
    assert (
        call(client, "verify", token=first, password="attacker-password")["error"][
            "code"
        ]
        == "invalid_verification"
    )
    assert call(client, "register", email=EMAIL)["data"]["accepted"]
    assert len(box.messages) == 2
    assert call(client, "login", email=EMAIL, password=PASSWORD)["data"][
        "authenticated"
    ]
    # 登録開始でパスワードを受け付けない。
    assert (
        call(client, "register", email=EMAIL, password=PASSWORD)["error"]["code"]
        == "invalid_request"
    )


def test_domain_and_password_validation_and_mail_failure(auth):
    app, client, box = auth
    assert (
        call(client, "register", email="x@edu.teu.ac.jp.evil.com")["error"]["code"]
        == "invalid_email"
    )
    box.fail = True
    assert call(client, "register", email=EMAIL)["error"]["code"] == "mail_unavailable"
    with Session(app.state.database_engine) as db:
        assert not db.exec(select(Student)).all()
    box.fail = False
    token = register(client, box)
    assert (
        call(client, "verify", token=token, password="short")["error"]["code"]
        == "invalid_password"
    )
    assert call(client, "verify", token=token, password=PASSWORD)["data"]["verified"]


def test_rate_limits_persist_and_are_shared_by_email(auth):
    app, client, box = auth
    for number in range(5):
        response = call(
            client,
            "login",
            email=EMAIL,
            password=PASSWORD,
            client_key=f"192.0.2.{number}",
        )
        assert response["error"]["code"] == "invalid_credentials"
    assert (
        call(client, "login", email=EMAIL, password=PASSWORD, client_key="192.0.2.99")[
            "error"
        ]["code"]
        == "rate_limited"
    )


def test_expired_and_disabled_sessions(auth):
    app, client, box = auth
    complete(client, box)
    result = call(client, "login", email=EMAIL, password=PASSWORD)["data"]
    with Session(app.state.database_engine) as db:
        record = db.exec(select(AuthSession)).one()
        record.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        db.add(record)
        db.commit()
    assert (
        call(client, "session", token=result["session_token"])["error"]["code"]
        == "invalid_credentials"
    )
    result = call(client, "login", email=EMAIL, password=PASSWORD)["data"]
    with Session(app.state.database_engine) as db:
        credential = db.exec(select(Credential)).one()
        credential.is_active = False
        db.add(credential)
        db.commit()
    assert (
        call(client, "session", token=result["session_token"])["error"]["code"]
        == "invalid_credentials"
    )


def test_concurrent_link_consumption_only_creates_one_account(auth):
    app, client, box = auth
    token = register(client, box)
    hashed = app.state.passwords.hash(PASSWORD)

    def consume():
        with Session(app.state.database_engine) as db:
            try:
                SqliteAccountRepository(db).complete_registration(
                    digest(token), hashed, datetime.now(UTC)
                )
                return "ok"
            except AuthError as error:
                return error.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: consume(), range(2)))
    assert sorted(results) == ["invalid_verification", "ok"]
    with Session(app.state.database_engine) as db:
        assert len(db.exec(select(Student)).all()) == 1
        assert len(db.exec(select(Credential)).all()) == 1

"""認証ユースケースのトランザクション範囲をFakeのUnit of Workで検証する。"""

from datetime import datetime

import pytest

from modules.accounts.grad_checker_accounts.application.auth import (
    Account,
    AuthPolicy,
    AuthService,
    StoredSession,
    digest,
)
from modules.accounts.grad_checker_accounts.application.errors.auth import AuthError
from tests.fakes import FakeUnitOfWork

USERNAME = "student_01"
PASSWORD = "app-only-password-123"
RECOVERY = "r" * 43
POLICY = AuthPolicy(
    session_hours=1,
    password_min_length=12,
    password_max_length=128,
    attempt_window_minutes=10,
    attempt_limit=5,
)


class FakeAccountRepository:
    def __init__(self, uow: FakeUnitOfWork) -> None:
        self.uow = uow
        self.attempts: list[str] = []
        self.account = Account(id="student-1", login_name=USERNAME)
        self.password_hash = f"hash:{PASSWORD}"
        self.recovery_hash = digest(RECOVERY)
        self.sessions: dict[str, datetime | None] = {"existing": None}
        self.saved_sessions: list[str] = []

    def take_attempt(self, key: str, now: datetime, window: int, limit: int) -> None:
        self.uow.require_block()
        self.attempts.append(key)

    def register(
        self, username: str, password_hash: str, recovery_hash: str, now: datetime
    ) -> Account:
        self.uow.require_block()
        return Account(id="student-2", login_name=username)

    def reset_credentials(
        self,
        username: str,
        recovery_hash: str,
        password_hash: str,
        new_recovery_hash: str,
        now: datetime,
    ) -> str | None:
        self.uow.require_block()
        if username != USERNAME or recovery_hash != self.recovery_hash:
            return None
        self.password_hash = password_hash
        self.recovery_hash = new_recovery_hash
        return self.account.id

    def revoke_sessions(self, student_id: str, now: datetime) -> None:
        self.uow.require_block()
        self.sessions = dict.fromkeys(self.sessions, now)

    def credentials(self, username: str) -> tuple[Account, str] | None:
        self.uow.require_block()
        if username != USERNAME:
            return None
        return self.account, self.password_hash

    def save_session(
        self,
        account: Account,
        token_hash: str,
        csrf: str,
        expires: datetime,
        password_hash: str,
    ) -> bool:
        self.uow.require_block()
        if password_hash != self.password_hash:
            return False
        self.saved_sessions.append(token_hash)
        return True

    def session(self, token_hash: str, now: datetime) -> StoredSession | None:
        self.uow.require_block()
        return None

    def revoke_session(self, token_hash: str, now: datetime) -> None:
        self.uow.require_block()


class FakeAccountUnitOfWork(FakeUnitOfWork):
    def __init__(self) -> None:
        super().__init__()
        self.repository = FakeAccountRepository(self)

    @property
    def accounts(self) -> FakeAccountRepository:
        return self.repository


class FakePasswords:
    """ハッシュ計算と照合がトランザクション外で行われることを確認する。"""

    def __init__(self, uow: FakeUnitOfWork) -> None:
        self.uow = uow

    def hash(self, password: str) -> str:
        assert not self.uow.active
        return f"hash:{password}"

    def verify(self, password_hash: str | None, password: str) -> bool:
        assert not self.uow.active
        return password_hash == f"hash:{password}"


@pytest.fixture
def uow() -> FakeAccountUnitOfWork:
    return FakeAccountUnitOfWork()


@pytest.fixture
def service(uow: FakeAccountUnitOfWork) -> AuthService:
    return AuthService(uow, FakePasswords(uow), POLICY)


ATTEMPTS = ["write", "commit", "write", "commit"]


def test_attempts_are_kept_even_when_registration_input_is_invalid(uow, service):
    with pytest.raises(AuthError, match="invalid_password"):
        service.register(USERNAME, "short", "192.0.2.1")
    # 試行回数は登録本体と別にcommitし、登録のトランザクションは開始しない。
    assert uow.events == ATTEMPTS
    assert len(uow.repository.attempts) == 2


def test_registration_writes_once_after_attempts(uow, service):
    assert len(service.register(USERNAME, PASSWORD, "192.0.2.1")) == 43
    assert uow.events == [*ATTEMPTS, "write", "commit"]


def test_recovery_updates_credentials_and_revokes_sessions_in_one_write(uow, service):
    replacement = service.recover(USERNAME, RECOVERY, "new-password-1234", "ip")
    assert uow.events == [*ATTEMPTS, "write", "commit"]
    assert uow.repository.password_hash == "hash:new-password-1234"
    assert uow.repository.recovery_hash == digest(replacement)
    assert all(revoked is not None for revoked in uow.repository.sessions.values())


def test_wrong_recovery_code_rolls_back_without_revoking_sessions(uow, service):
    with pytest.raises(AuthError, match="invalid_recovery"):
        service.recover(USERNAME, "x" * 43, "new-password-1234", "ip")
    assert uow.events == [*ATTEMPTS, "write", "rollback"]
    assert uow.repository.sessions == {"existing": None}


def test_wrong_password_reads_credentials_without_writing_a_session(uow, service):
    with pytest.raises(AuthError, match="invalid_credentials"):
        service.login(USERNAME, "wrong-password-1234", "ip")
    assert uow.events == [*ATTEMPTS, "read"]
    assert uow.repository.saved_sessions == []


def test_login_saves_a_session_after_verifying_outside_transactions(uow, service):
    identity, token = service.login(USERNAME, PASSWORD, "ip")
    assert identity.account.login_name == USERNAME
    assert uow.events == [*ATTEMPTS, "read", "write", "commit"]
    assert uow.repository.saved_sessions == [digest(token)]


def test_password_changed_after_verification_does_not_create_a_session(uow, service):
    repository = uow.repository
    original = repository.credentials

    def stale_credentials(username: str) -> tuple[Account, str] | None:
        result = original(username)
        # 照合後、セッション保存までの間に復旧でパスワードが変わった場合。
        repository.password_hash = "hash:changed"
        return result

    repository.credentials = stale_credentials
    with pytest.raises(AuthError, match="invalid_credentials"):
        service.login(USERNAME, PASSWORD, "ip")
    assert uow.events == [*ATTEMPTS, "read", "write", "rollback"]
    assert repository.saved_sessions == []

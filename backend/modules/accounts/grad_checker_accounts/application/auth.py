"""メールの所有確認後にアカウントを作成し、本人セッションを管理する。"""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Protocol

from pydantic import BaseModel, ConfigDict

from modules.accounts.grad_checker_accounts.domain.email_address import (
    validate_registration_email,
)


class AuthError(Exception):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class Account(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    login_name: str


class SessionIdentity(BaseModel):
    model_config = ConfigDict(frozen=True)

    account: Account
    csrf_token: str
    expires_at: datetime


class StoredSession(BaseModel):
    model_config = ConfigDict(frozen=True)
    account: Account
    csrf_token_hash: str
    expires_at: datetime


class AuthPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    verification_minutes: int
    session_hours: int
    password_min_length: int
    password_max_length: int
    attempt_window_minutes: int
    attempt_limit: int


class AccountRepository(Protocol):
    def take_attempt(
        self, key: str, now: datetime, window: int, limit: int
    ) -> None: ...
    def account_exists(self, email: str) -> bool: ...
    def save_verification(
        self, email: str, token_hash: str, expires: datetime
    ) -> None: ...
    def complete_registration(
        self, token_hash: str, password_hash: str, now: datetime
    ) -> Account: ...
    def credentials(self, email: str) -> tuple[Account, str] | None: ...
    def save_session(
        self, account: Account, token_hash: str, csrf: str, expires: datetime
    ) -> None: ...
    def session(self, token_hash: str, now: datetime) -> StoredSession | None: ...
    def revoke_session(self, token_hash: str, now: datetime) -> None: ...


class Passwords(Protocol):
    def hash(self, password: str) -> str: ...
    def verify(self, password_hash: str | None, password: str) -> bool: ...


class VerificationMailer(Protocol):
    def send(self, email: str, token: str) -> None: ...


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


class AuthService:
    def __init__(
        self,
        repository: AccountRepository,
        passwords: Passwords,
        mailer: VerificationMailer,
        policy: AuthPolicy,
    ) -> None:
        self.repository = repository
        self.passwords = passwords
        self.mailer = mailer
        self.policy = policy

    def _attempt(self, operation: str, identity: str, now: datetime) -> None:
        self.repository.take_attempt(
            digest(f"{operation}:{identity}"),
            now,
            self.policy.attempt_window_minutes,
            self.policy.attempt_limit,
        )

    def register(self, email: str, client_key: str) -> None:
        now = datetime.now(UTC)
        self._attempt("register-ip", client_key, now)
        email = self._email(email)
        self._attempt("register-email", email, now)
        # 登録済みでも同じ外部応答。確認済みのパスワードを変更しない。
        if self.repository.account_exists(email):
            return
        token = secrets.token_urlsafe(32)
        expires = now + timedelta(minutes=self.policy.verification_minutes)
        self.repository.save_verification(email, digest(token), expires)
        self.mailer.send(email, token)

    def verify(self, token: str, password: str, client_key: str) -> Account:
        now = datetime.now(UTC)
        self._attempt("verify-ip", client_key, now)
        if (
            not self.policy.password_min_length
            <= len(password)
            <= self.policy.password_max_length
        ):
            raise AuthError("invalid_password")
        if not 20 <= len(token) <= 128:
            raise AuthError("invalid_verification")
        return self.repository.complete_registration(
            digest(token), self.passwords.hash(password), now
        )

    def login(
        self, email: str, password: str, client_key: str
    ) -> tuple[SessionIdentity, str]:
        now = datetime.now(UTC)
        self._attempt("login-ip", client_key, now)
        email = self._email(email)
        self._attempt("login-email", email, now)
        if len(password) > self.policy.password_max_length:
            raise AuthError("invalid_credentials")
        credentials = self.repository.credentials(email)
        valid = self.passwords.verify(credentials[1] if credentials else None, password)
        if not valid or credentials is None:
            raise AuthError("invalid_credentials")
        account = credentials[0]
        token = secrets.token_urlsafe(32)
        csrf = digest(f"csrf:{token}")
        expires = now + timedelta(hours=self.policy.session_hours)
        self.repository.save_session(account, digest(token), csrf, expires)
        return SessionIdentity(
            account=account, csrf_token=csrf, expires_at=expires
        ), token

    def session(self, token: str) -> SessionIdentity:
        identity = self.repository.session(digest(token), datetime.now(UTC))
        if identity is None:
            raise AuthError("invalid_credentials")
        csrf = digest(f"csrf:{token}")
        if not secrets.compare_digest(digest(csrf), identity.csrf_token_hash):
            raise AuthError("invalid_credentials")
        return SessionIdentity(
            account=identity.account, csrf_token=csrf, expires_at=identity.expires_at
        )

    def logout(self, token: str, csrf: str) -> None:
        identity = self.session(token)
        if not secrets.compare_digest(identity.csrf_token, csrf):
            raise AuthError("invalid_csrf")
        self.repository.revoke_session(digest(token), datetime.now(UTC))

    @staticmethod
    def _email(email: str) -> str:
        try:
            return validate_registration_email(email)
        except ValueError as error:
            raise AuthError("invalid_email") from error

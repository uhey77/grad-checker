"""ユーザー名とパスワードによる登録・復旧・本人セッション管理。"""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Protocol

from pydantic import BaseModel, ConfigDict

from modules.accounts.grad_checker_accounts.application.errors.auth import AuthError
from modules.accounts.grad_checker_accounts.domain.username import (
    normalize_username,
)
from modules.shared.grad_checker_shared.application.unit_of_work import UnitOfWork


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

    session_hours: int
    password_min_length: int
    password_max_length: int
    attempt_window_minutes: int
    attempt_limit: int


class AccountRepository(Protocol):
    def take_attempt(
        self, key: str, now: datetime, window: int, limit: int
    ) -> None: ...
    def register(
        self, username: str, password_hash: str, recovery_hash: str, now: datetime
    ) -> Account: ...
    def reset_credentials(
        self,
        username: str,
        recovery_hash: str,
        password_hash: str,
        new_recovery_hash: str,
        now: datetime,
    ) -> str | None:
        """復旧コードが一致した場合だけ更新し、アカウントIDを返す。"""
        ...

    def revoke_sessions(self, student_id: str, now: datetime) -> None: ...
    def credentials(self, username: str) -> tuple[Account, str] | None: ...
    def save_session(
        self,
        account: Account,
        token_hash: str,
        csrf: str,
        expires: datetime,
        password_hash: str,
    ) -> bool:
        """照合したパスワードハッシュが現在も有効な場合だけ保存する。"""
        ...

    def session(self, token_hash: str, now: datetime) -> StoredSession | None: ...
    def revoke_session(self, token_hash: str, now: datetime) -> None: ...


class AccountUnitOfWork(UnitOfWork, Protocol):
    @property
    def accounts(self) -> AccountRepository: ...


class Passwords(Protocol):
    def hash(self, password: str) -> str: ...
    def verify(self, password_hash: str | None, password: str) -> bool: ...


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


class AuthService:
    def __init__(
        self,
        uow: AccountUnitOfWork,
        passwords: Passwords,
        policy: AuthPolicy,
    ) -> None:
        self.uow = uow
        self.passwords = passwords
        self.policy = policy

    def _attempt(self, operation: str, identity: str, now: datetime) -> None:
        # 試行回数は操作本体と別にcommitし、後続の検証や保存が失敗しても残す。
        with self.uow.write():
            self.uow.accounts.take_attempt(
                digest(f"{operation}:{identity}"),
                now,
                self.policy.attempt_window_minutes,
                self.policy.attempt_limit,
            )

    def _password(self, password: str) -> None:
        if (
            not self.policy.password_min_length
            <= len(password)
            <= self.policy.password_max_length
        ):
            raise AuthError("invalid_password")

    def register(self, username: str, password: str, client_key: str) -> str:
        now = datetime.now(UTC)
        self._attempt("register-ip", client_key, now)
        username = self._username(username)
        self._attempt("register-username", username, now)
        self._password(password)
        recovery = secrets.token_urlsafe(32)
        # ハッシュ計算は書込みロックの外で行う。
        password_hash = self.passwords.hash(password)
        with self.uow.write():
            self.uow.accounts.register(username, password_hash, digest(recovery), now)
        return recovery

    def recover(
        self, username: str, recovery_code: str, password: str, client_key: str
    ) -> str:
        now = datetime.now(UTC)
        self._attempt("recover-ip", client_key, now)
        username = self._username(username)
        self._attempt("recover-username", username, now)
        self._password(password)
        if len(recovery_code) != 43:
            raise AuthError("invalid_recovery")
        recovery = secrets.token_urlsafe(32)
        password_hash = self.passwords.hash(password)
        # コードの照合・更新、パスワード更新、全セッションの失効を一度に行う。
        with self.uow.write():
            student_id = self.uow.accounts.reset_credentials(
                username, digest(recovery_code), password_hash, digest(recovery), now
            )
            if student_id is None:
                raise AuthError("invalid_recovery")
            self.uow.accounts.revoke_sessions(student_id, now)
        return recovery

    def login(
        self, username: str, password: str, client_key: str
    ) -> tuple[SessionIdentity, str]:
        now = datetime.now(UTC)
        self._attempt("login-ip", client_key, now)
        username = self._username(username)
        self._attempt("login-username", username, now)
        if len(password) > self.policy.password_max_length:
            raise AuthError("invalid_credentials")
        with self.uow.read():
            credentials = self.uow.accounts.credentials(username)
        # パスワードの照合はトランザクションの外で行う。
        valid = self.passwords.verify(credentials[1] if credentials else None, password)
        if not valid or credentials is None:
            raise AuthError("invalid_credentials")
        account = credentials[0]
        token = secrets.token_urlsafe(32)
        csrf = digest(f"csrf:{token}")
        expires = now + timedelta(hours=self.policy.session_hours)
        with self.uow.write():
            # 照合後に復旧で変更されたパスワードからは、セッションを作らない。
            if not self.uow.accounts.save_session(
                account, digest(token), csrf, expires, credentials[1]
            ):
                raise AuthError("invalid_credentials")
        return SessionIdentity(
            account=account, csrf_token=csrf, expires_at=expires
        ), token

    def session(self, token: str) -> SessionIdentity:
        # 有効なセッションの最終利用日時を更新するため、書込みで確認する。
        with self.uow.write():
            identity = self.uow.accounts.session(digest(token), datetime.now(UTC))
        if identity is None:
            raise AuthError("invalid_credentials")
        csrf = digest(f"csrf:{token}")
        if not secrets.compare_digest(digest(csrf), identity.csrf_token_hash):
            raise AuthError("invalid_credentials")
        return SessionIdentity(
            account=identity.account, csrf_token=csrf, expires_at=identity.expires_at
        )

    def authorize(self, token: str, csrf: str) -> SessionIdentity:
        """本人データを変更する要求のセッションとCSRFトークンを確認する。"""
        identity = self.session(token)
        if not secrets.compare_digest(identity.csrf_token, csrf):
            raise AuthError("invalid_csrf")
        return identity

    def logout(self, token: str, csrf: str) -> None:
        self.authorize(token, csrf)
        with self.uow.write():
            self.uow.accounts.revoke_session(digest(token), datetime.now(UTC))

    @staticmethod
    def _username(username: str) -> str:
        try:
            return normalize_username(username)
        except ValueError as error:
            raise AuthError("invalid_username") from error

"""ユーザー名とパスワードによる登録・復旧・本人セッション管理。"""

import hashlib
from abc import ABC, abstractmethod
from datetime import datetime

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


class AccountRepository(ABC):
    @abstractmethod
    def take_attempt(
        self, key: str, now: datetime, window: int, limit: int
    ) -> None: ...

    @abstractmethod
    def register(
        self, username: str, password_hash: str, recovery_hash: str, now: datetime
    ) -> Account: ...

    @abstractmethod
    def reset_credentials(
        self,
        username: str,
        recovery_hash: str,
        password_hash: str,
        new_recovery_hash: str,
        now: datetime,
    ) -> str | None:
        """復旧コードが一致した場合だけ更新し、アカウントIDを返す。"""

    @abstractmethod
    def revoke_sessions(self, student_id: str, now: datetime) -> None: ...

    @abstractmethod
    def credentials(self, username: str) -> tuple[Account, str] | None: ...

    @abstractmethod
    def save_session(
        self,
        account: Account,
        token_hash: str,
        csrf: str,
        expires: datetime,
        password_hash: str,
    ) -> bool:
        """照合したパスワードハッシュが現在も有効な場合だけ保存する。"""

    @abstractmethod
    def session(self, token_hash: str, now: datetime) -> StoredSession | None: ...

    @abstractmethod
    def revoke_session(self, token_hash: str, now: datetime) -> None: ...


class AccountUnitOfWork(UnitOfWork):
    @property
    @abstractmethod
    def accounts(self) -> AccountRepository: ...


class Passwords(ABC):
    @abstractmethod
    def hash(self, password: str) -> str: ...

    @abstractmethod
    def verify(self, password_hash: str | None, password: str) -> bool: ...


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def record_attempt(
    uow: AccountUnitOfWork,
    policy: AuthPolicy,
    operation: str,
    identity: str,
    now: datetime,
) -> None:
    # 操作本体が失敗しても試行回数は残す。
    with uow.write():
        uow.accounts.take_attempt(
            digest(f"{operation}:{identity}"),
            now,
            policy.attempt_window_minutes,
            policy.attempt_limit,
        )


def check_password(policy: AuthPolicy, password: str) -> None:
    if not policy.password_min_length <= len(password) <= policy.password_max_length:
        raise AuthError("invalid_password")


def normalize_login_name(value: str) -> str:
    try:
        return normalize_username(value)
    except ValueError as error:
        raise AuthError("invalid_username") from error

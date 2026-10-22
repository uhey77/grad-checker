"""ユーザー名・パスワードの検証と認証試行の共通処理。"""

import hashlib
from datetime import datetime

from modules.accounts.application.dto.auth import AuthPolicy
from modules.accounts.application.errors.auth import AuthError
from modules.accounts.application.uow.auth import AccountUnitOfWork
from modules.accounts.domain.value_objects.username import normalize_username


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

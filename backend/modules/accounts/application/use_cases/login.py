"""LoginUseCaseの処理手順とトランザクション境界。"""

import secrets
from datetime import timedelta

from modules.accounts.application.dto.auth import AuthPolicy, SessionIdentity
from modules.accounts.application.errors.auth import AuthError
from modules.accounts.application.ports.auth import Passwords
from modules.accounts.application.services.auth import (
    digest,
    normalize_login_name,
    record_attempt,
)
from modules.accounts.application.uow.auth import AccountUnitOfWork
from shared.application.ports.clock import Clock


class LoginUseCase:
    def __init__(
        self,
        uow: AccountUnitOfWork,
        passwords: Passwords,
        policy: AuthPolicy,
        clock: Clock,
    ) -> None:
        self.uow = uow
        self.passwords = passwords
        self.policy = policy
        self.clock = clock

    def execute(
        self, username: str, password: str, client_key: str
    ) -> tuple[SessionIdentity, str]:
        now = self.clock.now()
        record_attempt(self.uow, self.policy, "login-ip", client_key, now)
        username = normalize_login_name(username)
        record_attempt(self.uow, self.policy, "login-username", username, now)
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

"""RegisterAccountUseCaseの処理手順とトランザクション境界。"""

import secrets

from modules.accounts.application.dto.auth import AuthPolicy
from modules.accounts.application.ports.auth import Passwords
from modules.accounts.application.services.auth import (
    check_password,
    digest,
    normalize_login_name,
    record_attempt,
)
from modules.accounts.application.uow.auth import AccountUnitOfWork
from shared.application.ports.clock import Clock


class RegisterAccountUseCase:
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

    def execute(self, username: str, password: str, client_key: str) -> str:
        now = self.clock.now()
        record_attempt(self.uow, self.policy, "register-ip", client_key, now)
        username = normalize_login_name(username)
        record_attempt(self.uow, self.policy, "register-username", username, now)
        check_password(self.policy, password)
        recovery = secrets.token_urlsafe(32)
        # ハッシュ計算は書込みロックの外で行う。
        password_hash = self.passwords.hash(password)
        with self.uow.write():
            self.uow.accounts.register(username, password_hash, digest(recovery), now)
        return recovery

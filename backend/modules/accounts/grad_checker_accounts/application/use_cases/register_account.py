"""RegisterAccountUseCaseの処理手順とトランザクション境界。"""

import secrets

from modules.shared.grad_checker_shared.application.ports.clock import Clock

from ..dto.auth import AuthPolicy
from ..ports.auth import AccountUnitOfWork, Passwords
from ..services.auth import check_password, digest, normalize_login_name, record_attempt


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

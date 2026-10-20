"""RecoverAccountUseCaseの処理手順とトランザクション境界。"""

import secrets

from modules.accounts.grad_checker_accounts.application.errors.auth import AuthError
from modules.shared.grad_checker_shared.application.clock import Clock

from ..auth import (
    AccountUnitOfWork,
    AuthPolicy,
    Passwords,
    check_password,
    digest,
    normalize_login_name,
    record_attempt,
)


class RecoverAccountUseCase:
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
        self, username: str, recovery_code: str, password: str, client_key: str
    ) -> str:
        now = self.clock.now()
        record_attempt(self.uow, self.policy, "recover-ip", client_key, now)
        username = normalize_login_name(username)
        record_attempt(self.uow, self.policy, "recover-username", username, now)
        check_password(self.policy, password)
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

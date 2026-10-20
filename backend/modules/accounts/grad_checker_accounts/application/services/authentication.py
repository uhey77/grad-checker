"""セッション・CSRFの照合と最終利用日時の更新手順。"""

import secrets

from modules.shared.grad_checker_shared.application.ports.clock import Clock

from ..dto.auth import SessionIdentity
from ..errors.auth import AuthError
from ..ports.auth import AccountUnitOfWork
from .auth import digest


class SessionAuthentication:
    def __init__(self, uow: AccountUnitOfWork, clock: Clock) -> None:
        self.uow = uow
        self.clock = clock

    def authenticate(self, token: str, csrf: str | None = None) -> SessionIdentity:
        # 最終利用日時は、従来通り独立したwriteで更新する。
        with self.uow.write():
            identity = self.uow.accounts.session(digest(token), self.clock.now())
        if identity is None:
            raise AuthError("invalid_credentials")
        expected_csrf = digest(f"csrf:{token}")
        if not secrets.compare_digest(digest(expected_csrf), identity.csrf_token_hash):
            raise AuthError("invalid_credentials")
        if csrf is not None and not secrets.compare_digest(expected_csrf, csrf):
            raise AuthError("invalid_csrf")
        return SessionIdentity(
            account=identity.account,
            csrf_token=expected_csrf,
            expires_at=identity.expires_at,
        )

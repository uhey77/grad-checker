"""本人確認の後、指定したセッションを失効させる。"""

from modules.shared.grad_checker_shared.application.clock import Clock

from ..auth import AccountUnitOfWork, digest
from ..authentication import SessionAuthentication


class LogoutUseCase:
    def __init__(
        self,
        uow: AccountUnitOfWork,
        authentication: SessionAuthentication,
        clock: Clock,
    ) -> None:
        self.uow = uow
        self.authentication = authentication
        self.clock = clock

    def execute(self, token: str, csrf: str) -> None:
        self.authentication.authenticate(token, csrf)
        with self.uow.write():
            self.uow.accounts.revoke_session(digest(token), self.clock.now())

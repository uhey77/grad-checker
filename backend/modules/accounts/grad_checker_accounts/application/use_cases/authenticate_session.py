"""本人セッションと、変更時のCSRFを確認する。"""

from ..dto.auth import SessionIdentity
from ..services.authentication import SessionAuthentication


class AuthenticateSessionUseCase:
    def __init__(self, authentication: SessionAuthentication) -> None:
        self.authentication = authentication

    def execute(self, token: str, csrf: str | None = None) -> SessionIdentity:
        return self.authentication.authenticate(token, csrf)

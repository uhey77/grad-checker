"""本人セッションと、変更時のCSRFを確認する。"""

from ..auth import SessionIdentity
from ..authentication import SessionAuthentication


class AuthenticateSessionUseCase:
    def __init__(self, authentication: SessionAuthentication) -> None:
        self.authentication = authentication

    def execute(self, token: str, csrf: str | None = None) -> SessionIdentity:
        return self.authentication.authenticate(token, csrf)

"""認証ユースケースの内部呼出し。Cookieと外部HTTPはGoが管理する。"""

from typing import Literal, Self

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict, Field, model_validator

from api.api_service.presentation.dependencies import SessionDependency
from modules.accounts.grad_checker_accounts.application.auth import (
    AuthError,
    AuthPolicy,
    AuthService,
)
from modules.accounts.grad_checker_accounts.infrastructure.repository import (
    SqliteAccountRepository,
)

router = APIRouter(prefix="/internal")


class AuthCall(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    operation: Literal["register", "verify", "login", "session", "logout", "config"]
    email: str = Field(default="", max_length=254)
    password: str = Field(default="", max_length=1024)
    token: str = Field(default="", max_length=128)
    csrf: str = Field(default="", max_length=128)
    client_key: str = Field(default="", max_length=128)

    @model_validator(mode="after")
    def validate_arguments(self) -> Self:
        required = {
            "config": set(),
            "register": {"email", "client_key"},
            "verify": {"token", "password", "client_key"},
            "login": {"email", "password", "client_key"},
            "session": {"token"},
            "logout": {"token", "csrf"},
        }[self.operation]
        for field in ("email", "password", "token", "csrf", "client_key"):
            if bool(getattr(self, field)) != (field in required):
                raise ValueError("operation and arguments do not match")
        return self


@router.post("/auth")
def auth(
    call: AuthCall, request: Request, session: SessionDependency
) -> dict[str, object]:
    settings = request.app.state.settings
    service = AuthService(
        SqliteAccountRepository(session),
        request.app.state.passwords,
        request.app.state.verification_mailer,
        AuthPolicy(
            verification_minutes=settings.auth_verification_minutes,
            session_hours=settings.auth_session_hours,
            password_min_length=settings.auth_password_min_length,
            password_max_length=settings.auth_password_max_length,
            attempt_window_minutes=settings.auth_attempt_window_minutes,
            attempt_limit=settings.auth_attempt_limit,
        ),
    )
    try:
        if call.operation == "config":
            return {
                "data": {
                    "policy": {
                        "password_min_length": settings.auth_password_min_length,
                        "password_max_length": settings.auth_password_max_length,
                        "verification_minutes": settings.auth_verification_minutes,
                    }
                }
            }
        if call.operation == "register":
            service.register(call.email, call.client_key)
            return {"data": {"accepted": True}}
        if call.operation == "verify":
            service.verify(call.token, call.password, call.client_key)
            return {"data": {"verified": True}}
        if call.operation == "logout":
            service.logout(call.token, call.csrf)
            return {"data": {"authenticated": False}}
        raw_token = None
        if call.operation == "login":
            identity, raw_token = service.login(
                call.email, call.password, call.client_key
            )
        else:
            identity = service.session(call.token)
        data: dict[str, object] = {
            "authenticated": True,
            "student": {
                "id": identity.account.id,
                "login_name": identity.account.login_name,
            },
            "csrf_token": identity.csrf_token,
            "expires_at": identity.expires_at.isoformat(),
        }
        if raw_token is not None:
            data["session_token"] = raw_token
        return {"data": data}
    except AuthError as error:
        return {"error": {"code": error.code}}

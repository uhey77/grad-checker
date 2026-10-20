"""認証ユースケースのブリッジ呼出し。Cookieと外部HTTPはGoが管理する。"""

from typing import Annotated, Literal, Self

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field, model_validator

from api.api_service.presentation.dependencies import auth_service
from api.api_service.presentation.go_bridge_call import respond
from modules.accounts.grad_checker_accounts.public import AuthService

router = APIRouter(prefix="/bridge")


class AuthCall(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    operation: Literal["register", "recover", "login", "session", "logout", "config"]
    login_name: str = Field(default="", max_length=32)
    recovery_code: str = Field(default="", max_length=128)
    password: str = Field(default="", max_length=1024)
    token: str = Field(default="", max_length=128)
    csrf: str = Field(default="", max_length=128)
    client_key: str = Field(default="", max_length=128)

    @model_validator(mode="after")
    def validate_arguments(self) -> Self:
        required = {
            "config": set(),
            "register": {"login_name", "password", "client_key"},
            "recover": {"login_name", "recovery_code", "password", "client_key"},
            "login": {"login_name", "password", "client_key"},
            "session": {"token"},
            "logout": {"token", "csrf"},
        }[self.operation]
        for field in (
            "login_name",
            "recovery_code",
            "password",
            "token",
            "csrf",
            "client_key",
        ):
            if bool(getattr(self, field)) != (field in required):
                raise ValueError("operation and arguments do not match")
        return self


@router.post("/auth")
def auth(
    call: AuthCall, service: Annotated[AuthService, Depends(auth_service)]
) -> dict[str, object]:

    def run() -> object:
        if call.operation == "config":
            return {
                "policy": {
                    "password_min_length": service.policy.password_min_length,
                    "password_max_length": service.policy.password_max_length,
                }
            }
        if call.operation == "register":
            recovery = service.register(call.login_name, call.password, call.client_key)
            return {"registered": True, "recovery_code": recovery}
        if call.operation == "recover":
            recovery = service.recover(
                call.login_name, call.recovery_code, call.password, call.client_key
            )
            return {"recovered": True, "recovery_code": recovery}
        if call.operation == "logout":
            service.logout(call.token, call.csrf)
            return {"authenticated": False}
        raw_token = None
        if call.operation == "login":
            identity, raw_token = service.login(
                call.login_name, call.password, call.client_key
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
        return data

    return respond(run)

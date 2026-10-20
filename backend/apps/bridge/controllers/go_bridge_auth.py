"""認証ユースケースのブリッジ呼出し。Cookieと外部HTTPはGoが管理する。"""

from typing import Annotated

from fastapi import APIRouter, Depends

from apps.bridge.controllers.go_bridge_call import respond
from apps.bridge.dependencies import (
    authenticate_session,
    get_auth_policy,
    login,
    logout,
    recover_account,
    register_account,
)
from apps.bridge.schemas.auth import AuthCall
from modules.accounts.public import (
    AuthenticateSessionUseCase,
    GetAuthPolicyUseCase,
    LoginUseCase,
    LogoutUseCase,
    RecoverAccountUseCase,
    RegisterAccountUseCase,
)

router = APIRouter(prefix="/bridge")


@router.post("/auth")
def auth(
    call: AuthCall,
    *,
    register_account: Annotated[RegisterAccountUseCase, Depends(register_account)],
    recover_account: Annotated[RecoverAccountUseCase, Depends(recover_account)],
    login: Annotated[LoginUseCase, Depends(login)],
    logout: Annotated[LogoutUseCase, Depends(logout)],
    authenticate_session: Annotated[
        AuthenticateSessionUseCase, Depends(authenticate_session)
    ],
    get_auth_policy: Annotated[GetAuthPolicyUseCase, Depends(get_auth_policy)],
) -> dict[str, object]:

    def run() -> object:
        if call.operation == "config":
            policy = get_auth_policy.execute()
            return {
                "policy": {
                    "password_min_length": policy.password_min_length,
                    "password_max_length": policy.password_max_length,
                }
            }
        if call.operation == "register":
            recovery = register_account.execute(
                call.login_name, call.password, call.client_key
            )
            return {"registered": True, "recovery_code": recovery}
        if call.operation == "recover":
            recovery = recover_account.execute(
                call.login_name, call.recovery_code, call.password, call.client_key
            )
            return {"recovered": True, "recovery_code": recovery}
        if call.operation == "logout":
            logout.execute(call.token, call.csrf)
            return {"authenticated": False}
        raw_token = None
        if call.operation == "login":
            identity, raw_token = login.execute(
                call.login_name, call.password, call.client_key
            )
        else:
            identity = authenticate_session.execute(call.token)
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

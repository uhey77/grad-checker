"""ブリッジ呼出しごとのPythonリソース管理。"""

from fastapi import Request
from sqlalchemy import Engine

from modules.accounts.grad_checker_accounts.application.auth import (
    AuthPolicy,
    AuthService,
    SessionIdentity,
)
from modules.accounts.grad_checker_accounts.infrastructure.repository import (
    SqliteAccountUnitOfWork,
)


def database_engine(request: Request) -> Engine:
    """各モジュールのUnit of Workへ渡すDBエンジン。"""
    return request.app.state.database_engine


def auth_service(request: Request) -> AuthService:
    settings = request.app.state.settings
    return AuthService(
        SqliteAccountUnitOfWork(database_engine(request)),
        request.app.state.passwords,
        AuthPolicy(
            session_hours=settings.auth_session_hours,
            password_min_length=settings.auth_password_min_length,
            password_max_length=settings.auth_password_max_length,
            attempt_window_minutes=settings.auth_attempt_window_minutes,
            attempt_limit=settings.auth_attempt_limit,
        ),
    )


def current_identity(
    request: Request, token: str, csrf: str | None = None
) -> SessionIdentity:
    """本人をセッションから決定する。変更操作はCSRFトークンを渡して照合する。"""
    service = auth_service(request)
    if csrf is None:
        return service.session(token)
    return service.authorize(token, csrf)

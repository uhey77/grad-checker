"""ブリッジ呼出しごとのPythonリソース管理。"""

from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Request
from sqlmodel import Session

from modules.accounts.grad_checker_accounts.application.auth import (
    AuthPolicy,
    AuthService,
    SessionIdentity,
)
from modules.accounts.grad_checker_accounts.infrastructure.repository import (
    SqliteAccountRepository,
)


def get_session(request: Request) -> Iterator[Session]:
    # commitはユースケース側で明示する。終了時に未commitの変更は破棄される。
    with Session(request.app.state.database_engine) as session:
        yield session


SessionDependency = Annotated[Session, Depends(get_session)]


def auth_service(request: Request, session: Session) -> AuthService:
    settings = request.app.state.settings
    return AuthService(
        SqliteAccountRepository(session),
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
    request: Request, session: Session, token: str, csrf: str | None = None
) -> SessionIdentity:
    """本人をセッションから決定する。変更操作はCSRFトークンを渡して照合する。"""
    service = auth_service(request, session)
    if csrf is None:
        return service.session(token)
    return service.authorize(token, csrf)

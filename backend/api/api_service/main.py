"""アプリケーション生成と、各層の依存関係の組み立て。"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlmodel import SQLModel

from api.api_service.presentation.internal_auth import router as internal_auth_router
from api.api_service.presentation.internal_subject_list import (
    router as internal_subject_list_router,
)
from config.settings import Settings
from modules.accounts.grad_checker_accounts.infrastructure.mailer import (
    SmtpVerificationMailer,
)
from modules.accounts.grad_checker_accounts.infrastructure.models import ACCOUNT_TABLES
from modules.accounts.grad_checker_accounts.infrastructure.passwords import (
    ArgonPasswords,
)
from modules.subjects.grad_checker_subjects.infrastructure.database import (
    create_database_engine,
    create_database_schema,
)


def create_app(settings: Settings | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncGenerator[None]:
        runtime_settings = settings or Settings()
        engine = create_database_engine(runtime_settings.database_url)
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            create_database_schema(engine)
            SQLModel.metadata.create_all(engine, tables=ACCOUNT_TABLES)
            application.state.database_engine = engine
            application.state.settings = runtime_settings
            application.state.passwords = ArgonPasswords()
            application.state.verification_mailer = SmtpVerificationMailer(
                host=runtime_settings.smtp_host,
                port=runtime_settings.smtp_port,
                username=runtime_settings.smtp_username,
                password=runtime_settings.smtp_password.get_secret_value(),
                sender=runtime_settings.smtp_sender,
                origin=runtime_settings.public_origin,
                starttls=runtime_settings.smtp_starttls,
                minutes=runtime_settings.auth_verification_minutes,
            )
            yield
        finally:
            engine.dispose()

    application = FastAPI(
        title="卒業要件チェッカー内部サービス",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    @application.exception_handler(RequestValidationError)
    def invalid_internal_call(
        _request: Request, _error: RequestValidationError
    ) -> JSONResponse:
        # 内部呼出しの契約違反。利用者向け422への変換はここで行わない。
        return JSONResponse({"error": {"code": "invalid_request"}})

    application.include_router(internal_subject_list_router)
    application.include_router(internal_auth_router)
    return application


app = create_app()

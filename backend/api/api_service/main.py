"""アプリケーション生成と、各層の依存関係の組み立て。"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from grad_checker_config.settings import Settings
from grad_checker_subjects.infrastructure.database import (
    create_database_engine,
    create_database_schema,
)
from sqlalchemy import text

from api_service.presentation.internal_subject_list import (
    router as internal_subject_list_router,
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
            application.state.database_engine = engine
            application.state.settings = runtime_settings
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
    return application


app = create_app()

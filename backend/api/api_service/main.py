"""アプリケーション生成と、各層の依存関係の組み立て。"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import text

from api.api_service.presentation.go_bridge_auth import router as bridge_auth_router
from api.api_service.presentation.go_bridge_call import failure
from api.api_service.presentation.go_bridge_checks import (
    router as bridge_checks_router,
)
from api.api_service.presentation.go_bridge_courses import (
    router as bridge_courses_router,
)
from api.api_service.presentation.go_bridge_evaluation import (
    router as bridge_evaluation_router,
)
from api.api_service.presentation.go_bridge_grades import (
    router as bridge_grades_router,
)
from api.api_service.presentation.go_bridge_profile import (
    router as bridge_profile_router,
)
from api.api_service.presentation.go_bridge_subject_list import (
    router as bridge_subject_list_router,
)
from config.settings import Settings
from modules.accounts.grad_checker_accounts.infrastructure.passwords import (
    ArgonPasswords,
)
from modules.accounts.grad_checker_accounts.infrastructure.schema import (
    create_account_schema,
)
from modules.grades.grad_checker_grades.infrastructure.schema import (
    create_grade_schema,
)
from modules.requirements.grad_checker_requirements.infrastructure.schema import (
    create_requirement_schema,
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
            create_account_schema(engine)
            create_grade_schema(engine)
            create_requirement_schema(engine)
            application.state.database_engine = engine
            application.state.settings = runtime_settings
            application.state.passwords = ArgonPasswords()
            yield
        finally:
            engine.dispose()

    application = FastAPI(
        title="卒業要件チェッカーPythonサービス",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    @application.exception_handler(RequestValidationError)
    def invalid_go_bridge_call(
        _request: Request, _error: RequestValidationError
    ) -> JSONResponse:
        # ブリッジ呼出しの契約違反。利用者向け422への変換はここで行わない。
        return JSONResponse(failure("invalid_request"))

    application.include_router(bridge_subject_list_router)
    application.include_router(bridge_auth_router)
    application.include_router(bridge_profile_router)
    application.include_router(bridge_courses_router)
    application.include_router(bridge_grades_router)
    application.include_router(bridge_evaluation_router)
    application.include_router(bridge_checks_router)
    return application


app = create_app()

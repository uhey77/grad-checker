"""アプリケーション生成と、各層の依存関係の組み立て。"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from sqlalchemy import text

from apps.bridge.composition import build_dependencies
from apps.bridge.controllers.go_bridge_auth import router as bridge_auth_router
from apps.bridge.controllers.go_bridge_checks import router as bridge_checks_router
from apps.bridge.controllers.go_bridge_courses import router as bridge_courses_router
from apps.bridge.controllers.go_bridge_evaluation import (
    router as bridge_evaluation_router,
)
from apps.bridge.controllers.go_bridge_grades import router as bridge_grades_router
from apps.bridge.controllers.go_bridge_profile import router as bridge_profile_router
from apps.bridge.controllers.go_bridge_subject_list import (
    router as bridge_subject_list_router,
)
from apps.bridge.middleware.errors import invalid_go_bridge_call
from apps.settings import Settings
from migrations.postgres import validate_database_schema
from modules.accounts.infrastructure.external_services.passwords import ArgonPasswords
from modules.accounts.infrastructure.persistence.schema import create_account_schema
from modules.grades.infrastructure.persistence.schema import create_grade_schema
from modules.requirements.infrastructure.persistence.schema import (
    create_requirement_schema,
)
from modules.subjects.infrastructure.persistence.database import create_database_schema
from shared.infrastructure.persistence.database import create_database_engine


def create_app(settings: Settings | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncGenerator[None]:
        runtime_settings = settings or Settings()
        engine = create_database_engine(runtime_settings.database_url)
        installed_dependencies = {}
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            if engine.dialect.name == "postgresql":
                # 本番起動でDDL・既存データ改訂を実行しない。
                with engine.connect() as connection:
                    validate_database_schema(connection)
            else:
                create_database_schema(engine)
                create_account_schema(engine)
                create_grade_schema(engine)
                create_requirement_schema(engine)
            application.state.database_engine = engine
            application.state.settings = runtime_settings
            application.state.passwords = ArgonPasswords()
            for dependency, factory in build_dependencies(
                engine, runtime_settings, application.state.passwords
            ).items():
                if dependency not in application.dependency_overrides:
                    application.dependency_overrides[dependency] = factory
                    installed_dependencies[dependency] = factory
            yield
        finally:
            for dependency, factory in installed_dependencies.items():
                if application.dependency_overrides.get(dependency) is factory:
                    del application.dependency_overrides[dependency]
            engine.dispose()

    application = FastAPI(
        title="卒業要件チェッカーPythonサービス",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    application.add_exception_handler(RequestValidationError, invalid_go_bridge_call)

    application.include_router(bridge_subject_list_router)
    application.include_router(bridge_auth_router)
    application.include_router(bridge_profile_router)
    application.include_router(bridge_courses_router)
    application.include_router(bridge_grades_router)
    application.include_router(bridge_evaluation_router)
    application.include_router(bridge_checks_router)
    return application


app = create_app()

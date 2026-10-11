"""アプリケーション生成と、各層の依存関係の組み立て。"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from app.config import Settings
from app.infrastructure.database import create_database_engine, create_database_schema
from app.presentation.health import router as health_router
from app.presentation.course_catalog import router as course_catalog_router


def create_app(settings: Settings | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
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

    application = FastAPI(title="卒業要件チェッカー", lifespan=lifespan)
    application.include_router(health_router, prefix="/api")
    application.include_router(course_catalog_router, prefix="/api")
    return application


app = create_app()

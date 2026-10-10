"""アプリケーション生成と、各層の依存関係の組み立て。"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from app.config import Settings
from app.infrastructure.database import create_database_engine
from app.presentation.health import router as health_router


def create_app(settings: Settings | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        engine = create_database_engine((settings or Settings.from_env()).database_url)
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            application.state.database_engine = engine
            yield
        finally:
            engine.dispose()

    application = FastAPI(title="卒業要件チェッカー", lifespan=lifespan)
    application.include_router(health_router, prefix="/api")
    return application


app = create_app()

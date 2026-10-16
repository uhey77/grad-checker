"""科目スキーマ生成後に、要件スキーマを追加する。既存行は変更しない。"""

from sqlalchemy import Engine
from sqlmodel import SQLModel

from modules.requirements.grad_checker_requirements.infrastructure.models import (
    REQUIREMENT_TABLES,
)


def create_requirement_schema(engine: Engine) -> None:
    SQLModel.metadata.create_all(engine, tables=REQUIREMENT_TABLES)

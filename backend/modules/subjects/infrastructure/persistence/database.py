"""SQLiteエンジンと、課程・科目データのスキーマの生成。"""

from sqlalchemy import Engine
from sqlmodel import SQLModel

from modules.subjects.infrastructure.persistence.models.subject_models import (
    SUBJECT_TABLES,
)


def create_database_schema(engine: Engine) -> None:
    SQLModel.metadata.create_all(engine, tables=SUBJECT_TABLES)

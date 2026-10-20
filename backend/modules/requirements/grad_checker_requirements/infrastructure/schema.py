"""要件・判定履歴のスキーマと、照合済みのCS2026規則改訂を適用する。"""

from sqlalchemy import Engine, inspect, text
from sqlmodel import SQLModel

from .check_models import CHECK_TABLES, IMMUTABLE_TRIGGER
from .cs_2026_revision import revise_cs_2026
from .models import REQUIREMENT_TABLES


def create_requirement_schema(engine: Engine) -> None:
    SQLModel.metadata.create_all(engine, tables=REQUIREMENT_TABLES + CHECK_TABLES)
    with engine.begin() as connection:
        connection.execute(text(IMMUTABLE_TRIGGER))
        if "allocation_policy" not in {
            col["name"] for col in inspect(connection).get_columns("credit_rules")
        }:
            connection.execute(
                text(
                    "ALTER TABLE credit_rules ADD COLUMN allocation_policy TEXT "
                    "CHECK (allocation_policy IS NULL OR (kind = 'other_faculty' "
                    "AND allocation_policy = 'chronological_best_fit_v1'))"
                )
            )
        revise_cs_2026(connection)

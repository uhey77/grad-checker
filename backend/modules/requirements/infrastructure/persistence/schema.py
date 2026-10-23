"""要件・判定履歴のスキーマと、照合済みのCS2026規則改訂を適用する。"""

from sqlalchemy import Connection, Engine, inspect, text
from sqlmodel import SQLModel

from migrations.cs_2026_revision import (
    revise_cs_2026,
)
from modules.requirements.infrastructure.persistence.models.check_models import (
    CHECK_TABLES,
    IMMUTABLE_TRIGGER,
)
from modules.requirements.infrastructure.persistence.models.models import (
    REQUIREMENT_TABLES,
)


def install_check_trigger(connection: Connection) -> None:
    if connection.dialect.name == "sqlite":
        connection.execute(text(IMMUTABLE_TRIGGER))
        return
    connection.execute(
        text(
            "CREATE FUNCTION reject_check_result_update() RETURNS trigger "
            "LANGUAGE plpgsql AS $$ BEGIN "
            "RAISE EXCEPTION 'check_results are immutable' USING ERRCODE = '23514'; "
            "END $$"
        )
    )
    connection.execute(
        text(
            "CREATE TRIGGER check_results_immutable BEFORE UPDATE ON check_results "
            "FOR EACH ROW EXECUTE FUNCTION reject_check_result_update()"
        )
    )


def create_requirement_schema(engine: Engine) -> None:
    SQLModel.metadata.create_all(engine, tables=REQUIREMENT_TABLES + CHECK_TABLES)
    with engine.begin() as connection:
        if connection.dialect.name == "sqlite":
            install_check_trigger(connection)
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

"""この業務モジュールの具体実装を操作別UseCaseへ注入する。"""

from collections.abc import Callable

from sqlalchemy import Engine

from modules.grades.infrastructure.persistence.unit_of_work import (
    SqliteGradeUnitOfWork,
)
from modules.grades.public import GetGradesUseCase, SaveGradesUseCase


def build_use_cases(engine: Engine) -> dict[str, Callable[[], object]]:
    return {
        "get_grades": lambda: GetGradesUseCase(SqliteGradeUnitOfWork(engine)),
        "save_grades": lambda: SaveGradesUseCase(SqliteGradeUnitOfWork(engine)),
    }

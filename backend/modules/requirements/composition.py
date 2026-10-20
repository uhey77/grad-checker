"""この業務モジュールの具体実装を操作別UseCaseへ注入する。"""

from collections.abc import Callable

from sqlalchemy import Engine

from modules.requirements.infrastructure.persistence.unit_of_work import (
    SqliteCheckUnitOfWork,
    SqliteEvaluationUnitOfWork,
    SqliteRequirementUnitOfWork,
)
from modules.requirements.public import (
    CreateCheckUseCase,
    EvaluateGraduationUseCase,
    GetCheckUseCase,
    GetDashboardUseCase,
    ImportRequirementsUseCase,
    ListChecksUseCase,
)
from shared.application.ports.clock import Clock


def build_use_cases(engine: Engine, clock: Clock) -> dict[str, Callable[[], object]]:
    return {
        "create_check": lambda: CreateCheckUseCase(
            SqliteCheckUnitOfWork(engine), clock
        ),
        "get_check": lambda: GetCheckUseCase(SqliteCheckUnitOfWork(engine)),
        "list_checks": lambda: ListChecksUseCase(SqliteCheckUnitOfWork(engine)),
        "evaluate_graduation": lambda: EvaluateGraduationUseCase(
            SqliteEvaluationUnitOfWork(engine), clock
        ),
        "get_dashboard": lambda: GetDashboardUseCase(
            SqliteEvaluationUnitOfWork(engine), clock
        ),
    }


def build_import_use_case(engine: Engine) -> ImportRequirementsUseCase:
    return ImportRequirementsUseCase(SqliteRequirementUnitOfWork(engine))

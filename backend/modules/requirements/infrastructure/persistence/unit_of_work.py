"""このモジュールのRepository・Queryを束ねるSQLiteのUnit of Work実装。"""

from sqlalchemy import Engine

from modules.requirements.application.uow.check_results import CheckUnitOfWork
from modules.requirements.application.uow.seed_import import RequirementUnitOfWork
from modules.requirements.application.uow.student_evaluation import EvaluationUnitOfWork
from modules.requirements.infrastructure.persistence.queries.evaluation import (
    SqliteEvaluationRepository,
)
from modules.requirements.infrastructure.persistence.queries.evaluation import (
    unavailable as evaluation_unavailable,
)
from modules.requirements.infrastructure.persistence.repositories.check_results import (
    SqliteCheckRepository,
)
from modules.requirements.infrastructure.persistence.repositories.check_results import (
    unavailable as check_results_unavailable,
)
from modules.requirements.infrastructure.persistence.repositories.seed import (
    SqliteRequirementDataStore,
)
from modules.requirements.infrastructure.persistence.repositories.seed import (
    unavailable as seed_unavailable,
)
from shared.infrastructure.persistence.unit_of_work import SqlUnitOfWork


class SqliteEvaluationUnitOfWork(SqlUnitOfWork, EvaluationUnitOfWork):
    def __init__(self, engine: Engine) -> None:
        super().__init__(engine, evaluation_unavailable)

    @property
    def evaluation(self) -> SqliteEvaluationRepository:
        return SqliteEvaluationRepository(self.session)


class SqliteRequirementUnitOfWork(SqlUnitOfWork, RequirementUnitOfWork):
    def __init__(self, engine: Engine) -> None:
        super().__init__(engine, seed_unavailable)

    @property
    def requirements(self) -> SqliteRequirementDataStore:
        return SqliteRequirementDataStore(self.session)


class SqliteCheckUnitOfWork(SqlUnitOfWork, CheckUnitOfWork):
    def __init__(self, engine: Engine) -> None:
        super().__init__(engine, check_results_unavailable)

    @property
    def evaluation(self) -> SqliteEvaluationRepository:
        return SqliteEvaluationRepository(self.session)

    @property
    def checks(self) -> SqliteCheckRepository:
        return SqliteCheckRepository(self.session)

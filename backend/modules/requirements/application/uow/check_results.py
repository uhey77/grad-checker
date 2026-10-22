from abc import abstractmethod

from modules.requirements.application.ports.check_results import CheckRepository
from modules.requirements.application.queries.student_evaluation import (
    EvaluationRepository,
)
from shared.application.uow.unit_of_work import UnitOfWork


class CheckUnitOfWork(UnitOfWork):
    @property
    @abstractmethod
    def evaluation(self) -> EvaluationRepository: ...

    @property
    @abstractmethod
    def checks(self) -> CheckRepository: ...

from abc import abstractmethod

from modules.requirements.application.queries.student_evaluation import (
    EvaluationRepository,
)
from shared.application.uow.unit_of_work import UnitOfWork


class EvaluationUnitOfWork(UnitOfWork):
    @property
    @abstractmethod
    def evaluation(self) -> EvaluationRepository: ...

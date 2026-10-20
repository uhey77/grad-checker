"""成績セットの取得・保存とトランザクションの契約。"""

from abc import ABC, abstractmethod

from modules.shared.grad_checker_shared.application.ports.unit_of_work import UnitOfWork

from ..dto.grades import GradeSet, StudentGrades


class GradeRepository(ABC):
    @abstractmethod
    def get_grades(self, student_id: str) -> StudentGrades: ...

    @abstractmethod
    def replace_grades(self, student_id: str, grade_set: GradeSet) -> StudentGrades: ...


class GradeUnitOfWork(UnitOfWork):
    @property
    @abstractmethod
    def grades(self) -> GradeRepository: ...

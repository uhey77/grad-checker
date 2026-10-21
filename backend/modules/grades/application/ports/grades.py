"""成績セットの取得・保存とトランザクションの契約。"""

from abc import ABC, abstractmethod

from modules.grades.application.dto.grades import GradeSet, StudentGrades


class GradeRepository(ABC):
    @abstractmethod
    def get_grades(self, student_id: str) -> StudentGrades: ...

    @abstractmethod
    def replace_grades(self, student_id: str, grade_set: GradeSet) -> StudentGrades: ...

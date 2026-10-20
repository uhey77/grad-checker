"""GetGradesUseCaseの処理手順とトランザクション境界。"""

from ..dto.grades import StudentGrades
from ..ports.grades import GradeUnitOfWork


class GetGradesUseCase:
    def __init__(self, uow: GradeUnitOfWork) -> None:
        self.uow = uow

    def execute(self, student_id: str) -> StudentGrades:
        # 成績とdata_revisionを同じ読取スナップショットから返す。
        with self.uow.read():
            return self.uow.grades.get_grades(student_id)

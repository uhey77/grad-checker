"""GetGradesUseCaseの処理手順とトランザクション境界。"""

from modules.grades.application.dto.grades import StudentGrades
from modules.grades.application.uow.grades import GradeUnitOfWork


class GetGradesUseCase:
    def __init__(self, uow: GradeUnitOfWork) -> None:
        self.uow = uow

    def execute(self, student_id: str) -> StudentGrades:
        # 成績とdata_revisionを同じ読取スナップショットから返す。
        with self.uow.read():
            return self.uow.grades.get_grades(student_id)

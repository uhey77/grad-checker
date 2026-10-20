"""SaveGradesUseCaseの処理手順とトランザクション境界。"""

from ..dto.grades import GradeSet, StudentGrades
from ..ports.grades import GradeUnitOfWork
from ..services.grade_validation import check_attempts


class SaveGradesUseCase:
    def __init__(self, uow: GradeUnitOfWork) -> None:
        self.uow = uow

    def execute(self, student_id: str, grade_set: GradeSet) -> StudentGrades:
        # 省略した回次は取消になるため、全集合を検証してから置換する。
        # 回次の検証はDBを使わないため、書込みロックの外で行う。
        check_attempts(grade_set.grades)
        # 版の確認から置換・版の加算までを、同じ書込みロックの下で行う。
        with self.uow.write():
            return self.uow.grades.replace_grades(student_id, grade_set)

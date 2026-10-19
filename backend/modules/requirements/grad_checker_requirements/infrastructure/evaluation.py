"""本人の所属・成績・マスタの取得。同じ読取り時点はUnit of Workが保証する。"""

from pydantic import ValidationError
from sqlalchemy import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session, col, select

from modules.accounts.grad_checker_accounts.infrastructure.models import Student
from modules.grades.grad_checker_grades.infrastructure.grades import attempt_data
from modules.grades.grad_checker_grades.infrastructure.models import GradeAttemptRecord
from modules.shared.grad_checker_shared.infrastructure.unit_of_work import (
    SqlUnitOfWork,
)
from modules.subjects.grad_checker_subjects.infrastructure.subject_data_import import (
    TABLE_MAPPING as SUBJECT_MAPPING,
)
from modules.subjects.grad_checker_subjects.infrastructure.subject_models import (
    CurriculumSubject,
)

from ..application.errors.evaluation import EvaluationError
from ..application.evaluation_models import EvaluationSnapshot
from ..application.student_evaluation import EvaluationRepository, EvaluationUnitOfWork
from .models import CreditRule, CreditRuleCourse
from .seed import TABLE_MAPPING


def unavailable(_error: SQLAlchemyError) -> EvaluationError:
    return EvaluationError("evaluation_unavailable", "判定用データを取得できません。")


class SqliteEvaluationRepository(EvaluationRepository):
    def __init__(self, session: Session) -> None:
        self.db = session

    def get_snapshot(self, student_id: str) -> EvaluationSnapshot:
        try:
            student = self.db.get(Student, student_id, populate_existing=True)
            if student is None:
                raise EvaluationError("student_not_found", "本人が見つかりません。")
            if student.program_id is None or student.curriculum_id is None:
                raise EvaluationError(
                    "program_not_selected", "所属を設定してください。"
                )
            grades = self.db.exec(
                select(GradeAttemptRecord).where(
                    col(GradeAttemptRecord.student_id) == student_id
                )
            ).all()
            own_ids = self.db.exec(
                select(CurriculumSubject.course_id).where(
                    col(CurriculumSubject.curriculum_id) == student.curriculum_id
                )
            ).all()
            external_ids = self.db.exec(
                select(CreditRuleCourse.course_id).where(
                    col(CreditRuleCourse.curriculum_id) == student.curriculum_id
                )
            ).all()
            course_ids = (
                set(own_ids) | set(external_ids) | {g.course_id for g in grades}
            )
            return EvaluationSnapshot.model_validate(
                {
                    "program_id": student.program_id,
                    "curriculum_id": student.curriculum_id,
                    "data_revision": student.data_revision,
                    "grades": [attempt_data(row) for row in grades],
                    "subjects": self._master(
                        SUBJECT_MAPPING, student.curriculum_id, course_ids
                    ),
                    "requirements": self._master(
                        TABLE_MAPPING, student.curriculum_id, course_ids
                    ),
                }
            )
        except ValidationError as error:
            raise EvaluationError(
                "invalid_evaluation_input", "保存済みの判定データが不正です。"
            ) from error

    def _master(self, mapping: tuple, curriculum_id: str, course_ids: set[str]) -> dict:
        # 本人課程と明示的な算入対象だけを読む。全課程マスタの増加を本人の
        # 判定コストにせず、無関係な未整備課程を本人の判定へ混在させない。
        result = {}
        for name, model, schema in mapping:
            query = select(model)
            if name == "curricula":
                query = query.where(col(model.id) == curriculum_id)
            elif name == "courses":
                query = query.where(col(model.id).in_(course_ids))
            elif name == "course_offerings":
                query = query.where(col(model.course_id).in_(course_ids))
            elif name == "credit_rule_limits":
                rule_ids = select(CreditRule.id).where(
                    col(CreditRule.curriculum_id) == curriculum_id
                )
                query = query.where(col(model.rule_id).in_(rule_ids))
            elif name != "academic_programs":
                query = query.where(col(model.curriculum_id) == curriculum_id)
            result[name] = [
                row.model_dump(include=set(schema.model_fields))
                for row in self.db.exec(query).all()
            ]
        return result


class SqliteEvaluationUnitOfWork(SqlUnitOfWork, EvaluationUnitOfWork):
    def __init__(self, engine: Engine) -> None:
        super().__init__(engine, unavailable)

    @property
    def evaluation(self) -> SqliteEvaluationRepository:
        return SqliteEvaluationRepository(self.session)

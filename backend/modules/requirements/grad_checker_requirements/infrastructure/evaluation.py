"""本人の所属・成績・マスタを同じSQLite読取り時点で取得する。"""

from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session, col, select

from modules.accounts.grad_checker_accounts.infrastructure.models import Student
from modules.grades.grad_checker_grades.infrastructure.grades import attempt_data
from modules.grades.grad_checker_grades.infrastructure.models import GradeAttemptRecord
from modules.shared.grad_checker_shared.infrastructure.transactions import read_snapshot
from modules.subjects.grad_checker_subjects.infrastructure.subject_data_import import (
    TABLE_MAPPING as SUBJECT_MAPPING,
)

from ..application.errors.evaluation import EvaluationError
from ..application.evaluation_models import EvaluationSnapshot
from .seed import TABLE_MAPPING


def unavailable(_error: SQLAlchemyError) -> EvaluationError:
    return EvaluationError("evaluation_unavailable", "判定用データを取得できません。")


class SqliteEvaluationRepository:
    def __init__(self, session: Session) -> None:
        self.db = session

    def get_snapshot(self, student_id: str) -> EvaluationSnapshot:
        try:
            with read_snapshot(self.db, unavailable):
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
                # 読取り専用。履歴作成や成績版の更新は行わない。
                return EvaluationSnapshot.model_validate(
                    {
                        "program_id": student.program_id,
                        "curriculum_id": student.curriculum_id,
                        "data_revision": student.data_revision,
                        "grades": [attempt_data(row) for row in grades],
                        "subjects": self._master(SUBJECT_MAPPING),
                        "requirements": self._master(TABLE_MAPPING),
                    }
                )
        except ValidationError as error:
            raise EvaluationError(
                "invalid_evaluation_input", "保存済みの判定データが不正です。"
            ) from error

    def _master(self, mapping: tuple) -> dict:
        return {
            name: [
                row.model_dump(include=set(schema.model_fields))
                for row in self.db.exec(select(model)).all()
            ]
            for name, model, schema in mapping
        }

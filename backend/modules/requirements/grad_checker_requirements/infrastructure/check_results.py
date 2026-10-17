"""判定履歴の保存と本人限定の取得。判定と保存を一つの書込みトランザクションで行う。"""

from datetime import UTC
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session, col, select

from modules.shared.grad_checker_shared.infrastructure.transactions import (
    database_errors,
    write_transaction,
)

from ..application.check_results import BuildCheck, CheckInput, SavedCheck
from ..application.errors.evaluation import EvaluationError
from ..application.student_evaluation import StudentEvaluation
from .check_models import CheckResultRecord
from .evaluation import SqliteEvaluationRepository


def unavailable(_error: SQLAlchemyError) -> EvaluationError:
    return EvaluationError("check_unavailable", "判定履歴を保存・取得できません。")


class SqliteCheckRepository:
    def __init__(self, session: Session) -> None:
        self.db = session
        self.evaluation = SqliteEvaluationRepository(session)

    def create_check(self, student_id: str, build: BuildCheck) -> SavedCheck:
        # 書込みロックの下で成績・所属・マスタを読み、判定から保存までを直列化する。
        with write_transaction(self.db, unavailable):
            check = build(self.evaluation.load_snapshot(student_id))
            self.db.add(
                CheckResultRecord(
                    id=str(check.id),
                    student_id=student_id,
                    input_json=check.input.model_dump_json(),
                    result_json=check.result.model_dump_json(),
                    curriculum_code=check.result.curriculum.code,
                    curriculum_revision=check.result.curriculum.revision,
                    data_revision=check.input.data_revision,
                    created_at=check.created_at,
                )
            )
            self.db.flush()
        # commitが成功してから結果を返す。
        return check

    def get_check(self, student_id: str, check_id: UUID) -> SavedCheck | None:
        with database_errors(unavailable):
            record = self.db.exec(
                select(CheckResultRecord).where(
                    col(CheckResultRecord.id) == str(check_id),
                    col(CheckResultRecord.student_id) == student_id,
                )
            ).first()
        if record is None:
            return None
        try:
            # 保存時のJSONだけから復元し、現在の成績・マスタを参照しない。
            return SavedCheck(
                id=UUID(record.id),
                created_at=record.created_at.replace(tzinfo=UTC),
                input=CheckInput.model_validate_json(record.input_json),
                result=StudentEvaluation.model_validate_json(record.result_json),
            )
        except ValidationError as error:
            raise EvaluationError(
                "invalid_check_result", "保存済みの判定履歴が不正です。"
            ) from error

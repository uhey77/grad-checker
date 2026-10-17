"""判定履歴の保存と本人限定の取得。トランザクションはUnit of Workが開始する。"""

from datetime import UTC
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session, col, select

from modules.shared.grad_checker_shared.infrastructure.unit_of_work import (
    SqlUnitOfWork,
)

from ..application.check_results import (
    CheckInput,
    CheckRepository,
    CheckUnitOfWork,
    SavedCheck,
)
from ..application.errors.evaluation import EvaluationError
from ..application.student_evaluation import StudentEvaluation
from .check_models import CheckResultRecord
from .evaluation import SqliteEvaluationRepository


def unavailable(_error: SQLAlchemyError) -> EvaluationError:
    return EvaluationError("check_unavailable", "判定履歴を保存・取得できません。")


class SqliteCheckRepository(CheckRepository):
    def __init__(self, session: Session) -> None:
        self.db = session

    def add(self, student_id: str, check: SavedCheck) -> None:
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

    def get(self, student_id: str, check_id: UUID) -> SavedCheck | None:
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


class SqliteCheckUnitOfWork(SqlUnitOfWork, CheckUnitOfWork):
    def __init__(self, engine: Engine) -> None:
        super().__init__(engine, unavailable)

    @property
    def evaluation(self) -> SqliteEvaluationRepository:
        return SqliteEvaluationRepository(self.session)

    @property
    def checks(self) -> SqliteCheckRepository:
        return SqliteCheckRepository(self.session)

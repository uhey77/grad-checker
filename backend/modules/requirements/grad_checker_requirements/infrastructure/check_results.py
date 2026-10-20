"""判定履歴の保存と本人限定の取得。トランザクションはUnit of Workが開始する。"""

from datetime import UTC
from uuid import UUID

from pydantic import TypeAdapter, ValidationError
from sqlalchemy import Engine, func
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session, col, select

from modules.shared.grad_checker_shared.infrastructure.unit_of_work import SqlUnitOfWork

from ..application.dto.check_results import (
    CheckCurriculum,
    CheckInput,
    CheckPage,
    CheckSummary,
    SavedCheck,
)
from ..application.dto.evaluation import CreditSummary, Judgment
from ..application.dto.student_evaluation import StudentEvaluation
from ..application.errors.evaluation import EvaluationError
from ..application.ports.check_results import CheckRepository, CheckUnitOfWork
from .check_models import CheckResultRecord
from .evaluation import SqliteEvaluationRepository


def unavailable(_error: SQLAlchemyError) -> EvaluationError:
    return EvaluationError("check_unavailable", "判定履歴を保存・取得できません。")


# 一覧の要約に使う結果JSONの項目。複数パスのjson_extractは配列で返る。
SUMMARY_FIELDS = TypeAdapter(tuple[Judgment, CheckCurriculum, CreditSummary])


def invalid_record(error: ValidationError) -> EvaluationError:
    return EvaluationError("invalid_check_result", "保存済みの判定履歴が不正です。")


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
            raise invalid_record(error) from error

    def count(self, student_id: str) -> int:
        return self.db.exec(
            select(func.count()).where(col(CheckResultRecord.student_id) == student_id)
        ).one()

    def list_page(self, student_id: str, page: CheckPage) -> list[CheckSummary]:
        # 一覧では結果JSONのうち要約に使う項目だけを読み出す。
        rows = self.db.exec(
            select(
                CheckResultRecord.id,
                CheckResultRecord.created_at,
                CheckResultRecord.data_revision,
                func.json_extract(
                    CheckResultRecord.result_json, "$.result", "$.curriculum", "$.total"
                ),
            )
            .where(col(CheckResultRecord.student_id) == student_id)
            .order_by(
                col(CheckResultRecord.created_at).desc(),
                col(CheckResultRecord.id).asc(),
            )
            .limit(page.limit)
            .offset(page.offset)
        ).all()
        try:
            summaries = []
            for check_id, created, revision, fields in rows:
                result, curriculum, total = SUMMARY_FIELDS.validate_json(fields)
                summaries.append(
                    CheckSummary(
                        id=UUID(check_id),
                        created_at=created.replace(tzinfo=UTC),
                        data_revision=revision,
                        result=result,
                        curriculum=curriculum,
                        total=total,
                    )
                )
            return summaries
        except ValidationError as error:
            raise invalid_record(error) from error


class SqliteCheckUnitOfWork(SqlUnitOfWork, CheckUnitOfWork):
    def __init__(self, engine: Engine) -> None:
        super().__init__(engine, unavailable)

    @property
    def evaluation(self) -> SqliteEvaluationRepository:
        return SqliteEvaluationRepository(self.session)

    @property
    def checks(self) -> SqliteCheckRepository:
        return SqliteCheckRepository(self.session)

"""本人の判定履歴テーブル。保存後の更新はDBのトリガーでも拒否する。"""

from datetime import datetime

from sqlalchemy import CheckConstraint, Index
from sqlmodel import Field, SQLModel

# 外部キーの参照先を同じメタデータへ登録する。
from modules.accounts.grad_checker_accounts.infrastructure.models import (  # noqa: F401
    Student,
)
from modules.subjects.grad_checker_subjects.infrastructure.subject_models import (
    integer_check,
    text_check,
)


class CheckResultRecord(SQLModel, table=True):
    __tablename__ = "check_results"
    __table_args__ = (
        # 本人の履歴を作成日時の降順・同時刻はID順で読む。
        Index("ix_check_results_student_created", "student_id", "created_at", "id"),
        CheckConstraint("json_valid(input_json)"),
        CheckConstraint("json_valid(result_json)"),
        text_check("curriculum_code"),
        integer_check("curriculum_revision", minimum=1),
        integer_check("data_revision"),
    )
    id: str = Field(primary_key=True)
    student_id: str = Field(foreign_key="students.id", ondelete="RESTRICT")
    input_json: str
    result_json: str
    curriculum_code: str
    curriculum_revision: int
    data_revision: int
    created_at: datetime


CHECK_TABLES = [SQLModel.metadata.tables[CheckResultRecord.__tablename__]]

IMMUTABLE_TRIGGER = (
    "CREATE TRIGGER IF NOT EXISTS check_results_immutable "
    "BEFORE UPDATE ON check_results "
    "BEGIN SELECT RAISE(ABORT, 'check_results are immutable'); END"
)

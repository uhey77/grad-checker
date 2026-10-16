"""成績スキーマの生成。学生・科目テーブルの生成後に呼び出す。"""

from sqlalchemy import Engine
from sqlmodel import SQLModel

from modules.grades.grad_checker_grades.infrastructure.models import GRADE_TABLES


def create_grade_schema(engine: Engine) -> None:
    SQLModel.metadata.create_all(engine, tables=GRADE_TABLES)

"""アカウントスキーマの生成と、空の旧メール認証DBの移行。"""

from sqlalchemy import Engine, inspect, text
from sqlmodel import SQLModel

from modules.accounts.grad_checker_accounts.infrastructure.models import ACCOUNT_TABLES


def create_account_schema(engine: Engine) -> None:
    with engine.begin() as connection:
        inspector = inspect(connection)
        if inspector.has_table("students"):
            columns = {column["name"] for column in inspector.get_columns("students")}
            if "email_verified_at" in columns:
                count = connection.execute(
                    text("SELECT COUNT(*) FROM students")
                ).scalar_one()
                if count:
                    raise RuntimeError(
                        "旧メール認証のアカウントが存在します。DBをバックアップし、"
                        "ユーザー名の移行方針を確認してください。自動変更は行いません。"
                    )
                connection.execute(
                    text(
                        "ALTER TABLE students RENAME COLUMN "
                        "email_verified_at TO created_at"
                    )
                )
        if inspector.has_table("student_credentials"):
            columns = {
                column["name"]
                for column in inspector.get_columns("student_credentials")
            }
            if "recovery_code_hash" not in columns:
                connection.execute(
                    text(
                        "ALTER TABLE student_credentials ADD COLUMN "
                        "recovery_code_hash TEXT"
                    )
                )
        SQLModel.metadata.create_all(connection, tables=ACCOUNT_TABLES)

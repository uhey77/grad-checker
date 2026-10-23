"""本人情報・認証情報・復旧コード・試行回数の永続化。"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import CheckConstraint
from sqlmodel import Field, SQLModel

from shared.infrastructure.persistence.types import UtcDateTime


class Student(SQLModel, table=True):
    __tablename__ = "students"
    __table_args__ = (CheckConstraint("data_revision >= 0"),)
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    login_name: str = Field(unique=True)
    program_id: str | None = Field(default=None, foreign_key="academic_programs.id")
    curriculum_id: str | None = Field(default=None, foreign_key="curricula.id")
    admission_year: int | None = None
    name: str | None = None
    data_revision: int = 0
    created_at: datetime = Field(sa_type=UtcDateTime)


class Credential(SQLModel, table=True):
    __tablename__ = "student_credentials"
    student_id: str = Field(primary_key=True, foreign_key="students.id")
    password_hash: str
    recovery_code_hash: str | None = None
    is_active: bool = True
    password_updated_at: datetime = Field(sa_type=UtcDateTime)


class AuthSession(SQLModel, table=True):
    __tablename__ = "auth_sessions"
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    student_id: str = Field(foreign_key="students.id")
    token_hash: str = Field(unique=True)
    csrf_token_hash: str
    created_at: datetime = Field(sa_type=UtcDateTime)
    last_seen_at: datetime = Field(sa_type=UtcDateTime)
    expires_at: datetime = Field(sa_type=UtcDateTime)
    revoked_at: datetime | None = Field(default=None, sa_type=UtcDateTime)


class AuthAttempt(SQLModel, table=True):
    __tablename__ = "auth_attempts"
    key: str = Field(primary_key=True)
    window_started_at: datetime = Field(sa_type=UtcDateTime)
    count: int


ACCOUNT_TABLES = [
    SQLModel.metadata.tables[model.__tablename__]
    for model in (Student, Credential, AuthSession, AuthAttempt)
]

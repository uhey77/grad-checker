"""認証の保存処理。更新・確認リンクの消費はSQLiteトランザクションで行う。"""

from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, update
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlmodel import Session, col, select

from modules.accounts.grad_checker_accounts.application.auth import (
    Account,
    AuthError,
    StoredSession,
    digest,
)
from modules.accounts.grad_checker_accounts.infrastructure.models import (
    AuthAttempt,
    AuthSession,
    Credential,
    Student,
    Verification,
)


def utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


class SqliteAccountRepository:
    def __init__(self, session: Session) -> None:
        self.db = session

    @contextmanager
    def transaction(self) -> Generator[None]:
        try:
            yield
            self.db.commit()
        except AuthError:
            self.db.rollback()
            raise
        except IntegrityError as error:
            self.db.rollback()
            raise AuthError("registration_conflict") from error
        except SQLAlchemyError as error:
            self.db.rollback()
            raise AuthError("auth_unavailable") from error

    def take_attempt(self, key: str, now: datetime, window: int, limit: int) -> None:
        with self.transaction():
            # UPSERTを先に行い、並行要求も同じ書込みロックで直列化する。
            self.db.connection().execute(
                insert(AuthAttempt)
                .values(
                    key=key,
                    window_started_at=now,
                    count=0,
                )
                .on_conflict_do_nothing(index_elements=["key"])
            )
            attempt = self.db.get(AuthAttempt, key)
            assert attempt is not None
            if utc(attempt.window_started_at) + timedelta(minutes=window) <= now:
                attempt.window_started_at = now
                attempt.count = 0
            if attempt.count >= limit:
                raise AuthError("rate_limited")
            attempt.count += 1
            self.db.add(attempt)
            # 期限切れの別キーを削除し、試行履歴が際限なく増えないようにする。
            self.db.connection().execute(
                delete(AuthAttempt).where(
                    col(AuthAttempt.window_started_at)
                    < now - timedelta(minutes=window),
                    col(AuthAttempt.key) != key,
                )
            )

    def account_exists(self, email: str) -> bool:
        with self.transaction():
            return (
                self.db.exec(
                    select(Student).where(col(Student.login_name) == email)
                ).first()
                is not None
            )

    def save_verification(self, email: str, token_hash: str, expires: datetime) -> None:
        with self.transaction():
            self.db.add(
                Verification(token_hash=token_hash, email=email, expires_at=expires)
            )

    def complete_registration(
        self, token_hash: str, password_hash: str, now: datetime
    ) -> Account:
        with self.transaction():
            # 条件付きUPDATEによって同じリンクを同時に消費できないようにする。
            result = self.db.connection().execute(
                update(Verification)
                .where(
                    col(Verification.token_hash) == token_hash,
                    col(Verification.used_at).is_(None),
                    col(Verification.expires_at) > now,
                )
                .values(used_at=now)
                .returning(col(Verification.email))
            )
            email = result.scalar_one_or_none()
            if email is None:
                raise AuthError("invalid_verification")
            if self.db.exec(
                select(Student).where(col(Student.login_name) == email)
            ).first():
                raise AuthError("invalid_verification")
            student = Student(login_name=email, email_verified_at=now)
            self.db.add(student)
            self.db.flush()
            self.db.add(
                Credential(
                    student_id=student.id,
                    password_hash=password_hash,
                    password_updated_at=now,
                )
            )
            self.db.connection().execute(
                update(Verification)
                .where(
                    col(Verification.email) == email,
                    col(Verification.used_at).is_(None),
                )
                .values(used_at=now)
            )
            return Account(id=student.id, login_name=student.login_name)

    def credentials(self, email: str) -> tuple[Account, str] | None:
        with self.transaction():
            row = self.db.exec(
                select(Student, Credential)
                .join(Credential)
                .where(
                    col(Student.login_name) == email,
                    col(Credential.is_active),
                )
            ).first()
            if row is None:
                return None
            student, credential = row
            return Account(
                id=student.id, login_name=student.login_name
            ), credential.password_hash

    def save_session(
        self, account: Account, token_hash: str, csrf: str, expires: datetime
    ) -> None:
        now = datetime.now(UTC)
        with self.transaction():
            self.db.add(
                AuthSession(
                    student_id=account.id,
                    token_hash=token_hash,
                    csrf_token_hash=digest(csrf),
                    created_at=now,
                    last_seen_at=now,
                    expires_at=expires,
                )
            )

    def session(self, token_hash: str, now: datetime) -> StoredSession | None:
        with self.transaction():
            row = self.db.exec(
                select(AuthSession, Student)
                .join(Student)
                .join(Credential)
                .where(
                    col(AuthSession.token_hash) == token_hash,
                    col(AuthSession.revoked_at).is_(None),
                    col(AuthSession.expires_at) > now,
                    col(Credential.is_active),
                )
            ).first()
            if row is None:
                return None
            record, student = row
            record.last_seen_at = now
            self.db.add(record)
            # CSRF原値は保存せず、ユースケースでセッション原値から再構成する。
            return StoredSession(
                account=Account(id=student.id, login_name=student.login_name),
                csrf_token_hash=record.csrf_token_hash,
                expires_at=utc(record.expires_at),
            )

    def revoke_session(self, token_hash: str, now: datetime) -> None:
        with self.transaction():
            self.db.connection().execute(
                update(AuthSession)
                .where(col(AuthSession.token_hash) == token_hash)
                .values(revoked_at=now)
            )

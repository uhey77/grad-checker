"""認証の保存処理。トランザクションはUnit of Workで認証ユースケースが決める。"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, update
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlmodel import Session, col, select

from modules.accounts.application.dto.auth import Account, StoredSession
from modules.accounts.application.errors.auth import AuthError
from modules.accounts.application.ports.auth import AccountRepository
from modules.accounts.application.services.auth import digest
from modules.accounts.infrastructure.persistence.models.models import (
    AuthAttempt,
    AuthSession,
    Credential,
    Student,
)


def auth_failure(error: SQLAlchemyError) -> AuthError:
    if isinstance(error, IntegrityError):
        return AuthError("registration_conflict")
    return AuthError("auth_unavailable")


def utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


class SqliteAccountRepository(AccountRepository):
    def __init__(self, session: Session) -> None:
        self.db = session

    def take_attempt(self, key: str, now: datetime, window: int, limit: int) -> None:
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
                col(AuthAttempt.window_started_at) < now - timedelta(minutes=window),
                col(AuthAttempt.key) != key,
            )
        )

    def register(
        self, username: str, password_hash: str, recovery_hash: str, now: datetime
    ) -> Account:
        student = Student(login_name=username, created_at=now)
        self.db.add(student)
        self.db.flush()
        self.db.add(
            Credential(
                student_id=student.id,
                password_hash=password_hash,
                recovery_code_hash=recovery_hash,
                password_updated_at=now,
            )
        )
        return Account(id=student.id, login_name=student.login_name)

    def reset_credentials(
        self,
        username: str,
        recovery_hash: str,
        password_hash: str,
        new_recovery_hash: str,
        now: datetime,
    ) -> str | None:
        # 条件付きUPDATEで、同じ復旧コードの並行使用を一度だけ成功させる。
        return (
            self.db.connection()
            .execute(
                update(Credential)
                .where(
                    col(Credential.student_id).in_(
                        select(Student.id).where(col(Student.login_name) == username)
                    ),
                    col(Credential.recovery_code_hash) == recovery_hash,
                    col(Credential.is_active),
                )
                .values(
                    password_hash=password_hash,
                    recovery_code_hash=new_recovery_hash,
                    password_updated_at=now,
                )
                .returning(col(Credential.student_id))
            )
            .scalar_one_or_none()
        )

    def revoke_sessions(self, student_id: str, now: datetime) -> None:
        self.db.connection().execute(
            update(AuthSession)
            .where(
                col(AuthSession.student_id) == student_id,
                col(AuthSession.revoked_at).is_(None),
            )
            .values(revoked_at=now)
        )

    def credentials(self, username: str) -> tuple[Account, str] | None:
        row = self.db.exec(
            select(Student, Credential)
            .join(Credential)
            .where(
                col(Student.login_name) == username,
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
        self,
        account: Account,
        token_hash: str,
        csrf: str,
        expires: datetime,
        password_hash: str,
    ) -> bool:
        now = datetime.now(UTC)
        # 復旧と直列化し、古いパスワードで検証済みの要求からセッションを作らない。
        current = (
            self.db.connection()
            .execute(
                update(Credential)
                .where(
                    col(Credential.student_id) == account.id,
                    col(Credential.password_hash) == password_hash,
                    col(Credential.is_active),
                )
                .values(password_hash=password_hash)
                .returning(col(Credential.student_id))
            )
            .scalar_one_or_none()
        )
        if current is None:
            return False
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
        return True

    def session(self, token_hash: str, now: datetime) -> StoredSession | None:
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
        self.db.connection().execute(
            update(AuthSession)
            .where(col(AuthSession.token_hash) == token_hash)
            .values(revoked_at=now)
        )

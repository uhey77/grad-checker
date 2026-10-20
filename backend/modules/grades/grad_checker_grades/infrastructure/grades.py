"""本人成績の取得と全集合の置換。トランザクションはUnit of Workが開始する。"""

from datetime import UTC, datetime

from sqlalchemy import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session, col, select

from modules.accounts.grad_checker_accounts.infrastructure.models import Student
from modules.shared.grad_checker_shared.infrastructure.unit_of_work import SqlUnitOfWork
from modules.subjects.grad_checker_subjects.infrastructure.subject_models import Subject

from ..application.dto.grades import GradeAttempt, GradeSet, StudentGrades
from ..application.errors.grades import GradeError
from ..application.ports.grades import GradeRepository, GradeUnitOfWork
from .models import GradeAttemptRecord

VALUE_FIELDS = ("result_status", "grade_code", "academic_year", "term_code")


def unavailable(_error: SQLAlchemyError) -> GradeError:
    return GradeError("grades_unavailable")


def attempt_data(record: GradeAttemptRecord) -> GradeAttempt:
    return GradeAttempt.model_validate(
        {
            "course_id": record.course_id,
            "attempt_no": record.attempt_no,
            **{field: getattr(record, field) for field in VALUE_FIELDS},
        }
    )


def ordered(grades: list[GradeAttempt]) -> list[GradeAttempt]:
    return sorted(grades, key=lambda grade: (grade.course_id, grade.attempt_no))


class SqliteGradeRepository(GradeRepository):
    def __init__(self, session: Session) -> None:
        self.db = session

    def _records(self, student_id: str) -> list[GradeAttemptRecord]:
        return list(
            self.db.exec(
                select(GradeAttemptRecord).where(
                    col(GradeAttemptRecord.student_id) == student_id
                )
            ).all()
        )

    def get_grades(self, student_id: str) -> StudentGrades:
        student = self.db.get(Student, student_id, populate_existing=True)
        if student is None:
            raise GradeError("student_not_found")
        return StudentGrades(
            grades=ordered([attempt_data(r) for r in self._records(student_id)]),
            data_revision=student.data_revision,
        )

    def replace_grades(self, student_id: str, grade_set: GradeSet) -> StudentGrades:
        student = self.db.get(Student, student_id, populate_existing=True)
        if student is None:
            raise GradeError("student_not_found")
        if student.data_revision != grade_set.expected_revision:
            raise GradeError("revision_conflict")
        course_ids = {grade.course_id for grade in grade_set.grades}
        if course_ids:
            known = self.db.exec(
                select(Subject.id).where(col(Subject.id).in_(course_ids))
            ).all()
            if set(known) != course_ids:
                raise GradeError("unknown_course")
        now = datetime.now(UTC)
        existing = {
            (record.course_id, record.attempt_no): record
            for record in self._records(student_id)
        }
        wanted = {
            (grade.course_id, grade.attempt_no): grade for grade in grade_set.grades
        }
        for key, record in existing.items():
            if key not in wanted:
                self.db.delete(record)
        for key, grade in wanted.items():
            values = {field: getattr(grade, field) for field in VALUE_FIELDS}
            record = existing.get(key)
            if record is None:
                record = GradeAttemptRecord(
                    student_id=student_id,
                    course_id=grade.course_id,
                    attempt_no=grade.attempt_no,
                    updated_at=now,
                    **values,
                )
            elif any(getattr(record, k) != v for k, v in values.items()):
                # 変更した回次だけ更新日時を進め、変更のない回次は保持する。
                for field, value in values.items():
                    setattr(record, field, value)
                record.updated_at = now
            else:
                continue
            self.db.add(record)
        student.data_revision += 1
        self.db.add(student)
        self.db.flush()
        return StudentGrades(
            grades=ordered(list(grade_set.grades)),
            data_revision=student.data_revision,
        )


class SqliteGradeUnitOfWork(SqlUnitOfWork, GradeUnitOfWork):
    def __init__(self, engine: Engine) -> None:
        super().__init__(engine, unavailable)

    @property
    def grades(self) -> SqliteGradeRepository:
        return SqliteGradeRepository(self.session)

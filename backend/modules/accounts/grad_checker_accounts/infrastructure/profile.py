"""保存済み本人情報と課程マスタを扱う。成績データは変更しない。"""

from pydantic import TypeAdapter
from sqlalchemy import Engine, update
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session, col, select

from modules.accounts.grad_checker_accounts.application.errors.profile import (
    ProfileError,
)
from modules.accounts.grad_checker_accounts.application.profile import (
    Profile,
    ProfileRepository,
    ProfileUnitOfWork,
    ProgramOption,
    ProgramSelection,
    VerificationStatus,
)
from modules.accounts.grad_checker_accounts.infrastructure.models import Student
from modules.requirements.grad_checker_requirements.application import (
    completion_policy as completion_contracts,
)
from modules.requirements.grad_checker_requirements.infrastructure.models import (
    CompletionPolicy,
)
from modules.shared.grad_checker_shared.infrastructure.unit_of_work import (
    SqlUnitOfWork,
)
from modules.subjects.grad_checker_subjects.infrastructure.subject_models import (
    AcademicProgram,
    Curriculum,
)


def unavailable(_error: SQLAlchemyError) -> ProfileError:
    return ProfileError("profile_unavailable")


class SqliteProfileRepository(ProfileRepository):
    def __init__(self, session: Session) -> None:
        self.db = session

    def list_programs(self) -> list[ProgramOption]:
        rows = self.db.exec(
            select(AcademicProgram, Curriculum)
            .join(Curriculum, col(Curriculum.program_id) == col(AcademicProgram.id))
            .order_by(AcademicProgram.code, Curriculum.code)
        ).all()
        policies = {
            row.curriculum_id: completion_contracts.CompletionPolicyData.model_validate(
                row.model_dump()
            )
            for row in self.db.exec(select(CompletionPolicy)).all()
        }
        return [
            ProgramOption(
                completion_policy=policies.get(curriculum.id),
                program_id=program.id,
                curriculum_id=curriculum.id,
                faculty_name=program.faculty_name,
                department_name=program.department_name,
                specialization_name=program.specialization_name,
                course_name=program.course_name,
                curriculum_name=curriculum.name,
                revision=curriculum.revision,
                verification_status=TypeAdapter(VerificationStatus).validate_python(
                    curriculum.verification_status
                ),
                admission_year_from=curriculum.admission_year_from,
                admission_year_to=curriculum.admission_year_to,
                source_document=curriculum.source_document,
                source_pages=curriculum.source_pages,
            )
            for program, curriculum in rows
        ]

    def get_profile(self, student_id: str) -> Profile:
        student = self.db.get(Student, student_id)
        if student is None:
            raise ProfileError("profile_not_found")
        return Profile(
            student_id=student.id,
            login_name=student.login_name,
            program_id=student.program_id,
            curriculum_id=student.curriculum_id,
            data_revision=student.data_revision,
        )

    def save_program(self, student_id: str, selection: ProgramSelection) -> Profile:
        curriculum = self.db.get(Curriculum, selection.curriculum_id)
        if curriculum is None or curriculum.program_id != selection.program_id:
            raise ProfileError("invalid_program")
        row = (
            self.db.connection()
            .execute(
                update(Student)
                .where(
                    col(Student.id) == student_id,
                    col(Student.data_revision) == selection.expected_revision,
                )
                .values(
                    program_id=selection.program_id,
                    curriculum_id=selection.curriculum_id,
                    data_revision=col(Student.data_revision) + 1,
                )
                .returning(
                    col(Student.id).label("student_id"),
                    col(Student.login_name),
                    col(Student.program_id),
                    col(Student.curriculum_id),
                    col(Student.data_revision),
                )
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            raise ProfileError("revision_conflict")
        return Profile.model_validate(dict(row))


class SqliteProfileUnitOfWork(SqlUnitOfWork, ProfileUnitOfWork):
    def __init__(self, engine: Engine) -> None:
        super().__init__(engine, unavailable)

    @property
    def profiles(self) -> SqliteProfileRepository:
        return SqliteProfileRepository(self.session)

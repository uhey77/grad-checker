"""課程と科目データの取得。読取スナップショットはUnit of Workが開始する。"""

from collections import defaultdict
from uuid import UUID

from sqlalchemy import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session, col, select

from modules.shared.grad_checker_shared.infrastructure.unit_of_work import (
    SqlUnitOfWork,
)
from modules.subjects.grad_checker_subjects.application.errors.subject_list import (
    SubjectListIntegrityError,
    SubjectListNotFoundError,
    SubjectListUnavailableError,
)
from modules.subjects.grad_checker_subjects.application.subject_list import (
    SubjectList,
    SubjectListClassification,
    SubjectListItem,
    SubjectListOffering,
    SubjectListProgram,
    SubjectListRepository,
    SubjectListUnitOfWork,
)
from modules.subjects.grad_checker_subjects.infrastructure.classification_path import (
    classification_path,
)
from modules.subjects.grad_checker_subjects.infrastructure.subject_models import (
    AcademicProgram,
    Classification,
    Curriculum,
    CurriculumSubject,
    Subject,
    SubjectOffering,
)


def unavailable(_error: SQLAlchemyError) -> SubjectListUnavailableError:
    return SubjectListUnavailableError()


def program_data(
    curriculum: Curriculum, program: AcademicProgram
) -> SubjectListProgram:
    return SubjectListProgram(
        curriculum_id=curriculum.id,
        name=curriculum.name,
        faculty_name=program.faculty_name,
        specialization_name=program.specialization_name,
        course_name=program.course_name,
        verification_status=curriculum.verification_status,
        admission_year_from=curriculum.admission_year_from,
        admission_year_to=curriculum.admission_year_to,
        source_document=curriculum.source_document,
        source_pages=curriculum.source_pages,
    )


class SqliteSubjectListRepository(SubjectListRepository):
    def __init__(self, session: Session):
        self.session = session

    def list_programs(self) -> list[SubjectListProgram]:
        rows = self.session.exec(
            select(Curriculum, AcademicProgram)
            .join(
                AcademicProgram,
                col(Curriculum.program_id) == col(AcademicProgram.id),
            )
            .order_by(AcademicProgram.code, Curriculum.code)
        ).all()
        return [program_data(curriculum, program) for curriculum, program in rows]

    def get_subject_list(self, curriculum_id: UUID) -> SubjectList:
        row = self.session.exec(
            select(Curriculum, AcademicProgram)
            .join(
                AcademicProgram,
                col(Curriculum.program_id) == col(AcademicProgram.id),
            )
            .where(Curriculum.id == str(curriculum_id))
        ).first()
        if row is None:
            raise SubjectListNotFoundError
        curriculum, program = row
        classifications = {
            item.id: item
            for item in self.session.exec(
                select(Classification).where(
                    Classification.curriculum_id == curriculum.id
                )
            ).all()
        }
        rows = self.session.exec(
            select(CurriculumSubject, Subject, AcademicProgram)
            .join(Subject, col(CurriculumSubject.course_id) == col(Subject.id))
            .join(
                AcademicProgram,
                col(Subject.offering_program_id) == col(AcademicProgram.id),
            )
            .where(CurriculumSubject.curriculum_id == curriculum.id)
            .order_by(col(CurriculumSubject.display_order), col(Subject.code))
        ).all()
        offerings = defaultdict(list)
        if rows:
            course_ids = [course.id for _, course, _ in rows]
            for offering in self.session.exec(
                select(SubjectOffering)
                .where(col(SubjectOffering.course_id).in_(course_ids))
                .order_by(col(SubjectOffering.semester_order), col(SubjectOffering.id))
            ).all():
                offerings[offering.course_id].append(
                    SubjectListOffering(
                        term_code=offering.term_code,
                        semester_order=offering.semester_order,
                        academic_year=offering.academic_year,
                        source_note=offering.source_note,
                    )
                )
        courses = []
        for association, course, offering_program in rows:
            path = classification_path(classifications, association.classification_id)
            if path is None:
                raise SubjectListIntegrityError
            courses.append(
                SubjectListItem(
                    id=course.id,
                    code=course.code,
                    name=course.name,
                    credits=course.credits,
                    faculty_name=offering_program.faculty_name,
                    department_name=offering_program.department_name,
                    specialization_name=offering_program.specialization_name,
                    teaching_type_label=course.teaching_type_label,
                    course_type=association.course_type,
                    classification_path=[
                        SubjectListClassification(id=item.id, name=item.name)
                        for item in path
                    ],
                    offerings=offerings[course.id],
                )
            )
        return SubjectList(program=program_data(curriculum, program), courses=courses)


class SqliteSubjectListUnitOfWork(SqlUnitOfWork, SubjectListUnitOfWork):
    def __init__(self, engine: Engine) -> None:
        super().__init__(engine, unavailable)

    @property
    def subject_list(self) -> SqliteSubjectListRepository:
        return SqliteSubjectListRepository(self.session)

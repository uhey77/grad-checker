"""同じ読取スナップショットから、本人課程の分類と全既知科目を取得する。"""

from collections import defaultdict

from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session, col, select

from modules.shared.grad_checker_shared.infrastructure.transactions import (
    read_snapshot,
)
from modules.subjects.grad_checker_subjects.application.course_catalog import (
    CatalogCategory,
    CatalogClassification,
    CatalogCourse,
    CatalogCurriculum,
    CatalogOffering,
    CatalogPlacement,
    CourseCatalog,
)
from modules.subjects.grad_checker_subjects.application.errors.course_catalog import (
    CourseCatalogError,
)
from modules.subjects.grad_checker_subjects.domain.subject_type import SubjectType
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

from ..domain.curriculum_verification_status import (
    VerificationStatus,
)


def unavailable(_error: SQLAlchemyError) -> CourseCatalogError:
    return CourseCatalogError("catalog_unavailable")


class SqliteCourseCatalogRepository:
    def __init__(self, session: Session) -> None:
        self.db = session

    def get_catalog(self, curriculum_id: str) -> CourseCatalog:
        with read_snapshot(self.db, unavailable):
            curriculum = self.db.get(Curriculum, curriculum_id)
            if curriculum is None:
                raise CourseCatalogError("curriculum_not_found")
            classifications = {
                item.id: item
                for item in self.db.exec(
                    select(Classification)
                    .where(Classification.curriculum_id == curriculum.id)
                    .order_by(
                        col(Classification.level),
                        col(Classification.display_order),
                        col(Classification.code),
                    )
                ).all()
            }
            placements = {
                item.course_id: item
                for item in self.db.exec(
                    select(CurriculumSubject).where(
                        CurriculumSubject.curriculum_id == curriculum.id
                    )
                ).all()
            }
            offerings: defaultdict[str, list[CatalogOffering]] = defaultdict(list)
            for offering in self.db.exec(
                select(SubjectOffering).order_by(
                    col(SubjectOffering.semester_order), col(SubjectOffering.id)
                )
            ).all():
                offerings[offering.course_id].append(
                    CatalogOffering(
                        term_code=offering.term_code,
                        semester_order=offering.semester_order,
                        academic_year=offering.academic_year,
                        source_note=offering.source_note,
                    )
                )
            courses = []
            for course, program in self.db.exec(
                select(Subject, AcademicProgram).join(
                    AcademicProgram,
                    col(Subject.offering_program_id) == col(AcademicProgram.id),
                )
            ).all():
                association = placements.get(course.id)
                placement = None
                if association is not None:
                    path = classification_path(
                        classifications, association.classification_id
                    )
                    if path is None:
                        raise CourseCatalogError("classification_inconsistent")
                    placement = CatalogPlacement(
                        classification_path=[
                            CatalogClassification(id=item.id, name=item.name)
                            for item in path
                        ],
                        course_type=SubjectType(association.course_type),
                    )
                courses.append(
                    (
                        (0, association.display_order, course.code)
                        if association
                        else (1, 0, course.code),
                        CatalogCourse(
                            course_id=course.id,
                            code=course.code,
                            name=course.name,
                            credits=course.credits,
                            offering_faculty_name=program.faculty_name,
                            offering_department_name=program.department_name,
                            offering_specialization_name=program.specialization_name,
                            teaching_type=course.teaching_type,
                            teaching_type_label=course.teaching_type_label,
                            offerings=offerings[course.id],
                            placement=placement,
                        ),
                    )
                )
            return CourseCatalog(
                curriculum=CatalogCurriculum(
                    curriculum_id=curriculum.id,
                    name=curriculum.name,
                    verification_status=VerificationStatus(
                        curriculum.verification_status
                    ),
                    admission_year_from=curriculum.admission_year_from,
                    admission_year_to=curriculum.admission_year_to,
                    source_document=curriculum.source_document,
                    source_pages=curriculum.source_pages,
                ),
                categories=[
                    CatalogCategory(
                        id=item.id,
                        code=item.code,
                        name=item.name,
                        parent_id=item.parent_id,
                        level=item.level,
                        display_order=item.display_order,
                    )
                    for item in classifications.values()
                ],
                # 本人課程の科目表を便覧順に先に並べ、課程外の既知科目を続ける。
                courses=[course for _, course in sorted(courses, key=lambda c: c[0])],
            )

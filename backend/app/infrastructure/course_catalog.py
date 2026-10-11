"""同じ読取スナップショットから課程と科目データを取得する。"""

from collections import defaultdict
from uuid import UUID

from sqlmodel import Session, select

from app.application.errors.course_catalog import CatalogNotFound
from app.application.course_catalog import (
    CatalogRepository,
    CatalogClassification,
    CatalogCourse,
    CatalogOffering,
    CatalogProgram,
    CourseCatalog,
)
from app.infrastructure.course_catalog_models import (
    AcademicProgram,
    Classification,
    Course,
    CourseOffering,
    Curriculum,
    CurriculumCourse,
)


def program_data(curriculum: Curriculum, program: AcademicProgram) -> CatalogProgram:
    return CatalogProgram(
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


class SqliteCatalogRepository(CatalogRepository):
    def __init__(self, session: Session):
        self.session = session

    def list_programs(self) -> list[CatalogProgram]:
        rows = self.session.exec(
            select(Curriculum, AcademicProgram)
            .join(AcademicProgram, Curriculum.program_id == AcademicProgram.id)
            .order_by(AcademicProgram.code, Curriculum.code)
        ).all()
        return [program_data(curriculum, program) for curriculum, program in rows]

    def get_catalog(self, curriculum_id: UUID) -> CourseCatalog:
        # SQLiteの従来トランザクションモードでも複数SELECTの一貫性を保証する。
        self.session.connection().exec_driver_sql("BEGIN")
        row = self.session.exec(
            select(Curriculum, AcademicProgram)
            .join(AcademicProgram, Curriculum.program_id == AcademicProgram.id)
            .where(Curriculum.id == str(curriculum_id))
        ).first()
        if row is None:
            raise CatalogNotFound("選択したカリキュラムが見つかりません。")
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
            select(CurriculumCourse, Course, AcademicProgram)
            .join(Course, CurriculumCourse.course_id == Course.id)
            .join(AcademicProgram, Course.offering_program_id == AcademicProgram.id)
            .where(CurriculumCourse.curriculum_id == curriculum.id)
            .order_by(CurriculumCourse.display_order, Course.code)
        ).all()
        offerings = defaultdict(list)
        if rows:
            course_ids = [course.id for _, course, _ in rows]
            for offering in self.session.exec(
                select(CourseOffering)
                .where(CourseOffering.course_id.in_(course_ids))
                .order_by(CourseOffering.semester_order, CourseOffering.id)
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
        for association, course, offering_program in rows:
            path = []
            visited = set()
            current = association.classification_id
            while current is not None:
                if current in visited or current not in classifications:
                    raise ValueError("科目分類の階層が不整合です。")
                visited.add(current)
                classification = classifications[current]
                path.append(
                    CatalogClassification(
                        id=classification.id, name=classification.name
                    )
                )
                current = classification.parent_id
            courses.append(
                CatalogCourse(
                    id=course.id,
                    code=course.code,
                    name=course.name,
                    credits=course.credits,
                    faculty_name=offering_program.faculty_name,
                    department_name=offering_program.department_name,
                    specialization_name=offering_program.specialization_name,
                    teaching_type_label=course.teaching_type_label,
                    course_type=association.course_type,
                    classification_path=list(reversed(path)),
                    offerings=offerings[course.id],
                )
            )
        return CourseCatalog(program=program_data(curriculum, program), courses=courses)

"""同じ読取スナップショットから課程と科目データを取得する。"""

from collections import defaultdict
from uuid import UUID

from sqlmodel import Session, col, select

from app.application.errors.subject_list import SubjectListNotFoundError
from app.application.subject_list import (
    SubjectList,
    SubjectListClassification,
    SubjectListItem,
    SubjectListOffering,
    SubjectListProgram,
    SubjectListRepository,
)
from app.infrastructure.subject_models import (
    AcademicProgram,
    Classification,
    Curriculum,
    CurriculumSubject,
    Subject,
    SubjectOffering,
)


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
                AcademicProgram, col(Curriculum.program_id) == col(AcademicProgram.id)
            )
            .order_by(AcademicProgram.code, Curriculum.code)
        ).all()
        return [program_data(curriculum, program) for curriculum, program in rows]

    def get_subject_list(self, curriculum_id: UUID) -> SubjectList:
        # SQLiteの従来トランザクションモードでも複数SELECTの一貫性を保証する。
        self.session.connection().exec_driver_sql("BEGIN")
        row = self.session.exec(
            select(Curriculum, AcademicProgram)
            .join(
                AcademicProgram, col(Curriculum.program_id) == col(AcademicProgram.id)
            )
            .where(Curriculum.id == str(curriculum_id))
        ).first()
        if row is None:
            raise SubjectListNotFoundError("選択したカリキュラムが見つかりません。")
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
            path = []
            visited = set()
            current = association.classification_id
            while current is not None:
                if current in visited or current not in classifications:
                    raise ValueError("科目分類の階層が不整合です。")
                visited.add(current)
                classification = classifications[current]
                path.append(
                    SubjectListClassification(
                        id=classification.id, name=classification.name
                    )
                )
                current = classification.parent_id
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
                    classification_path=list(reversed(path)),
                    offerings=offerings[course.id],
                )
            )
        return SubjectList(program=program_data(curriculum, program), courses=courses)

"""JSONシードの入力契約と、マスタ集合の整合性検証。"""

from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.master import CourseType, TeachingType, VerificationStatus

PositiveInteger = Annotated[int, Field(strict=True, gt=0)]
NonnegativeInteger = Annotated[int, Field(strict=True, ge=0)]
NonemptyText = Annotated[str, Field(strict=True, min_length=1)]


class SeedRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class AcademicProgramData(SeedRecord):
    id: UUID
    code: NonemptyText
    faculty_name: NonemptyText
    department_name: NonemptyText | None = None
    specialization_name: NonemptyText | None = None
    course_name: NonemptyText | None = None


class CurriculumData(SeedRecord):
    id: UUID
    program_id: UUID
    code: NonemptyText
    name: NonemptyText
    revision: PositiveInteger
    admission_year_from: PositiveInteger | None = None
    admission_year_to: PositiveInteger | None = None
    source_document: NonemptyText
    source_pages: NonemptyText
    verification_status: VerificationStatus


class ClassificationData(SeedRecord):
    id: UUID
    curriculum_id: UUID
    code: NonemptyText
    name: NonemptyText
    parent_id: UUID | None = None
    level: NonnegativeInteger
    display_order: NonnegativeInteger = 0


class CourseData(SeedRecord):
    id: UUID
    code: NonemptyText
    name: NonemptyText
    credits: PositiveInteger
    offering_program_id: UUID
    teaching_type: TeachingType
    teaching_type_label: NonemptyText


class CourseOfferingData(SeedRecord):
    course_id: UUID
    term_code: NonemptyText
    semester_order: PositiveInteger
    academic_year: PositiveInteger | None = None
    source_note: NonemptyText | None = None


class CurriculumCourseData(SeedRecord):
    curriculum_id: UUID
    course_id: UUID
    classification_id: UUID
    course_type: CourseType
    display_order: NonnegativeInteger = 0


class MasterSeed(SeedRecord):
    academic_programs: list[AcademicProgramData]
    curricula: list[CurriculumData]
    classifications: list[ClassificationData]
    courses: list[CourseData]
    course_offerings: list[CourseOfferingData]
    curriculum_courses: list[CurriculumCourseData]


class SeedError(ValueError):
    """利用者へ表示できるシードエラー。"""


def validate_master(seed: MasterSeed) -> list[ClassificationData]:
    """DB既存分と投入分を合わせて検証し、分類を親から順に返す。"""

    def unique(records: list, key, label: str) -> dict:
        result = {}
        for record in records:
            identity = key(record)
            if identity in result:
                raise SeedError(f"{label}が重複しています。")
            result[identity] = record
        return result

    programs = unique(seed.academic_programs, lambda x: x.id, "課程ID")
    curricula = unique(seed.curricula, lambda x: x.id, "カリキュラムID")
    classifications = unique(seed.classifications, lambda x: x.id, "分類ID")
    courses = unique(seed.courses, lambda x: x.id, "科目ID")
    for records, label in (
        (seed.academic_programs, "課程コード"),
        (seed.curricula, "カリキュラムコード"),
        (seed.courses, "科目コード"),
    ):
        unique(records, lambda x: x.code, label)
    unique(
        seed.classifications, lambda x: (x.curriculum_id, x.code), "課程内の分類コード"
    )
    unique(
        seed.course_offerings,
        lambda x: (x.course_id, x.term_code, x.semester_order, x.academic_year),
        "科目の開講期",
    )
    unique(
        seed.curriculum_courses, lambda x: (x.curriculum_id, x.course_id), "課程別科目"
    )

    for curriculum in curricula.values():
        if curriculum.program_id not in programs:
            raise SeedError("カリキュラムの所属課程が存在しません。")
        start, end = curriculum.admission_year_from, curriculum.admission_year_to
        if start is not None and end is not None and start > end:
            raise SeedError("適用入学年度の開始が終了を超えています。")
        if (
            curriculum.verification_status == VerificationStatus.VERIFIED
            and start is None
        ):
            raise SeedError("確認済みカリキュラムには適用入学年度の開始が必要です。")

    # 親を先に確定する。親が全て存在していても進まなければ循環。
    ordered: list[ClassificationData] = []
    remaining = dict(classifications)
    visited: set[UUID] = set()
    for classification in classifications.values():
        if classification.curriculum_id not in curricula:
            raise SeedError("分類のカリキュラムが存在しません。")
        parent = classifications.get(classification.parent_id)
        if classification.parent_id is not None:
            if parent is None or parent.curriculum_id != classification.curriculum_id:
                raise SeedError("親分類は同じカリキュラム内の分類を指定してください。")
        elif classification.level != 0:
            raise SeedError("最上位の分類のlevelは0にしてください。")
    while remaining:
        ready = [
            x
            for x in remaining.values()
            if x.parent_id is None or x.parent_id in visited
        ]
        if not ready:
            raise SeedError("分類の親子関係が循環しています。")
        for classification in ready:
            if classification.parent_id is not None:
                parent = classifications[classification.parent_id]
                if classification.level != parent.level + 1:
                    raise SeedError(
                        "子分類のlevelは親分類のlevelに1を加えた値にしてください。"
                    )
            ordered.append(classification)
            visited.add(classification.id)
            del remaining[classification.id]

    for course in courses.values():
        if course.offering_program_id not in programs:
            raise SeedError("科目の開講元課程が存在しません。")
    for offering in seed.course_offerings:
        if offering.course_id not in courses:
            raise SeedError("開講期の科目が存在しません。")
    for association in seed.curriculum_courses:
        classification = classifications.get(association.classification_id)
        if (
            association.curriculum_id not in curricula
            or association.course_id not in courses
        ):
            raise SeedError("課程別科目のカリキュラムまたは科目が存在しません。")
        if (
            classification is None
            or classification.curriculum_id != association.curriculum_id
        ):
            raise SeedError("課程別科目の分類は同じカリキュラム内で指定してください。")
    return ordered

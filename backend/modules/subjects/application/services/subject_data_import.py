"""科目マスタの投入順序と既存データを照合するキー。"""

from modules.subjects.application.dto.subject_data import (
    AcademicProgramData,
    ClassificationData,
    CurriculumData,
    CurriculumSubjectData,
    SubjectData,
    SubjectDataSeed,
    SubjectOfferingData,
)

TABLES = tuple(SubjectDataSeed.model_fields)


def record_key(
    record: AcademicProgramData
    | CurriculumData
    | ClassificationData
    | SubjectData
    | SubjectOfferingData
    | CurriculumSubjectData,
) -> tuple:
    if isinstance(record, SubjectOfferingData):
        return (
            record.course_id,
            record.term_code,
            record.semester_order,
            record.academic_year,
        )
    if isinstance(record, CurriculumSubjectData):
        return record.curriculum_id, record.course_id
    return (record.id,)

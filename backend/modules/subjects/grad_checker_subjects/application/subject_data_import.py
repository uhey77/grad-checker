"""検証済みの課程・科目データの原子的な追加投入。同じ内容の再投入は変更しない。"""

from abc import ABC, abstractmethod

from modules.shared.grad_checker_shared.application.unit_of_work import UnitOfWork
from modules.subjects.grad_checker_subjects.application.subject_data_validation import (
    AcademicProgramData,
    ClassificationData,
    CurriculumData,
    CurriculumSubjectData,
    SubjectData,
    SubjectDataSeed,
    SubjectOfferingData,
)

# 投入するテーブルの順。参照先のテーブルを先に置く。
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


class SubjectDataStore(ABC):
    @abstractmethod
    def load(self) -> SubjectDataSeed:
        """投入済みの課程・科目データをすべて読む。"""

    @abstractmethod
    def insert(self, additions: SubjectDataSeed) -> None:
        """テーブルの順、各テーブル内では並びの順に追加する。"""


class SubjectDataUnitOfWork(UnitOfWork):
    @property
    @abstractmethod
    def subject_data(self) -> SubjectDataStore: ...

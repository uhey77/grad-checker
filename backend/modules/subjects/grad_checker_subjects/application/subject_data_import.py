"""検証済みの課程・科目データの原子的な追加投入。同じ内容の再投入は変更しない。"""

from typing import Protocol

from modules.shared.grad_checker_shared.application.unit_of_work import UnitOfWork
from modules.subjects.grad_checker_subjects.application.errors.subject_data import (
    SeedError,
)
from modules.subjects.grad_checker_subjects.application.subject_data_validation import (
    AcademicProgramData,
    ClassificationData,
    CurriculumData,
    CurriculumSubjectData,
    SubjectData,
    SubjectDataSeed,
    SubjectOfferingData,
    validate_subject_data,
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


class SubjectDataStore(Protocol):
    def load(self) -> SubjectDataSeed:
        """投入済みの課程・科目データをすべて読む。"""
        ...

    def insert(self, additions: SubjectDataSeed) -> None:
        """テーブルの順、各テーブル内では並びの順に追加する。"""
        ...


class SubjectDataUnitOfWork(UnitOfWork, Protocol):
    @property
    def subject_data(self) -> SubjectDataStore: ...


def import_subject_data(
    uow: SubjectDataUnitOfWork, seed: SubjectDataSeed
) -> dict[str, int]:
    # 入力内の重複を先に拒否する。参照は既存DBを使えるため、ここでは検証しない。
    for name in TABLES:
        keys = [record_key(record) for record in getattr(seed, name)]
        if len(keys) != len(set(keys)):
            raise SeedError(f"{name}の投入データが重複しています。")
    # 検証から投入完了まで書込みロックを保持し、並行シードの競合を防ぐ。
    with uow.write():
        existing = uow.subject_data.load()
        combined: dict[str, list] = {}
        additions: dict[str, list] = {}
        for name in TABLES:
            current = getattr(existing, name)
            by_key = {record_key(record): record for record in current}
            new = []
            for record in getattr(seed, name):
                key = record_key(record)
                if key in by_key:
                    if by_key[key] != record:
                        raise SeedError(
                            f"{name}の既存データと内容が異なります。通常のシードでは更新できません。"
                        )
                else:
                    new.append(record)
            combined[name] = current + new
            additions[name] = new
        ordered = validate_subject_data(SubjectDataSeed(**combined))
        # 親分類も同じテーブルなので、親から順に追加する。
        new_classifications = {record.id for record in additions["classifications"]}
        additions["classifications"] = [
            record for record in ordered if record.id in new_classifications
        ]
        uow.subject_data.insert(SubjectDataSeed(**additions))
    return {name: len(additions[name]) for name in TABLES}

"""要件マスタの原子的な追加投入。既存行の変更・削除は拒否する。"""

from abc import ABC, abstractmethod

from modules.requirements.grad_checker_requirements.application.errors.seed import (
    RequirementSeedError,
)
from modules.requirements.grad_checker_requirements.application.seed import (
    CreditRuleCourseData,
    CreditRuleData,
    CreditRuleLimitData,
    RequirementData,
    RequirementScopeData,
    RequirementSeed,
)
from modules.requirements.grad_checker_requirements.application.validation import (
    unique,
    validate_requirements,
)
from modules.shared.grad_checker_shared.application.unit_of_work import UnitOfWork
from modules.subjects.grad_checker_subjects.application.subject_data_validation import (
    SubjectDataSeed,
)

from .completion_policy import CompletionPolicyData

# 投入するテーブルの順。参照先のテーブルを先に置く。
TABLES = tuple(RequirementSeed.model_fields)


def record_key(
    record: RequirementData
    | RequirementScopeData
    | CreditRuleData
    | CreditRuleCourseData
    | CreditRuleLimitData
    | CompletionPolicyData,
) -> tuple:
    if isinstance(record, CreditRuleCourseData):
        return record.rule_id, record.course_id
    return (record.id,)


class RequirementDataStore(ABC):
    @abstractmethod
    def subjects(self) -> SubjectDataSeed:
        """要件が参照する、投入済みの課程・科目データを読む。"""

    @abstractmethod
    def load(self) -> RequirementSeed:
        """投入済みの要件マスタをすべて読む。"""

    @abstractmethod
    def insert(self, additions: RequirementSeed) -> None:
        """テーブルの順、各テーブル内では並びの順に追加する。"""


class RequirementUnitOfWork(UnitOfWork):
    @property
    @abstractmethod
    def requirements(self) -> RequirementDataStore: ...


def import_requirements(
    uow: RequirementUnitOfWork, seed: RequirementSeed
) -> dict[str, int]:
    # model_copy等から渡されても、入口で型・値の検証を省略しない。
    seed = RequirementSeed.model_validate_json(seed.model_dump_json())
    for name in TABLES:
        unique(getattr(seed, name), record_key, name)
    # 科目マスタの読取りから投入完了まで書込みロックを保持し、並行シードと競合させない。
    with uow.write():
        subjects = uow.requirements.subjects()
        existing = uow.requirements.load()
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
                        raise RequirementSeedError(
                            f"{name}の既存データと内容が異なります。通常のシードでは更新できません。"
                        )
                else:
                    new.append(record)
            combined[name] = current + new
            additions[name] = new
        ordered = validate_requirements(RequirementSeed(**combined), subjects)
        # 親要件も同じテーブルなので、親から順に追加する。
        new_ids = {record.id for record in additions["graduation_requirements"]}
        additions["graduation_requirements"] = [
            row for row in ordered if row.id in new_ids
        ]
        uow.requirements.insert(RequirementSeed(**additions))
    return {name: len(additions[name]) for name in TABLES}

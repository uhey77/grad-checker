"""要件マスタの原子的な追加投入。既存行の変更・削除は拒否する。"""

from abc import ABC, abstractmethod

from modules.requirements.grad_checker_requirements.application.seed import (
    CreditRuleCourseData,
    CreditRuleData,
    CreditRuleLimitData,
    RequirementData,
    RequirementScopeData,
    RequirementSeed,
)
from modules.shared.grad_checker_shared.application.unit_of_work import UnitOfWork
from modules.subjects.grad_checker_subjects.public import SubjectDataSeed

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

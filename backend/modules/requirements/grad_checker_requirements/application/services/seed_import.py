"""卒業要件マスタの投入順序と既存データを照合するキー。"""

from ..dto.completion_policy import CompletionPolicyData
from ..dto.seed import (
    CreditRuleCourseData,
    CreditRuleData,
    CreditRuleLimitData,
    RequirementData,
    RequirementScopeData,
    RequirementSeed,
)

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

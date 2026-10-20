"""単位条件の判定を公開DTOへ変換する。"""

from modules.requirements.application.dto.evaluation import CreditSummary
from modules.requirements.domain.value_objects.credits import CreditRequirement


def summarize(required: int, earned: int, credited: int) -> CreditSummary:
    condition = CreditRequirement(required=required, credited=credited)
    return CreditSummary(
        required_credits=required,
        earned_credits=earned,
        credited_credits=credited,
        shortage=condition.shortage,
        result=condition.result,
    )

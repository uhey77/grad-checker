"""単位条件の判定を公開DTOへ変換する。"""

from ..domain.credits import CreditRequirement
from .evaluation_models import CreditSummary


def summarize(required: int, earned: int, credited: int) -> CreditSummary:
    condition = CreditRequirement(required, credited)
    return CreditSummary(
        required_credits=required,
        earned_credits=earned,
        credited_credits=credited,
        shortage=condition.shortage,
        result=condition.result,
    )

"""単位の充足と、同時期に修得した他学部単位の配分規則。"""

from collections.abc import Sequence
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CreditRequirement(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    required: int = Field(ge=0)
    credited: int = Field(ge=0)

    @property
    def shortage(self) -> int:
        return max(self.required - self.credited, 0)

    @property
    def result(self) -> Literal["pass", "fail"]:
        return "fail" if self.shortage else "pass"


class AllocationTarget(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    id: UUID
    code: str
    available_credits: int = Field(ge=0)
    conditions: tuple[CreditRequirement, ...]

    def score(self, additional_credits: int) -> tuple[int, int]:
        shortages = [
            CreditRequirement(
                required=c.required, credited=c.credited + additional_credits
            ).shortage
            for c in self.conditions
        ]
        return sum(value == 0 for value in shortages), -sum(shortages)


def allocate_best_fit(
    targets: Sequence[AllocationTarget], limit: int
) -> dict[UUID, int]:
    """達成条件数を最大化し、次に不足単位を最小化。同点は分類コード順で固定。"""
    ordered = sorted(targets, key=lambda target: target.code)
    # 共通上限ごとの最良状態を残し、科目数に対する全組合せ探索を避ける。
    states: dict[int, tuple[int, int, tuple[int, ...]]] = {0: (0, 0, ())}
    for target in ordered:
        following: dict[int, tuple[int, int, tuple[int, ...]]] = {}
        for used, (passed, shortage, values) in states.items():
            for value in range(min(target.available_credits, limit - used) + 1):
                fulfilled, deficit = target.score(value)
                candidate = (passed + fulfilled, shortage + deficit, (*values, value))
                count = used + value
                if count not in following or candidate > following[count]:
                    following[count] = candidate
        states = following
    return dict(zip((target.id for target in ordered), states[limit][2], strict=True))

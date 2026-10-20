"""単位の充足と、同時期に修得した他学部単位の配分規則。"""

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

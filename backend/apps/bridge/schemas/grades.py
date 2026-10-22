from typing import Literal, Self

from pydantic import model_validator

from apps.bridge.schemas.call import WritableSessionCall
from modules.grades.public import GradeSet


class GradeCall(WritableSessionCall):
    operation: Literal["get", "save"]
    grade_set: GradeSet | None = None

    @model_validator(mode="after")
    def arguments_match(self) -> Self:
        return self.check_write(self.operation == "save", self.grade_set)

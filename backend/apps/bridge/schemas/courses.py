from typing import Literal, Self

from pydantic import model_validator

from apps.bridge.schemas.call import SessionCall
from modules.subjects.public import CourseFilters


class CourseCall(SessionCall):
    operation: Literal["courses", "categories"]
    filters: CourseFilters | None = None

    @model_validator(mode="after")
    def arguments_match(self) -> Self:
        if (self.operation == "categories") and self.filters is not None:
            raise ValueError("categories does not accept filters")
        return self

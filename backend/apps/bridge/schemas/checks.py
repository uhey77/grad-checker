from typing import Literal, Self
from uuid import UUID

from pydantic import Field, model_validator

from apps.bridge.schemas.call import WritableSessionCall
from modules.requirements.public import CheckPage, CheckRequest


class CheckCall(WritableSessionCall):
    operation: Literal["create", "list", "get"]
    request: CheckRequest | None = None
    page: CheckPage | None = None
    check_id: UUID | None = Field(default=None, strict=False)

    @model_validator(mode="after")
    def arguments_match(self) -> Self:
        if (self.operation == "get") != (self.check_id is not None):
            raise ValueError("check_id is required only for get")
        if (self.operation == "list") != (self.page is not None):
            raise ValueError("page is required only for list")
        return self.check_write(self.operation == "create", self.request)

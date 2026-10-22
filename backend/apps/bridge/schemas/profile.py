from typing import Literal, Self

from pydantic import model_validator

from apps.bridge.schemas.call import WritableSessionCall
from modules.accounts.public import (
    ProgramSelection,
)


class ProfileCall(WritableSessionCall):
    operation: Literal["programs", "me", "save_program"]
    selection: ProgramSelection | None = None

    @model_validator(mode="after")
    def arguments_match(self) -> Self:
        return self.check_write(self.operation == "save_program", self.selection)

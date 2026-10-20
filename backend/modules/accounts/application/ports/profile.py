"""本人の所属の取得・保存とトランザクションの契約。"""

from abc import ABC, abstractmethod

from modules.accounts.application.dto.profile import (
    Profile,
    ProgramOption,
    ProgramSelection,
)


class ProfileRepository(ABC):
    @abstractmethod
    def list_programs(self) -> list[ProgramOption]: ...

    @abstractmethod
    def get_profile(self, student_id: str) -> Profile: ...

    @abstractmethod
    def save_program(self, student_id: str, selection: ProgramSelection) -> Profile: ...

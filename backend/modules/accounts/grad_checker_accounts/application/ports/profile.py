"""本人の所属の取得・保存とトランザクションの契約。"""

from abc import ABC, abstractmethod

from modules.shared.grad_checker_shared.application.ports.unit_of_work import UnitOfWork

from ..dto.profile import Profile, ProgramOption, ProgramSelection


class ProfileRepository(ABC):
    @abstractmethod
    def list_programs(self) -> list[ProgramOption]: ...

    @abstractmethod
    def get_profile(self, student_id: str) -> Profile: ...

    @abstractmethod
    def save_program(self, student_id: str, selection: ProgramSelection) -> Profile: ...


class ProfileUnitOfWork(UnitOfWork):
    @property
    @abstractmethod
    def profiles(self) -> ProfileRepository: ...

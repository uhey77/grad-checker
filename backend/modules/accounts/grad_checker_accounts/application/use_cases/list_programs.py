"""ListProgramsUseCaseの処理手順とトランザクション境界。"""

from ..profile import ProfileUnitOfWork, ProgramOption


class ListProgramsUseCase:
    def __init__(self, uow: ProfileUnitOfWork) -> None:
        self.uow = uow

    def execute(self) -> list[ProgramOption]:
        with self.uow.read():
            return self.uow.profiles.list_programs()

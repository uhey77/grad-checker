"""SaveProgramUseCaseの処理手順とトランザクション境界。"""

from ..profile import Profile, ProfileUnitOfWork, ProgramSelection


class SaveProgramUseCase:
    def __init__(self, uow: ProfileUnitOfWork) -> None:
        self.uow = uow

    def execute(self, student_id: str, selection: ProgramSelection) -> Profile:
        # 組合せの検証と版付き更新を、同じ書込みロックの下で行う。
        with self.uow.write():
            return self.uow.profiles.save_program(student_id, selection)

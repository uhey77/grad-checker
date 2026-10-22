"""SaveProgramUseCaseの処理手順とトランザクション境界。"""

from modules.accounts.application.dto.profile import Profile, ProgramSelection
from modules.accounts.application.uow.profile import ProfileUnitOfWork


class SaveProgramUseCase:
    def __init__(self, uow: ProfileUnitOfWork) -> None:
        self.uow = uow

    def execute(self, student_id: str, selection: ProgramSelection) -> Profile:
        # 組合せの検証と版付き更新を、同じ書込みロックの下で行う。
        with self.uow.write():
            return self.uow.profiles.save_program(student_id, selection)

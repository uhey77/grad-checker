"""GetSelectedCurriculumUseCaseの処理手順とトランザクション境界。"""

from modules.accounts.application.errors.profile import ProfileError
from modules.accounts.application.uow.profile import ProfileUnitOfWork


class GetSelectedCurriculumUseCase:
    def __init__(self, uow: ProfileUnitOfWork) -> None:
        self.uow = uow

    def execute(self, student_id: str) -> str:
        """本人課程を前提とする処理のため、所属未設定を業務エラーにする。"""
        with self.uow.read():
            curriculum_id = self.uow.profiles.get_profile(student_id).curriculum_id
        if curriculum_id is None:
            raise ProfileError("program_not_selected")
        return curriculum_id

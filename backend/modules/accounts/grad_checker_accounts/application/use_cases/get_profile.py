"""GetProfileUseCaseの処理手順とトランザクション境界。"""

from ..profile import Profile, ProfileUnitOfWork


class GetProfileUseCase:
    def __init__(self, uow: ProfileUnitOfWork) -> None:
        self.uow = uow

    def execute(self, student_id: str) -> Profile:
        with self.uow.read():
            return self.uow.profiles.get_profile(student_id)

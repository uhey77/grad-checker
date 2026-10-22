"""GetCheckUseCaseの処理手順とトランザクション境界。"""

from uuid import UUID

from modules.requirements.application.dto.check_results import SavedCheck
from modules.requirements.application.errors.evaluation import EvaluationError
from modules.requirements.application.uow.check_results import CheckUnitOfWork


class GetCheckUseCase:
    def __init__(self, uow: CheckUnitOfWork) -> None:
        self.uow = uow

    def execute(self, student_id: str, check_id: UUID) -> SavedCheck:
        with self.uow.read():
            check = self.uow.checks.get(student_id, check_id)
        # 他人の履歴と存在しない履歴を区別しない。
        if check is None:
            raise EvaluationError("check_not_found", "判定履歴が見つかりません。")
        return check

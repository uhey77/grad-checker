"""要件マスタの投入エラー。CLIで理由を表示する。"""

from modules.shared.grad_checker_shared.application.errors.business import BusinessError


class RequirementSeedError(BusinessError):
    code = "invalid_requirement_data"

    def __init__(self, message: str) -> None:
        super().__init__()
        self.message = message

    def __str__(self) -> str:
        return self.message

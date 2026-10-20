"""科目データのシード処理で発生する業務エラー。CLIで理由を表示する。"""

from shared.application.errors.business import BusinessError


class SeedError(BusinessError):
    """利用者へ表示できるシードエラー。"""

    code = "invalid_subject_data"

    def __init__(self, message: str) -> None:
        super().__init__()
        self.message = message

    def __str__(self) -> str:
        return self.message

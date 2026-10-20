"""確定判定を返せない入力・マスタ・算入規則のエラー。"""

from uuid import UUID

from shared.application.errors.business import BusinessError


class EvaluationError(BusinessError):
    def __init__(self, code: str, reason: str, *, rule_id: UUID | None = None) -> None:
        super().__init__(code)
        self.reason = reason
        self.rule_id = rule_id

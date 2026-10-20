"""認証処理の業務エラー。"""

from modules.shared.grad_checker_shared.application.errors.business import BusinessError


class AuthError(BusinessError):
    pass

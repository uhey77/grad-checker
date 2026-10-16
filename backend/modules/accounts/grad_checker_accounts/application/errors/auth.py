"""認証処理の業務エラー。"""

from modules.shared.grad_checker_shared.application.errors import BusinessError


class AuthError(BusinessError):
    pass

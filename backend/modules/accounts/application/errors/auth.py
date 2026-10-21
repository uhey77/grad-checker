"""認証処理の業務エラー。"""

from shared.application.errors.business import BusinessError


class AuthError(BusinessError):
    pass

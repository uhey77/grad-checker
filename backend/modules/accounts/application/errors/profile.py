"""所属取得・保存の業務エラー。外部HTTPへの変換はGoで行う。"""

from shared.application.errors.business import BusinessError


class ProfileError(BusinessError):
    pass

"""成績取得・保存の業務エラー。外部HTTPへの変換はGoで行う。"""

from modules.shared.grad_checker_shared.application.errors.business import BusinessError


class GradeError(BusinessError):
    pass

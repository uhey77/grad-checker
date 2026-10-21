"""学生向け科目一覧・分類の業務エラー。外部HTTPへの変換はGoで行う。"""

from shared.application.errors.business import BusinessError


class CourseCatalogError(BusinessError):
    pass

"""科目一覧の取得で発生する業務エラー。コードはブリッジ通信でGoへ返す。"""

from shared.application.errors.business import BusinessError


class SubjectListNotFoundError(BusinessError):
    """指定されたカリキュラムが見つからない。"""

    code = "curriculum_not_found"


class SubjectListIntegrityError(BusinessError):
    """科目分類の階層が不整合。"""

    code = "classification_inconsistent"


class SubjectListUnavailableError(BusinessError):
    """科目データの取得先が利用できない。"""

    code = "subject_list_unavailable"

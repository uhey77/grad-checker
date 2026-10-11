"""科目一覧の取得で発生する例外。"""


class SubjectListNotFoundError(ValueError):
    """指定されたカリキュラムが見つからない。"""


class SubjectListIntegrityError(ValueError):
    """科目分類の階層が不整合。"""


class SubjectListUnavailableError(RuntimeError):
    """科目データの取得先が利用できない。"""

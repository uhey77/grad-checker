"""科目一覧の取得で発生する例外。"""


class SubjectListNotFoundError(ValueError):
    """指定されたカリキュラムが見つからない。"""

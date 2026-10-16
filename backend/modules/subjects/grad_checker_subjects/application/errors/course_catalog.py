"""学生向け科目一覧・分類の業務エラー。外部HTTPへの変換はGoで行う。"""


class CourseCatalogError(Exception):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)

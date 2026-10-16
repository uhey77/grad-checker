"""成績取得・保存の業務エラー。外部HTTPへの変換はGoで行う。"""


class GradeError(Exception):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)

"""各業務モジュールの業務エラーの共通基底。外部HTTPへの変換はGoで行う。"""


class BusinessError(Exception):
    """ブリッジアダプターが {"error": {"code": ...}} として返す業務エラー。

    コードを固定するエラーはクラス属性 ``code`` を定義し、引数なしで送出する。
    """

    code: str

    def __init__(self, code: str | None = None) -> None:
        if code is not None:
            self.code = code
        super().__init__(self.code)

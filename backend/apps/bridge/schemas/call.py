from typing import Self

from pydantic import BaseModel, ConfigDict, Field


class SessionCall(BaseModel):
    """本人セッションで行うブリッジ呼出し。本人IDはセッションからのみ決定する。"""

    model_config = ConfigDict(extra="forbid", strict=True)
    token: str = Field(min_length=43, max_length=43)


class WritableSessionCall(SessionCall):
    """本人データを変更する操作を含む呼出し。書込みだけがCSRFと変更内容を持つ。"""

    csrf: str = Field(default="", max_length=64)

    def check_write(self, writes: bool, payload: object | None) -> Self:
        if writes:
            if payload is None or len(self.csrf) != 64:
                raise ValueError("write payload and csrf required")
        elif payload is not None or self.csrf:
            raise ValueError("unexpected write arguments")
        return self

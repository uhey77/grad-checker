"""ブリッジアダプターで共通の包絡形式と呼出し契約。外部HTTPの判断はGoで行う。"""

import logging
from collections.abc import Callable
from typing import Self

from pydantic import BaseModel, ConfigDict, Field

from modules.shared.grad_checker_shared.application.errors import BusinessError

logger = logging.getLogger(__name__)


def failure(code: str) -> dict[str, object]:
    return {"error": {"code": code}}


def respond(action: Callable[[], object]) -> dict[str, object]:
    """結果を {"data": ...}、業務エラーを {"error": {"code": ...}} として返す。"""
    try:
        return {"data": action()}
    except BusinessError as error:
        return failure(error.code)
    except Exception:
        # 予期しない失敗の詳細はPythonのログだけに残し、Goへはコードだけを返す。
        logger.exception("Unexpected bridge call failure")
        return failure("internal_error")


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

"""ブリッジアダプターで共通の包絡形式と呼出し契約。外部HTTPの判断はGoで行う。"""

import logging
from collections.abc import Callable

from shared.application.errors.business import BusinessError

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

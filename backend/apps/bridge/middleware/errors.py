"""ブリッジ呼出しの契約違反を共通の包絡形式へ変換する。"""

from fastapi import Request
from fastapi.responses import JSONResponse

from apps.bridge.controllers.go_bridge_call import failure


def invalid_go_bridge_call(_request: Request, _error: Exception) -> JSONResponse:
    # ブリッジ呼出しの契約違反。利用者向け422への変換はここで行わない。
    return JSONResponse(failure("invalid_request"))

"""運用向けreadiness。接続詳細は外部へ返さない。"""

from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

router = APIRouter()


def get_probe(request: Request) -> Callable[[], bool]:
    return request.app.state.database_probe


@router.get("/bridge/health")
def health(probe: Annotated[Callable[[], bool], Depends(get_probe)]) -> JSONResponse:
    ready = probe()
    return JSONResponse(
        {"status": "ok" if ready else "unavailable"},
        status_code=200 if ready else 503,
    )

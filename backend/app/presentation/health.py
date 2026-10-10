"""個人情報を返さない、プロセスの稼働確認用エンドポイント。"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health", tags=["運用"])
def health() -> dict[str, str]:
    return {"status": "ok"}

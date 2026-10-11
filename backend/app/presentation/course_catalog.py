"""明示的に有効化したローカル確認用の読取API。学生用APIとは別経路。"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.exc import SQLAlchemyError

from app.application.errors.course_catalog import CatalogNotFound
from app.application.course_catalog import (
    CatalogProgram,
    CourseCatalog,
    get_course_catalog,
    list_catalog_programs,
)
from app.infrastructure.course_catalog import SqliteCatalogRepository
from app.presentation.dependencies import SessionDependency


def require_catalog_preview(request: Request, response: Response) -> None:
    if not request.app.state.settings.enable_catalog_preview:
        raise HTTPException(status_code=404, detail="科目一覧の開発用表示は無効です。")
    response.headers["Cache-Control"] = "no-store"


router = APIRouter(
    prefix="/dev/course-catalog",
    tags=["開発用科目一覧"],
    dependencies=[Depends(require_catalog_preview)],
)


@router.get("/programs", response_model=list[CatalogProgram])
def programs(session: SessionDependency) -> list[CatalogProgram]:
    try:
        return list_catalog_programs(SqliteCatalogRepository(session))
    except SQLAlchemyError as error:
        raise HTTPException(
            status_code=503,
            detail="科目データを読み込めません。時間をおいて再試行してください。",
        ) from error


@router.get("/{curriculum_id}", response_model=CourseCatalog)
def catalog(curriculum_id: str, session: SessionDependency) -> CourseCatalog:
    try:
        identifier = UUID(curriculum_id)
    except ValueError as error:
        raise HTTPException(
            status_code=422, detail="カリキュラムIDの形式が不正です。"
        ) from error
    try:
        return get_course_catalog(SqliteCatalogRepository(session), identifier)
    except CatalogNotFound as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(
            status_code=409,
            detail="科目分類のデータが不整合です。課程・科目データを確認してください。",
        ) from error
    except SQLAlchemyError as error:
        raise HTTPException(
            status_code=503,
            detail="科目データを読み込めません。時間をおいて再試行してください。",
        ) from error

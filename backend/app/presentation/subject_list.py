"""明示的に有効化したローカル確認用の読取API。学生用APIとは別経路。"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.exc import SQLAlchemyError

from app.application.errors.subject_list import SubjectListNotFoundError
from app.application.subject_list import (
    SubjectList,
    SubjectListProgram,
    get_subject_list,
    list_subject_programs,
)
from app.infrastructure.subject_list import SqliteSubjectListRepository
from app.presentation.dependencies import SessionDependency


def require_subject_list_preview(request: Request, response: Response) -> None:
    if not request.app.state.settings.enable_subject_list_preview:
        raise HTTPException(status_code=404, detail="科目一覧の開発用表示は無効です。")
    response.headers["Cache-Control"] = "no-store"


router = APIRouter(
    prefix="/dev/course-catalog",
    tags=["開発用科目一覧"],
    dependencies=[Depends(require_subject_list_preview)],
)


@router.get("/programs", response_model=list[SubjectListProgram])
def programs(session: SessionDependency) -> list[SubjectListProgram]:
    try:
        return list_subject_programs(SqliteSubjectListRepository(session))
    except SQLAlchemyError as error:
        raise HTTPException(
            status_code=503,
            detail="科目データを読み込めません。時間をおいて再試行してください。",
        ) from error


@router.get("/{curriculum_id}", response_model=SubjectList)
def subject_list(curriculum_id: str, session: SessionDependency) -> SubjectList:
    try:
        identifier = UUID(curriculum_id)
    except ValueError as error:
        raise HTTPException(
            status_code=422, detail="カリキュラムIDの形式が不正です。"
        ) from error
    try:
        return get_subject_list(SqliteSubjectListRepository(session), identifier)
    except SubjectListNotFoundError as error:
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

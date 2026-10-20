"""学生向け科目一覧・分類のブリッジアダプター。本人課程はセッションから決定する。"""

from typing import Annotated, Literal, Self

from fastapi import APIRouter, Depends
from pydantic import model_validator

from api.api_service.presentation.dependencies import (
    authenticate_session,
    current_identity,
    get_selected_curriculum,
    list_categories,
    list_courses,
)
from api.api_service.presentation.go_bridge_call import SessionCall, respond
from modules.accounts.grad_checker_accounts.public import (
    AuthenticateSessionUseCase,
    GetSelectedCurriculumUseCase,
)
from modules.subjects.grad_checker_subjects.public import (
    CourseFilters,
    ListCategoriesUseCase,
    ListCoursesUseCase,
)

router = APIRouter(prefix="/bridge")


class CourseCall(SessionCall):
    operation: Literal["courses", "categories"]
    filters: CourseFilters | None = None

    @model_validator(mode="after")
    def arguments_match(self) -> Self:
        if (self.operation == "categories") and self.filters is not None:
            raise ValueError("categories does not accept filters")
        return self


@router.post("/courses")
def courses(
    call: CourseCall,
    list_courses: Annotated[ListCoursesUseCase, Depends(list_courses)],
    list_categories: Annotated[ListCategoriesUseCase, Depends(list_categories)],
    get_selected_curriculum: Annotated[
        GetSelectedCurriculumUseCase, Depends(get_selected_curriculum)
    ],
    auth: Annotated[AuthenticateSessionUseCase, Depends(authenticate_session)],
) -> dict[str, object]:
    def run() -> object:
        identity = current_identity(auth, call.token)
        curriculum_id = get_selected_curriculum.execute(identity.account.id)
        if call.operation == "categories":
            return list_categories.execute(curriculum_id)
        return list_courses.execute(curriculum_id, call.filters or CourseFilters())

    return respond(run)

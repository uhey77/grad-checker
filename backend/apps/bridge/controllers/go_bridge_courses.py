"""学生向け科目一覧・分類のブリッジアダプター。本人課程はセッションから決定する。"""

from typing import Annotated

from fastapi import APIRouter, Depends

from apps.bridge.controllers.go_bridge_call import respond
from apps.bridge.dependencies import (
    authenticate_session,
    current_identity,
    get_selected_curriculum,
    list_categories,
    list_courses,
)
from apps.bridge.schemas.courses import CourseCall
from modules.accounts.public import (
    AuthenticateSessionUseCase,
    GetSelectedCurriculumUseCase,
)
from modules.subjects.public import (
    CourseFilters,
    ListCategoriesUseCase,
    ListCoursesUseCase,
)

router = APIRouter(prefix="/bridge")


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

"""学生向け科目一覧・分類のブリッジアダプター。本人課程はセッションから決定する。"""

from typing import Annotated, Literal, Self

from fastapi import APIRouter, Depends
from pydantic import model_validator

from api.api_service.presentation.dependencies import (
    auth_service,
    course_catalog_service,
    current_identity,
    profile_service,
)
from api.api_service.presentation.go_bridge_call import SessionCall, respond
from modules.accounts.grad_checker_accounts.public import AuthService, ProfileService
from modules.subjects.grad_checker_subjects.public import (
    CourseCatalogService,
    CourseFilters,
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
    auth: Annotated[AuthService, Depends(auth_service)],
    service: Annotated[CourseCatalogService, Depends(course_catalog_service)],
    profiles: Annotated[ProfileService, Depends(profile_service)],
) -> dict[str, object]:
    def run() -> object:
        identity = current_identity(auth, call.token)
        curriculum_id = profiles.selected_curriculum(identity.account.id)
        if call.operation == "categories":
            return service.list_categories(curriculum_id)
        return service.list_courses(curriculum_id, call.filters or CourseFilters())

    return respond(run)

"""学生向け科目一覧・分類の内部アダプター。本人課程はセッションから決定する。"""

from typing import Literal, Self

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict, Field, model_validator

from api.api_service.presentation.dependencies import SessionDependency, auth_service
from modules.accounts.grad_checker_accounts.application.errors.auth import AuthError
from modules.accounts.grad_checker_accounts.application.errors.profile import (
    ProfileError,
)
from modules.accounts.grad_checker_accounts.application.profile import ProfileService
from modules.accounts.grad_checker_accounts.infrastructure.profile import (
    SqliteProfileRepository,
)
from modules.subjects.grad_checker_subjects.application.course_catalog import (
    CourseCatalogService,
    CourseFilters,
)
from modules.subjects.grad_checker_subjects.application.errors.course_catalog import (
    CourseCatalogError,
)
from modules.subjects.grad_checker_subjects.infrastructure.course_catalog import (
    SqliteCourseCatalogRepository,
)

router = APIRouter(prefix="/internal")


class CourseCall(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    operation: Literal["courses", "categories"]
    token: str = Field(min_length=43, max_length=43)
    filters: CourseFilters | None = None

    @model_validator(mode="after")
    def arguments_match(self) -> Self:
        if (self.operation == "categories") and self.filters is not None:
            raise ValueError("categories does not accept filters")
        return self


@router.post("/courses")
def courses(
    call: CourseCall, request: Request, session: SessionDependency
) -> dict[str, object]:
    try:
        identity = auth_service(request, session).session(call.token)
        profile = ProfileService(SqliteProfileRepository(session)).get_profile(
            identity.account.id
        )
        if profile.curriculum_id is None:
            return {"error": {"code": "program_not_selected"}}
        service = CourseCatalogService(SqliteCourseCatalogRepository(session))
        if call.operation == "categories":
            return {"data": service.list_categories(profile.curriculum_id)}
        return {
            "data": service.list_courses(
                profile.curriculum_id, call.filters or CourseFilters()
            )
        }
    except (AuthError, ProfileError, CourseCatalogError) as error:
        return {"error": {"code": error.code}}

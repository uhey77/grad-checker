"""学生向け科目一覧・分類のブリッジアダプター。本人課程はセッションから決定する。"""

from typing import Literal, Self

from fastapi import APIRouter, Request
from pydantic import model_validator

from api.api_service.presentation.dependencies import (
    SessionDependency,
    current_identity,
)
from api.api_service.presentation.go_bridge_call import SessionCall, respond
from modules.accounts.grad_checker_accounts.application.profile import ProfileService
from modules.accounts.grad_checker_accounts.infrastructure.profile import (
    SqliteProfileRepository,
)
from modules.subjects.grad_checker_subjects.application.course_catalog import (
    CourseCatalogService,
    CourseFilters,
)
from modules.subjects.grad_checker_subjects.infrastructure.course_catalog import (
    SqliteCourseCatalogRepository,
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
    call: CourseCall, request: Request, session: SessionDependency
) -> dict[str, object]:
    def run() -> object:
        identity = current_identity(request, session, call.token)
        curriculum_id = ProfileService(
            SqliteProfileRepository(session)
        ).selected_curriculum(identity.account.id)
        service = CourseCatalogService(SqliteCourseCatalogRepository(session))
        if call.operation == "categories":
            return service.list_categories(curriculum_id)
        return service.list_courses(curriculum_id, call.filters or CourseFilters())

    return respond(run)

"""ブリッジが必要とする契約。具体的な生成方法はComposition Rootで登録する。"""

from modules.accounts.grad_checker_accounts.public import (
    AuthService,
    ProfileService,
    SessionIdentity,
)
from modules.grades.grad_checker_grades.public import GradeService
from modules.requirements.grad_checker_requirements.public import (
    CheckService,
    EvaluationService,
)
from modules.subjects.grad_checker_subjects.public import (
    CourseCatalogService,
    SubjectListUnitOfWork,
)


def auth_service() -> AuthService:
    raise RuntimeError("AuthService is not configured")


def profile_service() -> ProfileService:
    raise RuntimeError("ProfileService is not configured")


def grade_service() -> GradeService:
    raise RuntimeError("GradeService is not configured")


def evaluation_service() -> EvaluationService:
    raise RuntimeError("EvaluationService is not configured")


def check_service() -> CheckService:
    raise RuntimeError("CheckService is not configured")


def course_catalog_service() -> CourseCatalogService:
    raise RuntimeError("CourseCatalogService is not configured")


def subject_list_uow() -> SubjectListUnitOfWork:
    raise RuntimeError("SubjectListUnitOfWork is not configured")


def current_identity(
    service: AuthService, token: str, csrf: str | None = None
) -> SessionIdentity:
    """本人はセッションから決定し、変更操作はCSRFトークンも照合する。"""
    if csrf is None:
        return service.session(token)
    return service.authorize(token, csrf)

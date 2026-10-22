"""ブリッジが必要とするUseCase。具体的な生成方法はComposition Rootで登録する。"""

from modules.accounts.public import (
    AuthenticateSessionUseCase,
    GetAuthPolicyUseCase,
    GetProfileUseCase,
    GetSelectedCurriculumUseCase,
    ListProgramsUseCase,
    LoginUseCase,
    LogoutUseCase,
    RecoverAccountUseCase,
    RegisterAccountUseCase,
    SaveProgramUseCase,
    SessionIdentity,
)
from modules.grades.public import GetGradesUseCase, SaveGradesUseCase
from modules.requirements.public import (
    CreateCheckUseCase,
    EvaluateGraduationUseCase,
    GetCheckUseCase,
    GetDashboardUseCase,
    ListChecksUseCase,
)
from modules.subjects.public import (
    GetSubjectListUseCase,
    ListCategoriesUseCase,
    ListCoursesUseCase,
    ListSubjectProgramsUseCase,
)


def register_account() -> RegisterAccountUseCase:
    raise RuntimeError("RegisterAccountUseCase is not configured")


def recover_account() -> RecoverAccountUseCase:
    raise RuntimeError("RecoverAccountUseCase is not configured")


def login() -> LoginUseCase:
    raise RuntimeError("LoginUseCase is not configured")


def logout() -> LogoutUseCase:
    raise RuntimeError("LogoutUseCase is not configured")


def authenticate_session() -> AuthenticateSessionUseCase:
    raise RuntimeError("AuthenticateSessionUseCase is not configured")


def get_auth_policy() -> GetAuthPolicyUseCase:
    raise RuntimeError("GetAuthPolicyUseCase is not configured")


def list_programs() -> ListProgramsUseCase:
    raise RuntimeError("ListProgramsUseCase is not configured")


def get_profile() -> GetProfileUseCase:
    raise RuntimeError("GetProfileUseCase is not configured")


def save_program() -> SaveProgramUseCase:
    raise RuntimeError("SaveProgramUseCase is not configured")


def get_selected_curriculum() -> GetSelectedCurriculumUseCase:
    raise RuntimeError("GetSelectedCurriculumUseCase is not configured")


def get_grades() -> GetGradesUseCase:
    raise RuntimeError("GetGradesUseCase is not configured")


def save_grades() -> SaveGradesUseCase:
    raise RuntimeError("SaveGradesUseCase is not configured")


def create_check() -> CreateCheckUseCase:
    raise RuntimeError("CreateCheckUseCase is not configured")


def get_check() -> GetCheckUseCase:
    raise RuntimeError("GetCheckUseCase is not configured")


def list_checks() -> ListChecksUseCase:
    raise RuntimeError("ListChecksUseCase is not configured")


def evaluate_graduation() -> EvaluateGraduationUseCase:
    raise RuntimeError("EvaluateGraduationUseCase is not configured")


def get_dashboard() -> GetDashboardUseCase:
    raise RuntimeError("GetDashboardUseCase is not configured")


def list_courses() -> ListCoursesUseCase:
    raise RuntimeError("ListCoursesUseCase is not configured")


def list_categories() -> ListCategoriesUseCase:
    raise RuntimeError("ListCategoriesUseCase is not configured")


def get_subject_list() -> GetSubjectListUseCase:
    raise RuntimeError("GetSubjectListUseCase is not configured")


def list_subject_programs() -> ListSubjectProgramsUseCase:
    raise RuntimeError("ListSubjectProgramsUseCase is not configured")


def current_identity(
    use_case: AuthenticateSessionUseCase, token: str, csrf: str | None = None
) -> SessionIdentity:
    return use_case.execute(token, csrf)

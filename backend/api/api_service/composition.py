"""PythonサービスのComposition Root。呼出しごとにUseCaseとUoWを生成する。"""

from collections.abc import Callable

from sqlalchemy import Engine

from api.api_service.presentation import dependencies
from config.settings import Settings
from modules.accounts.grad_checker_accounts.application.authentication import (
    SessionAuthentication,
)
from modules.accounts.grad_checker_accounts.infrastructure.profile import (
    SqliteProfileUnitOfWork,
)
from modules.accounts.grad_checker_accounts.infrastructure.repository import (
    SqliteAccountUnitOfWork,
)
from modules.accounts.grad_checker_accounts.public import (
    AuthenticateSessionUseCase,
    AuthPolicy,
    GetAuthPolicyUseCase,
    GetProfileUseCase,
    GetSelectedCurriculumUseCase,
    ListProgramsUseCase,
    LoginUseCase,
    LogoutUseCase,
    Passwords,
    RecoverAccountUseCase,
    RegisterAccountUseCase,
    SaveProgramUseCase,
)
from modules.grades.grad_checker_grades.infrastructure.grades import (
    SqliteGradeUnitOfWork,
)
from modules.grades.grad_checker_grades.public import (
    GetGradesUseCase,
    SaveGradesUseCase,
)
from modules.requirements.grad_checker_requirements.infrastructure import (
    check_results as check_storage,
)
from modules.requirements.grad_checker_requirements.infrastructure.evaluation import (
    SqliteEvaluationUnitOfWork,
)
from modules.requirements.grad_checker_requirements.public import (
    CreateCheckUseCase,
    EvaluateGraduationUseCase,
    GetCheckUseCase,
    GetDashboardUseCase,
    ListChecksUseCase,
)
from modules.shared.grad_checker_shared.infrastructure.clock import SystemClock
from modules.subjects.grad_checker_subjects.infrastructure.course_catalog import (
    SqliteCourseCatalogUnitOfWork,
)
from modules.subjects.grad_checker_subjects.infrastructure.subject_list import (
    SqliteSubjectListUnitOfWork,
)
from modules.subjects.grad_checker_subjects.public import (
    GetSubjectListUseCase,
    ListCategoriesUseCase,
    ListCoursesUseCase,
    ListSubjectProgramsUseCase,
)


def build_dependencies(
    engine: Engine, settings: Settings, passwords: Passwords
) -> dict[Callable[..., object], Callable[..., object]]:
    clock = SystemClock()
    policy = AuthPolicy(
        session_hours=settings.auth_session_hours,
        password_min_length=settings.auth_password_min_length,
        password_max_length=settings.auth_password_max_length,
        attempt_window_minutes=settings.auth_attempt_window_minutes,
        attempt_limit=settings.auth_attempt_limit,
    )

    def build_logout() -> LogoutUseCase:
        uow = SqliteAccountUnitOfWork(engine)
        return LogoutUseCase(uow, SessionAuthentication(uow, clock), clock)

    return {
        dependencies.register_account: lambda: RegisterAccountUseCase(
            SqliteAccountUnitOfWork(engine), passwords, policy, clock
        ),
        dependencies.recover_account: lambda: RecoverAccountUseCase(
            SqliteAccountUnitOfWork(engine), passwords, policy, clock
        ),
        dependencies.login: lambda: LoginUseCase(
            SqliteAccountUnitOfWork(engine), passwords, policy, clock
        ),
        dependencies.logout: build_logout,
        dependencies.authenticate_session: lambda: AuthenticateSessionUseCase(
            SessionAuthentication(SqliteAccountUnitOfWork(engine), clock)
        ),
        dependencies.get_auth_policy: lambda: GetAuthPolicyUseCase(policy),
        dependencies.list_programs: lambda: ListProgramsUseCase(
            SqliteProfileUnitOfWork(engine)
        ),
        dependencies.get_profile: lambda: GetProfileUseCase(
            SqliteProfileUnitOfWork(engine)
        ),
        dependencies.save_program: lambda: SaveProgramUseCase(
            SqliteProfileUnitOfWork(engine)
        ),
        dependencies.get_selected_curriculum: lambda: GetSelectedCurriculumUseCase(
            SqliteProfileUnitOfWork(engine)
        ),
        dependencies.get_grades: lambda: GetGradesUseCase(
            SqliteGradeUnitOfWork(engine)
        ),
        dependencies.save_grades: lambda: SaveGradesUseCase(
            SqliteGradeUnitOfWork(engine)
        ),
        dependencies.create_check: lambda: CreateCheckUseCase(
            check_storage.SqliteCheckUnitOfWork(engine), clock
        ),
        dependencies.get_check: lambda: GetCheckUseCase(
            check_storage.SqliteCheckUnitOfWork(engine)
        ),
        dependencies.list_checks: lambda: ListChecksUseCase(
            check_storage.SqliteCheckUnitOfWork(engine)
        ),
        dependencies.evaluate_graduation: lambda: EvaluateGraduationUseCase(
            SqliteEvaluationUnitOfWork(engine), clock
        ),
        dependencies.get_dashboard: lambda: GetDashboardUseCase(
            SqliteEvaluationUnitOfWork(engine), clock
        ),
        dependencies.list_courses: lambda: ListCoursesUseCase(
            SqliteCourseCatalogUnitOfWork(engine)
        ),
        dependencies.list_categories: lambda: ListCategoriesUseCase(
            SqliteCourseCatalogUnitOfWork(engine)
        ),
        dependencies.get_subject_list: lambda: GetSubjectListUseCase(
            SqliteSubjectListUnitOfWork(engine)
        ),
        dependencies.list_subject_programs: lambda: ListSubjectProgramsUseCase(
            SqliteSubjectListUnitOfWork(engine)
        ),
    }

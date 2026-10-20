"""PythonサービスのComposition Root。要求ごとに独立したUoWを組み立てる。"""

from collections.abc import Callable

from sqlalchemy import Engine

from api.api_service.presentation import dependencies
from config.settings import Settings
from modules.accounts.grad_checker_accounts.infrastructure.profile import (
    SqliteProfileUnitOfWork,
)
from modules.accounts.grad_checker_accounts.infrastructure.repository import (
    SqliteAccountUnitOfWork,
)
from modules.accounts.grad_checker_accounts.public import (
    AuthPolicy,
    AuthService,
    Passwords,
    ProfileService,
)
from modules.grades.grad_checker_grades.infrastructure.grades import (
    SqliteGradeUnitOfWork,
)
from modules.grades.grad_checker_grades.public import GradeService
from modules.requirements.grad_checker_requirements.infrastructure import (
    check_results as check_storage,
)
from modules.requirements.grad_checker_requirements.infrastructure.evaluation import (
    SqliteEvaluationUnitOfWork,
)
from modules.requirements.grad_checker_requirements.public import (
    CheckService,
    EvaluationService,
)
from modules.shared.grad_checker_shared.infrastructure.clock import SystemClock
from modules.subjects.grad_checker_subjects.infrastructure.course_catalog import (
    SqliteCourseCatalogUnitOfWork,
)
from modules.subjects.grad_checker_subjects.infrastructure.subject_list import (
    SqliteSubjectListUnitOfWork,
)
from modules.subjects.grad_checker_subjects.public import CourseCatalogService


def build_dependencies(
    engine: Engine, settings: Settings, passwords: Passwords
) -> dict[Callable[..., object], Callable[..., object]]:
    """Engineと設定はプロセス単位。Sessionは各UoWのread/writeで開閉する。"""
    clock = SystemClock()
    policy = AuthPolicy(
        session_hours=settings.auth_session_hours,
        password_min_length=settings.auth_password_min_length,
        password_max_length=settings.auth_password_max_length,
        attempt_window_minutes=settings.auth_attempt_window_minutes,
        attempt_limit=settings.auth_attempt_limit,
    )
    return {
        dependencies.auth_service: lambda: AuthService(
            SqliteAccountUnitOfWork(engine), passwords, policy, clock
        ),
        dependencies.profile_service: lambda: ProfileService(
            SqliteProfileUnitOfWork(engine)
        ),
        dependencies.grade_service: lambda: GradeService(SqliteGradeUnitOfWork(engine)),
        dependencies.evaluation_service: lambda: EvaluationService(
            SqliteEvaluationUnitOfWork(engine), clock
        ),
        dependencies.check_service: lambda: CheckService(
            check_storage.SqliteCheckUnitOfWork(engine), clock
        ),
        dependencies.course_catalog_service: lambda: CourseCatalogService(
            SqliteCourseCatalogUnitOfWork(engine)
        ),
        dependencies.subject_list_uow: lambda: SqliteSubjectListUnitOfWork(engine),
    }

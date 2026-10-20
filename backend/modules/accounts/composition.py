"""この業務モジュールの具体実装を操作別UseCaseへ注入する。"""

from collections.abc import Callable

from sqlalchemy import Engine

from modules.accounts.application.services.authentication import SessionAuthentication
from modules.accounts.infrastructure.persistence.unit_of_work import (
    SqliteAccountUnitOfWork,
    SqliteProfileUnitOfWork,
)
from modules.accounts.public import (
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
from shared.application.ports.clock import Clock


def build_use_cases(
    engine: Engine, passwords: Passwords, policy: AuthPolicy, clock: Clock
) -> dict[str, Callable[[], object]]:
    def build_logout() -> LogoutUseCase:
        uow = SqliteAccountUnitOfWork(engine)
        return LogoutUseCase(uow, SessionAuthentication(uow, clock), clock)

    return {
        "register_account": lambda: RegisterAccountUseCase(
            SqliteAccountUnitOfWork(engine), passwords, policy, clock
        ),
        "recover_account": lambda: RecoverAccountUseCase(
            SqliteAccountUnitOfWork(engine), passwords, policy, clock
        ),
        "login": lambda: LoginUseCase(
            SqliteAccountUnitOfWork(engine), passwords, policy, clock
        ),
        "logout": build_logout,
        "authenticate_session": lambda: AuthenticateSessionUseCase(
            SessionAuthentication(SqliteAccountUnitOfWork(engine), clock)
        ),
        "get_auth_policy": lambda: GetAuthPolicyUseCase(policy),
        "list_programs": lambda: ListProgramsUseCase(SqliteProfileUnitOfWork(engine)),
        "get_profile": lambda: GetProfileUseCase(SqliteProfileUnitOfWork(engine)),
        "save_program": lambda: SaveProgramUseCase(SqliteProfileUnitOfWork(engine)),
        "get_selected_curriculum": lambda: GetSelectedCurriculumUseCase(
            SqliteProfileUnitOfWork(engine)
        ),
    }

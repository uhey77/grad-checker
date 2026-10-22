"""ブリッジのComposition Root。各モジュールのファクトリーをHTTPの依存へ接続する。"""

from collections.abc import Callable

from sqlalchemy import Engine

from apps.bridge import dependencies
from apps.settings import Settings
from modules.accounts.composition import build_use_cases as account_factories
from modules.accounts.public import AuthPolicy, Passwords
from modules.grades.composition import build_use_cases as grade_factories
from modules.requirements.composition import build_use_cases as requirement_factories
from modules.subjects.composition import build_use_cases as subject_factories
from shared.infrastructure.clock import SystemClock


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
    factories = {
        **account_factories(engine, passwords, policy, clock),
        **grade_factories(engine),
        **requirement_factories(engine, clock),
        **subject_factories(engine),
    }
    return {getattr(dependencies, name): factory for name, factory in factories.items()}

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect, text

from api.api_service.main import create_app
from api.api_service.presentation.dependencies import register_account
from config.settings import Settings
from modules.accounts.grad_checker_accounts.public import (
    AuthenticateSessionUseCase,
    RegisterAccountUseCase,
)


def test_startup_and_python_service(tmp_path: Path) -> None:
    database_path = tmp_path / "data" / "test.db"
    application = create_app(Settings(database_url=f"sqlite:///{database_path}"))

    with TestClient(application) as client:
        response = client.post(
            "/bridge/subject-list", json={"operation": "list_programs"}
        )
        assert response.status_code == 200
        assert response.json() == {"data": []}
        assert client.get("/docs").status_code == 404
        assert client.get("/openapi.json").status_code == 404
        assert set(inspect(application.state.database_engine).get_table_names()) == {
            "academic_programs",
            "curricula",
            "classifications",
            "courses",
            "course_offerings",
            "curriculum_courses",
            "students",
            "student_credentials",
            "auth_sessions",
            "auth_attempts",
            "grade_attempts",
            "graduation_requirements",
            "requirement_scopes",
            "credit_rules",
            "credit_rule_courses",
            "credit_rule_limits",
            "check_results",
            "completion_policies",
        }
        with application.state.database_engine.connect() as connection:
            assert connection.execute(text("SELECT 1")).scalar_one() == 1

    assert database_path.is_file()


def test_database_url_is_loaded_at_startup(tmp_path: Path, monkeypatch) -> None:
    application = create_app()
    database_path = tmp_path / "configured.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_path}")

    with TestClient(application):
        assert Path(application.state.database_engine.url.database) == database_path


def test_composition_creates_request_local_uows_and_cleans_up_on_restart(tmp_path):
    application = create_app(Settings(database_url=f"sqlite:///{tmp_path / 't.db'}"))
    previous = None
    for _ in range(2):
        with TestClient(application) as client:
            factory = application.dependency_overrides[register_account]
            first, second = factory(), factory()
            assert isinstance(first, RegisterAccountUseCase)
            assert isinstance(second, RegisterAccountUseCase)
            assert first.uow is not second.uow
            assert first.passwords is second.passwords
            assert first.clock is second.clock
            if previous is not None:
                assert factory is not previous
            assert (
                client.post("/bridge/auth", json={"operation": "config"}).status_code
                == 200
            )
            previous = factory
        assert register_account not in application.dependency_overrides


def test_composition_preserves_dependency_overrides(tmp_path):
    application = create_app(Settings(database_url=f"sqlite:///{tmp_path / 't.db'}"))

    def custom_auth():
        # このテストの開発用科目一覧経路は認証を利用しない。
        raise AssertionError("should not resolve auth")

    application.dependency_overrides[register_account] = custom_auth
    with TestClient(application) as client:
        assert application.dependency_overrides[register_account] is custom_auth
        assert client.post(
            "/bridge/subject-list", json={"operation": "list_programs"}
        ).json() == {"data": []}
    assert application.dependency_overrides[register_account] is custom_auth


@pytest.mark.parametrize(
    ("path", "call", "target"),
    [
        (
            "/bridge/subject-list",
            {"operation": "list_programs"},
            "modules.subjects.grad_checker_subjects.public.ListSubjectProgramsUseCase.execute",
        ),
        ("/bridge/auth", {"operation": "session", "token": "t" * 43}, None),
        ("/bridge/grades", {"operation": "get", "token": "t" * 43}, None),
    ],
)
def test_unexpected_failures_return_internal_error_code(
    tmp_path: Path, monkeypatch, path: str, call: dict[str, str], target: str | None
) -> None:
    def broken(*_args: object) -> None:
        raise RuntimeError("テスト用の障害")

    # 全てのブリッジアダプターが同じ包絡形式で予期しない失敗を返す。
    if target is None:
        monkeypatch.setattr(AuthenticateSessionUseCase, "execute", broken)
    else:
        monkeypatch.setattr(target, broken)
    application = create_app(Settings(database_url=f"sqlite:///{tmp_path / 't.db'}"))
    with TestClient(application) as client:
        response = client.post(path, json=call)
    assert response.status_code == 200
    assert response.json() == {"error": {"code": "internal_error"}}

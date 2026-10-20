"""本人認可・所属の原子的更新・競合を実SQLiteで確認する。"""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from test_auth import login, register

from api.api_service.main import create_app
from config.settings import Settings
from modules.accounts.grad_checker_accounts.application.dto.profile import (
    ProgramSelection,
)
from modules.accounts.grad_checker_accounts.application.errors.profile import (
    ProfileError,
)
from modules.accounts.grad_checker_accounts.infrastructure.profile import (
    SqliteProfileUnitOfWork,
)
from modules.accounts.grad_checker_accounts.public import SaveProgramUseCase
from modules.subjects.grad_checker_subjects.infrastructure.subject_data_import import (
    SqliteSubjectDataUnitOfWork,
    load_seed,
)
from modules.subjects.grad_checker_subjects.public import ImportSubjectDataUseCase

BACKEND = Path(__file__).resolve().parents[1]


@pytest.fixture
def profile_app(tmp_path):
    app = create_app(Settings(database_url=f"sqlite:///{tmp_path / 'profile.db'}"))
    with TestClient(app) as client:
        ImportSubjectDataUseCase(
            SqliteSubjectDataUnitOfWork(app.state.database_engine)
        ).execute(load_seed(BACKEND / "seeds/cs_2026.json"))
        register(client)
        yield app, client, login(client)


def call(client, identity, operation="me", **fields):
    return client.post(
        "/bridge/profile",
        json={"operation": operation, "token": identity["session_token"], **fields},
    ).json()


def selection(client, identity, index=0, revision=0):
    option = call(client, identity, "programs")["data"]["programs"][index]
    return {
        "program_id": option["program_id"],
        "curriculum_id": option["curriculum_id"],
        "expected_revision": revision,
    }


def test_profile_persistence_and_owner_isolation(profile_app):
    _, client, identity = profile_app
    initial = call(client, identity)["data"]["profile"]
    assert initial["program_id"] is None
    assert initial["curriculum_id"] is None
    assert initial["data_revision"] == 0
    options = call(client, identity, "programs")["data"]["programs"]
    assert len(options) == 4
    assert all(p["verification_status"] == "unverified" for p in options)
    assert all(p["admission_year_from"] is None for p in options)
    chosen = selection(client, identity)
    saved = call(
        client, identity, "save_program", csrf=identity["csrf_token"], selection=chosen
    )["data"]["profile"]
    assert saved == {
        **initial,
        **{k: chosen[k] for k in ("program_id", "curriculum_id")},
        "data_revision": 1,
    }
    assert call(client, login(client))["data"]["profile"] == saved
    register(client, "student_02")
    other = login(client, username="student_02")
    assert call(client, other)["data"]["profile"]["curriculum_id"] is None
    assert (
        call(client, other, student_id=initial["student_id"])["error"]["code"]
        == "invalid_request"
    )
    assert call(client, identity)["data"]["profile"] == saved


def test_failed_save_does_not_change_profile(profile_app):
    _, client, identity = profile_app
    before = call(client, identity)["data"]["profile"]
    chosen = selection(client, identity)
    invalid = {
        **chosen,
        "program_id": selection(client, identity, index=1)["program_id"],
    }
    for fields, code in [
        ({"csrf": "x" * 64, "selection": chosen}, "invalid_csrf"),
        ({"csrf": identity["csrf_token"], "selection": invalid}, "invalid_program"),
        (
            {
                "csrf": identity["csrf_token"],
                "selection": {**chosen, "expected_revision": 10},
            },
            "revision_conflict",
        ),
        (
            {
                "csrf": identity["csrf_token"],
                "selection": {**chosen, "expected_revision": True},
            },
            "invalid_request",
        ),
    ]:
        assert call(client, identity, "save_program", **fields)["error"]["code"] == code
        assert call(client, identity)["data"]["profile"] == before
    assert (
        call(client, {"session_token": "x" * 43})["error"]["code"]
        == "invalid_credentials"
    )


def test_concurrent_revision_updates_have_only_one_winner(profile_app):
    app, client, identity = profile_app
    choices = [
        ProgramSelection(**selection(client, identity, index=i)) for i in range(2)
    ]
    student_id = identity["student"]["id"]

    def save(chosen):
        service = SaveProgramUseCase(SqliteProfileUnitOfWork(app.state.database_engine))
        try:
            return service.execute(student_id, chosen)
        except ProfileError as error:
            return error.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(save, choices))
    assert results.count("revision_conflict") == 1
    saved = call(client, identity)["data"]["profile"]
    assert saved["data_revision"] == 1
    assert saved["curriculum_id"] in [p.curriculum_id for p in choices]


def test_database_failure_rolls_back_selection_and_revision(profile_app):
    app, client, identity = profile_app
    before = call(client, identity)["data"]["profile"]
    chosen = selection(client, identity)
    with app.state.database_engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TRIGGER reject_program BEFORE UPDATE OF program_id ON students "
                "BEGIN SELECT RAISE(ABORT, 'test failure'); END"
            )
        )
    result = call(
        client, identity, "save_program", csrf=identity["csrf_token"], selection=chosen
    )
    assert result["error"]["code"] == "profile_unavailable"
    assert call(client, identity)["data"]["profile"] == before


def test_empty_master_returns_empty_choices(tmp_path):
    app = create_app(Settings(database_url=f"sqlite:///{tmp_path / 'empty.db'}"))
    with TestClient(app) as client:
        register(client)
        identity = login(client)
        assert call(client, identity, "programs")["data"]["programs"] == []

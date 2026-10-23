"""実Go API → Python → ローカルPostgreSQLで認証・成績・卒業判定を検証する。"""

import pytest

from modules.requirements.infrastructure.persistence.unit_of_work import (
    SqliteRequirementUnitOfWork,
)
from modules.requirements.public import ImportRequirementsUseCase
from modules.subjects.infrastructure.persistence.unit_of_work import (
    SqliteSubjectDataUnitOfWork,
)
from modules.subjects.public import ImportSubjectDataUseCase
from tests.e2e.test_auth_http import (
    auth_services,  # noqa: F401
)
from tests.e2e.test_auth_http import (
    test_real_registration_recovery_and_session as auth_scenario,
)
from tests.e2e.test_check_results_http import sign_in
from tests.unit.test_requirement_evaluation import grade, snapshot, uid  # noqa: F401


@pytest.fixture
def service_database_url(postgres_engine):
    return postgres_engine.url.render_as_string(hide_password=False)


def test_postgres_http_auth(auth_services, service_database_url):  # noqa: F811
    auth_scenario(auth_services)


def test_postgres_http_grade_evaluation_and_history(
    auth_services,  # noqa: F811
    service_database_url,
    postgres_engine,
    snapshot,  # noqa: F811
):
    ImportSubjectDataUseCase(SqliteSubjectDataUnitOfWork(postgres_engine)).execute(
        snapshot.subjects
    )
    ImportRequirementsUseCase(SqliteRequirementUnitOfWork(postgres_engine)).execute(
        snapshot.requirements
    )
    client = auth_services
    headers = sign_in(client, "pg_owner", snapshot)
    saved = client.put(
        "/api/me/grades",
        headers=headers,
        json={
            "expected_revision": 1,
            "grades": [grade(uid(i)).model_dump() for i in (10, 11, 13, 15)],
        },
    )
    assert saved.status_code == 200
    assert saved.json()["data_revision"] == 2
    assert client.get("/api/me/graduation-requirements").json()["result"] == "pass"
    check = client.post("/api/checks", headers=headers, json={"expected_revision": 2})
    assert check.status_code == 201
    data = check.json()
    assert data["result"]["result"] == "pass"
    assert client.get(f"/api/checks/{data['id']}").json() == data
    assert client.get("/api/checks").json()["total_count"] == 1
    assert (
        client.post(
            "/api/checks", headers=headers, json={"expected_revision": 1}
        ).status_code
        == 409
    )
    client.post("/api/auth/logout", headers=headers, json={}).raise_for_status()
    sign_in(client, "pg_other", snapshot)
    assert client.get(f"/api/checks/{data['id']}").status_code == 404

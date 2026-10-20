"""Go公開ルート・メソッド・JSON応答と、生成されたOpenAPIの契約を照合する。"""

import json
import re

import pytest
from jsonschema import Draft202012Validator, FormatChecker
from openapi_spec_validator import validate
from test_auth_http import BACKEND, PASSWORD, auth_services  # noqa: F401
from test_requirement_evaluation import snapshot  # noqa: F401

from modules.requirements.grad_checker_requirements.infrastructure.seed import (
    SqliteRequirementUnitOfWork,
)
from modules.requirements.grad_checker_requirements.public import (
    ImportRequirementsUseCase,
)
from modules.subjects.grad_checker_subjects.infrastructure.database import (
    create_database_engine,
)
from modules.subjects.grad_checker_subjects.infrastructure.subject_data_import import (
    SqliteSubjectDataUnitOfWork,
)
from modules.subjects.grad_checker_subjects.public import ImportSubjectDataUseCase
from scripts.build_openapi import OUTPUT, build_document

DOCUMENT = json.loads(OUTPUT.read_text())


def assert_contract(response, path: str, method: str = "get"):
    operation = DOCUMENT["paths"][path][method]
    documented = operation["responses"][str(response.status_code)]
    if "$ref" in documented:
        documented = DOCUMENT["components"]["responses"][
            documented["$ref"].split("/")[-1]
        ]
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["content-type"].startswith("application/json")
    schema = documented["content"]["application/json"]["schema"]
    Draft202012Validator(
        {**schema, "components": DOCUMENT["components"]},
        format_checker=FormatChecker(),
    ).validate(response.json())
    if response.status_code >= 400:
        examples = documented["content"]["application/json"]["examples"].values()
        assert response.json() in [example["value"] for example in examples]
    return response.json()


def test_generated_openapi_is_valid_and_current():
    assert DOCUMENT == build_document()
    validate(DOCUMENT)
    ids = [
        operation["operationId"]
        for item in DOCUMENT["paths"].values()
        for operation in item.values()
    ]
    assert len(ids) == len(set(ids))
    assert all(path.startswith("/api/") for path in DOCUMENT["paths"])


def test_go_route_inventory_matches_openapi():
    # 既存のGoルート宣言から収集し、新規・削除・改名を検出する。
    source = "\n".join(
        path.read_text() for path in (BACKEND / "api/presentation").glob("*.go")
    )
    routes = set(re.findall(r'"(/api/[^" ]+)"', source))
    routes.remove("/api/auth/")
    auth = (BACKEND / "api/presentation/auth.go").read_text()
    allowed = re.search(r"allowed := map\[string\]bool\{([^}]+)\}", auth)
    assert allowed is not None
    routes.update(
        "/api/auth/" + name for name in re.findall(r'"([a-z]+)": true', allowed[1])
    )
    routes.remove("/api/dev/subject-list/")
    routes.update(
        {
            "/api/dev/subject-list/programs",
            "/api/dev/subject-list/{curriculum_id}",
            "/api/checks/{id}",
        }
    )
    assert routes == set(DOCUMENT["paths"])


def test_public_methods_match_running_go(auth_services):  # noqa: F811
    client = auth_services
    for path, item in DOCUMENT["paths"].items():
        concrete = path.replace("{id}", "00000000-0000-4000-8000-000000000001").replace(
            "{curriculum_id}", "00000000-0000-4000-8000-000000000001"
        )
        for method in ("get", "post", "put", "patch", "delete", "options"):
            result = client.request(method, concrete)
            if method not in item:
                assert result.status_code == 405, (path, method, result.text)
                assert {
                    value.strip().lower()
                    for value in result.headers["allow"].split(",")
                } == set(item)
            else:
                assert result.status_code != 405, (path, method)
    assert client.get("/docs").status_code == 404
    assert client.get("/openapi.json").status_code == 404


@pytest.mark.parametrize(
    "auth_services", [["-api-docs", "-subject-list-preview"]], indirect=True
)
def test_real_public_responses_match_openapi(auth_services, tmp_path, snapshot):  # noqa: F811
    client = auth_services
    engine = create_database_engine(f"sqlite:///{tmp_path / 'auth.db'}")
    try:
        ImportSubjectDataUseCase(SqliteSubjectDataUnitOfWork(engine)).execute(
            snapshot.subjects
        )
        ImportRequirementsUseCase(SqliteRequirementUnitOfWork(engine)).execute(
            snapshot.requirements
        )
    finally:
        engine.dispose()

    assert client.get("/openapi.json").json() == DOCUMENT
    page = client.get("/docs")
    assert page.status_code == 200
    assert "persistAuthorization: false" in page.text
    assert "validatorUrl: null" in page.text
    assert_contract(client.get("/api/health"), "/api/health")
    assert_contract(client.get("/api/auth/config"), "/api/auth/config")
    assert_contract(client.get("/api/me"), "/api/me")
    credentials = {"login_name": "openapi_01", "password": PASSWORD}
    registered = assert_contract(
        client.post("/api/auth/register", json=credentials),
        "/api/auth/register",
        "post",
    )
    assert_contract(
        client.post("/api/auth/register", json=credentials),
        "/api/auth/register",
        "post",
    )
    assert_contract(client.post("/api/auth/login", json={}), "/api/auth/login", "post")
    login_response = client.post("/api/auth/login", json=credentials)
    login = assert_contract(login_response, "/api/auth/login", "post")
    assert "session_token" not in login
    assert "HttpOnly" in login_response.headers["set-cookie"]
    assert_contract(client.get("/api/auth/session"), "/api/auth/session")
    headers = {"X-CSRF-Token": login["csrf_token"]}
    assert_contract(client.get("/api/programs"), "/api/programs")
    assert_contract(client.get("/api/me/dashboard"), "/api/me/dashboard")
    assert_contract(client.put("/api/me/program", json={}), "/api/me/program", "put")
    selection = {
        "program_id": str(snapshot.program_id),
        "curriculum_id": str(snapshot.curriculum_id),
        "expected_revision": 0,
    }
    assert_contract(
        client.put("/api/me/program", json=selection, headers=headers),
        "/api/me/program",
        "put",
    )
    assert_contract(
        client.put("/api/me/program", json=selection, headers=headers),
        "/api/me/program",
        "put",
    )
    for path in (
        "/api/me",
        "/api/me/grades",
        "/api/courses",
        "/api/categories",
        "/api/me/dashboard",
        "/api/me/graduation-requirements",
        "/api/checks",
        "/api/dev/subject-list/programs",
    ):
        assert_contract(client.get(path), path)
    assert_contract(
        client.get(f"/api/dev/subject-list/{snapshot.curriculum_id}"),
        "/api/dev/subject-list/{curriculum_id}",
    )
    assert_contract(client.get("/api/courses?faculty_id=invalid"), "/api/courses")
    assert_contract(client.get("/api/checks?limit=0"), "/api/checks")
    assert_contract(client.get("/api/checks/invalid"), "/api/checks/{id}")
    assert_contract(
        client.put(
            "/api/me/grades",
            json={"expected_revision": 1, "grades": []},
            headers=headers,
        ),
        "/api/me/grades",
        "put",
    )
    saved = assert_contract(
        client.post("/api/checks", json={"expected_revision": 2}, headers=headers),
        "/api/checks",
        "post",
    )
    assert_contract(client.get(f"/api/checks/{saved['id']}"), "/api/checks/{id}")
    assert_contract(client.get("/api/checks"), "/api/checks")
    assert_contract(
        client.post("/api/checks", json={"expected_revision": 0}, headers=headers),
        "/api/checks",
        "post",
    )
    assert_contract(
        client.post("/api/checks", content="{}", headers=headers), "/api/checks", "post"
    )
    assert_contract(
        client.post(
            "/api/checks",
            content=" " * 1025,
            headers={**headers, "Content-Type": "application/json"},
        ),
        "/api/checks",
        "post",
    )
    assert_contract(
        client.post("/api/auth/logout", headers=headers), "/api/auth/logout", "post"
    )
    assert_contract(client.get("/api/auth/session"), "/api/auth/session")
    assert_contract(
        client.post(
            "/api/auth/recover",
            json={**credentials, "recovery_code": registered["recovery_code"]},
        ),
        "/api/auth/recover",
        "post",
    )

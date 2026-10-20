from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from api.api_service.main import create_app
from config.settings import Settings
from modules.subjects.grad_checker_subjects.infrastructure.subject_data_import import (
    SqliteSubjectDataUnitOfWork,
    load_seed,
)
from modules.subjects.grad_checker_subjects.public import ImportSubjectDataUseCase

SEED_PATH = Path(__file__).resolve().parents[1] / "seeds" / "cs_2026.json"
BASE = "/bridge/subject-list"


@pytest.fixture
def subject_list_client(tmp_path):
    app = create_app(
        Settings(
            database_url=f"sqlite:///{tmp_path / 'subject-list.db'}",
        )
    )
    with TestClient(app) as client:
        ImportSubjectDataUseCase(
            SqliteSubjectDataUnitOfWork(app.state.database_engine)
        ).execute(load_seed(SEED_PATH))
        yield client


def programs(client):
    return client.post(BASE, json={"operation": "list_programs"})


def subjects(client, identifier):
    return client.post(
        BASE, json={"operation": "get_subject_list", "curriculum_id": str(identifier)}
    )


def test_external_routes_are_removed(tmp_path):
    app = create_app(Settings(database_url=f"sqlite:///{tmp_path / 'bridge.db'}"))
    with TestClient(app) as client:
        assert client.get("/api/dev/subject-list/programs").status_code == 404
        assert client.get("/api/health").status_code == 404


def test_four_curricula_and_course_specific_types_are_read_from_db(subject_list_client):
    response = programs(subject_list_client)
    assert response.status_code == 200
    assert len(response.json()["data"]) == 4
    for program in response.json()["data"]:
        response = subjects(subject_list_client, program["curriculum_id"])
        assert response.status_code == 200
        result = response.json()["data"]
        social = program["specialization_name"] == "社会情報専攻"
        assert len(result["courses"]) == (120 if social else 126)
        courses = {course["name"]: course for course in result["courses"]}
        assert courses["WebプログラミングⅠ"]["course_type"] == (
            "selective" if social else "required"
        )
        assert (
            courses["線形代数Ⅰ"]["classification_path"][0]["name"] == "専門基礎教育科目"
        )
        assert courses["線形代数Ⅰ"]["classification_path"][1]["name"] == "数理"
        assert courses["コンピュータ概論Ⅰ"]["teaching_type_label"] == "講義・演習"
        assert [
            x["semester_order"]
            for x in courses["コンピュータアーキテクチャ"]["offerings"]
        ] == [3, 4, 5, 6]
        assert (
            "学年共通"
            in courses["コンピュータアーキテクチャ"]["offerings"][0]["source_note"]
        )
        assert result["program"]["verification_status"] == "unverified"
        assert result["program"]["admission_year_from"] is None


def test_response_reflects_database_not_bundled_seed(subject_list_client):
    identifier = programs(subject_list_client).json()["data"][0]["curriculum_id"]
    with subject_list_client.app.state.database_engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE courses SET name = 'DBから取得した科目' WHERE code = 'CS-C001'"
            )
        )
    response = subjects(subject_list_client, identifier)
    assert any(
        course["name"] == "DBから取得した科目"
        for course in response.json()["data"]["courses"]
    )


def test_missing_and_invalid_bridge_calls_return_codes(subject_list_client):
    missing = subjects(subject_list_client, uuid4())
    assert missing.status_code == 200
    assert missing.json() == {"error": {"code": "curriculum_not_found"}}
    invalid = subjects(subject_list_client, "invalid")
    assert invalid.json() == {"error": {"code": "invalid_request"}}
    for call in [
        {"operation": "unknown"},
        {"operation": "get_subject_list"},
        {"operation": "list_programs", "curriculum_id": str(uuid4())},
        {"operation": "list_programs", "unexpected": True},
    ]:
        assert subject_list_client.post(BASE, json=call).json() == {
            "error": {"code": "invalid_request"}
        }


def test_empty_master_and_database_failure_do_not_look_like_success(tmp_path):
    app = create_app(
        Settings(
            database_url=f"sqlite:///{tmp_path / 'empty.db'}",
        )
    )
    with TestClient(app) as client:
        assert programs(client).json() == {"data": []}
        with app.state.database_engine.begin() as connection:
            connection.execute(text("DROP TABLE curricula"))
        response = programs(client)
        assert response.status_code == 200
        assert response.json() == {"error": {"code": "subject_list_unavailable"}}

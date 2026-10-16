"""学生向け科目一覧・分類と、本人課程による分類・絞り込みを確認する。"""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from test_auth import login, register
from test_profile import selection

from api.api_service.main import create_app
from config.settings import Settings
from modules.subjects.grad_checker_subjects.infrastructure.subject_data_import import (
    import_subject_data,
    load_seed,
)

BACKEND = Path(__file__).resolve().parents[1]
SEED = json.loads((BACKEND / "seeds/cs_2026.json").read_text())


@pytest.fixture
def catalog_app(tmp_path):
    app = create_app(Settings(database_url=f"sqlite:///{tmp_path / 'catalog.db'}"))
    with TestClient(app) as client:
        import_subject_data(
            app.state.database_engine, load_seed(BACKEND / "seeds/cs_2026.json")
        )
        register(client)
        yield client, login(client)


def call(client, identity, operation="courses", **fields):
    return client.post(
        "/internal/courses",
        json={"operation": operation, "token": identity["session_token"], **fields},
    ).json()


def choose_program(client, identity):
    chosen = selection(client, identity)
    client.post(
        "/internal/profile",
        json={
            "operation": "save_program",
            "token": identity["session_token"],
            "csrf": identity["csrf_token"],
            "selection": chosen,
        },
    )
    return chosen["curriculum_id"]


def test_program_is_required(catalog_app):
    client, identity = catalog_app
    for operation in ("courses", "categories"):
        assert (
            call(client, identity, operation)["error"]["code"] == "program_not_selected"
        )
    assert (
        call(client, {"session_token": "x" * 43})["error"]["code"]
        == "invalid_credentials"
    )


def test_catalog_marks_own_curriculum_and_keeps_other_courses(catalog_app):
    client, identity = catalog_app
    curriculum_id = choose_program(client, identity)
    data = call(client, identity)["data"]
    assert data["curriculum"]["curriculum_id"] == curriculum_id
    assert data["curriculum"]["verification_status"] == "unverified"
    courses = data["courses"]
    own = {
        item["course_id"]: item
        for item in SEED["curriculum_courses"]
        if item["curriculum_id"] == curriculum_id
    }
    assert len(courses) == len(SEED["courses"])
    placed = [course for course in courses if course["placement"] is not None]
    assert {course["course_id"] for course in placed} == set(own)
    # 課程の科目表を先に並べ、科目表にない科目へ分類を推測しない。
    assert courses[: len(placed)] == placed
    for course in placed:
        expected = own[course["course_id"]]
        assert course["placement"]["course_type"] == expected["course_type"]
        assert (
            course["placement"]["classification_path"][-1]["id"]
            == expected["classification_id"]
        )
    assert all(course["offerings"] for course in placed)
    categories = call(client, identity, "categories")["data"]["categories"]
    assert {c["id"] for c in categories} == {
        c["id"] for c in SEED["classifications"] if c["curriculum_id"] == curriculum_id
    }


def test_filters_are_combined_with_and(catalog_app):
    client, identity = catalog_app
    choose_program(client, identity)
    courses = call(client, identity)["data"]["courses"]
    categories = call(client, identity, "categories")["data"]["categories"]
    root = next(c for c in categories if c["parent_id"] is None)

    def filtered(**filters):
        return call(client, identity, filters=filters)["data"]["courses"]

    in_root = filtered(category_id=root["id"])
    assert in_root
    assert all(
        root["id"] in [c["id"] for c in course["placement"]["classification_path"]]
        for course in in_root
    )
    first = filtered(semester="first")
    assert first
    assert all(any(o["term_code"] == "first" for o in c["offerings"]) for c in first)
    assert filtered(faculty="コンピュータサイエンス学部") == courses
    assert filtered(department="存在しない学科") == []
    keyword = courses[0]["name"]
    assert courses[0] in filtered(q=keyword)
    combined = filtered(category_id=root["id"], semester="first")
    assert combined == [course for course in in_root if course in first]
    assert (
        call(
            client,
            identity,
            filters={"category_id": "00000000-0000-4000-8000-000000000000"},
        )["error"]["code"]
        == "unknown_category"
    )
    for invalid in ({"semester": "summer"}, {"q": ""}, {"term": "first"}):
        assert call(client, identity, filters=invalid)["error"]["code"] == (
            "invalid_request"
        )
    assert (
        call(client, identity, "categories", filters={})["error"]["code"]
        == "invalid_request"
    )

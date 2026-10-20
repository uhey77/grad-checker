"""Go外部API → Python → SQLiteの科目一覧・成績保存・再取得。"""

from pathlib import Path

from modules.subjects.infrastructure.persistence.repositories.subject_data import (
    load_seed,
)
from modules.subjects.infrastructure.persistence.unit_of_work import (
    SqliteSubjectDataUnitOfWork,
)
from modules.subjects.public import ImportSubjectDataUseCase
from shared.infrastructure.persistence.database import create_database_engine
from tests.e2e.test_auth_http import PASSWORD, auth_services  # noqa: F401


def grade(course_id, number=1, code="A"):
    return {
        "course_id": course_id,
        "attempt_no": number,
        "result_status": "finalized" if code else "pending",
        "grade_code": code,
        "academic_year": 2026,
        "term_code": "first",
    }


def seed(tmp_path):
    engine = create_database_engine(f"sqlite:///{tmp_path / 'auth.db'}")
    try:
        ImportSubjectDataUseCase(SqliteSubjectDataUnitOfWork(engine)).execute(
            load_seed(Path(__file__).resolve().parents[2] / "seeds/cs_2026.json")
        )
    finally:
        engine.dispose()


def check_course_filters(client):
    categories = client.get("/api/categories").json()["categories"]
    root = next(c for c in categories if c["parent_id"] is None)
    filtered = client.get(
        "/api/courses", params={"category_id": root["id"], "semester": "first"}
    ).json()["courses"]
    assert filtered
    assert all(
        root["id"] in [p["id"] for p in c["placement"]["classification_path"]]
        and any(o["term_code"] == "first" for o in c["offerings"])
        for c in filtered
    )
    assert client.get("/api/courses?semester=summer").status_code == 422
    unknown_category = client.get(
        "/api/courses", params={"category_id": "00000000-0000-4000-8000-000000000000"}
    )
    assert unknown_category.status_code == 422


def check_rejected_grades(client, csrf, course_id):
    for invalid, status in [
        ([grade("00000000-0000-4000-8000-000000000000")], 400),
        ([grade(course_id), grade(course_id)], 422),
        ([grade(course_id, 1, "A"), grade(course_id, 2)], 422),
        ([{**grade(course_id), "grade_code": "R"}], 422),
    ]:
        response = client.put(
            "/api/me/grades",
            json={"expected_revision": 1, "grades": invalid},
            headers=csrf,
        )
        assert response.status_code == status, response.text
        assert response.json()["detail"]
    assert client.get("/api/me/grades").json() == {"grades": [], "data_revision": 1}


def test_real_courses_and_grades_flow(auth_services, tmp_path):  # noqa: F811
    client = auth_services
    seed(tmp_path)
    for path in ("/api/courses", "/api/categories", "/api/me/grades"):
        assert client.get(path).status_code == 401
    credentials = {"login_name": "grades_01", "password": PASSWORD}
    assert client.post("/api/auth/register", json=credentials).status_code == 201
    auth = client.post("/api/auth/login", json=credentials).json()
    csrf = {"X-CSRF-Token": auth["csrf_token"]}
    assert client.get("/api/courses").status_code == 409
    assert client.get("/api/categories").status_code == 409
    initial = client.get("/api/me/grades")
    assert initial.status_code == 200
    assert initial.headers["cache-control"] == "no-store"
    assert initial.json() == {"grades": [], "data_revision": 0}

    option = client.get("/api/programs").json()["programs"][0]
    body = {k: option[k] for k in ("program_id", "curriculum_id")}
    profile = client.put(
        "/api/me/program", json={**body, "expected_revision": 0}, headers=csrf
    )
    assert profile.json()["data_revision"] == 1
    courses = client.get("/api/courses").json()["courses"]
    outside = next(c for c in courses if c["placement"] is None)
    own = [c for c in courses if c["placement"] is not None]
    check_course_filters(client)

    grades = [
        grade(own[0]["course_id"], 1, "D"),
        grade(own[0]["course_id"], 2, "B"),
        grade(outside["course_id"], 1, None),
    ]
    request = {"expected_revision": 0, "grades": grades}
    # 所属保存で進んだ版より古い版の成績は保存しない。
    assert client.put("/api/me/grades", json=request, headers=csrf).status_code == 409
    for headers in ({}, {**csrf, "Origin": "https://evil.example"}):
        response = client.put(
            "/api/me/grades", json={**request, "expected_revision": 1}, headers=headers
        )
        assert response.status_code == 403
    check_rejected_grades(client, csrf, own[0]["course_id"])

    saved = client.put(
        "/api/me/grades", json={"expected_revision": 1, "grades": grades}, headers=csrf
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()["data_revision"] == 2
    assert len(saved.json()["grades"]) == 3
    assert client.get("/api/me/grades").json() == saved.json()
    cleared = client.put(
        "/api/me/grades", json={"expected_revision": 2, "grades": []}, headers=csrf
    )
    assert cleared.json() == {"grades": [], "data_revision": 3}
    assert client.get("/api/me").json()["data_revision"] == 3

    assert client.post("/api/auth/logout", json={}, headers=csrf).status_code == 200
    assert client.get("/api/me/grades").status_code == 401
    other = {"login_name": "grades_02", "password": PASSWORD}
    assert client.post("/api/auth/register", json=other).status_code == 201
    assert client.post("/api/auth/login", json=other).status_code == 200
    assert client.get("/api/me/grades").json() == {"grades": [], "data_revision": 0}

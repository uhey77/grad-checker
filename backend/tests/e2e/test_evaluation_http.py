"""Go → Python → SQLiteで本人の保存済み成績を判定する。実DBは変更しない。"""

from sqlalchemy import text

from modules.requirements.infrastructure.persistence.repositories.seed import (
    load_requirement_seed,
)
from modules.requirements.infrastructure.persistence.unit_of_work import (
    SqliteRequirementUnitOfWork,
)
from modules.requirements.public import ImportRequirementsUseCase
from modules.subjects.infrastructure.persistence.repositories.subject_data import (
    load_seed,
)
from modules.subjects.infrastructure.persistence.unit_of_work import (
    SqliteSubjectDataUnitOfWork,
)
from modules.subjects.public import ImportSubjectDataUseCase
from shared.infrastructure.persistence.database import create_database_engine
from tests.e2e.test_auth_http import PASSWORD, auth_services  # noqa: F401
from tests.unit.test_external_allocation import add_external, external_snapshot  # noqa: F401
from tests.unit.test_requirement_evaluation import BACKEND, grade, snapshot, uid  # noqa: F401

ENDPOINT = "/api/me/graduation-requirements"


def test_external_allocation_period_prompt_and_warning(
    auth_services,  # noqa: F811
    tmp_path,
    external_snapshot,  # noqa: F811
):
    client = auth_services
    engine = create_database_engine(f"sqlite:///{tmp_path / 'auth.db'}")
    try:
        ImportSubjectDataUseCase(SqliteSubjectDataUnitOfWork(engine)).execute(
            external_snapshot.subjects
        )
        ImportRequirementsUseCase(SqliteRequirementUnitOfWork(engine)).execute(
            external_snapshot.requirements
        )
        credentials = {"login_name": "external_check", "password": PASSWORD}
        assert client.post("/api/auth/register", json=credentials).status_code == 201
        auth = client.post("/api/auth/login", json=credentials).json()
        headers = {"X-CSRF-Token": auth["csrf_token"]}
        client.put(
            "/api/me/program",
            headers=headers,
            json={
                "program_id": str(external_snapshot.program_id),
                "curriculum_id": str(external_snapshot.curriculum_id),
                "expected_revision": 0,
            },
        ).raise_for_status()
        add_external(external_snapshot, year=None, term=None)
        saved = client.put(
            "/api/me/grades",
            headers=headers,
            json={
                "grades": [row.model_dump() for row in external_snapshot.grades],
                "expected_revision": 1,
            },
        )
        saved.raise_for_status()
        before = client.get("/api/me/grades").json()
        missing = client.get(ENDPOINT)
        assert missing.status_code == 409
        assert "履修年度・学期" in missing.json()["detail"]
        assert client.get("/api/me/grades").json() == before
        external_snapshot.grades = [
            row.model_copy(update={"academic_year": 2026, "term_code": "first"})
            for row in external_snapshot.grades
        ]
        client.put(
            "/api/me/grades",
            headers=headers,
            json={
                "grades": [row.model_dump() for row in external_snapshot.grades],
                "expected_revision": 2,
            },
        ).raise_for_status()
        result = client.get(ENDPOINT)
        assert result.status_code == 200, result.text
        assert result.json()["result"] == "pass"
        assert result.json()["warnings"] == ["provisional_external_allocation"]
        assert (
            sum(row["free_credits"] for row in result.json()["external_allocations"])
            == 2
        )
        external_snapshot.grades.pop(
            5
        )  # 第一算入先の他学部科目を1つ取り消し、合計6単位にする。
        client.put(
            "/api/me/grades",
            headers=headers,
            json={
                "grades": [row.model_dump() for row in external_snapshot.grades],
                "expected_revision": 3,
            },
        ).raise_for_status()
        result = client.get(ENDPOINT).json()
        assert result["warnings"] == []
        assert result["result"] == "pass"
    finally:
        engine.dispose()


def test_current_cs_seed_evaluates_all_curricula_without_verification_override(
    auth_services,  # noqa: F811
    tmp_path,
):
    client = auth_services
    subjects = load_seed(BACKEND / "seeds/cs_2026.json")
    requirements = load_requirement_seed(BACKEND / "seeds/cs_requirements_2026.json")
    engine = create_database_engine(f"sqlite:///{tmp_path / 'auth.db'}")
    try:
        ImportSubjectDataUseCase(SqliteSubjectDataUnitOfWork(engine)).execute(subjects)
        ImportRequirementsUseCase(SqliteRequirementUnitOfWork(engine)).execute(
            requirements
        )
        credentials = {"login_name": "current_seed", "password": PASSWORD}
        assert client.post("/api/auth/register", json=credentials).status_code == 201
        auth = client.post("/api/auth/login", json=credentials).json()
        headers = {"X-CSRF-Token": auth["csrf_token"]}
        revision = 0
        for curriculum in subjects.curricula:
            saved = client.put(
                "/api/me/program",
                headers=headers,
                json={
                    "program_id": str(curriculum.program_id),
                    "curriculum_id": str(curriculum.id),
                    "expected_revision": revision,
                },
            )
            assert saved.status_code == 200, saved.text
            revision = saved.json()["data_revision"]
            empty = client.get(ENDPOINT)
            assert empty.status_code == 200, empty.text
            data = empty.json()
            assert data["result"] == "fail"
            assert data["curriculum"]["verification_status"] == "unverified"
            assert data["curriculum"]["admission_year_from"] is None
            assert data["total"]["earned_credits"] == 0
            assert data["total"]["shortage"] == 124
            assert len(data["requirements"]) == 20
            required = next(
                row
                for row in subjects.curriculum_courses
                if row.curriculum_id == curriculum.id and row.course_type == "required"
            )
            course_credits = next(
                course.credits
                for course in subjects.courses
                if course.id == required.course_id
            )
            saved_grade = client.put(
                "/api/me/grades",
                headers=headers,
                json={
                    "expected_revision": revision,
                    "grades": [grade(required.course_id).model_dump()],
                },
            )
            assert saved_grade.status_code == 200, saved_grade.text
            revision = saved_grade.json()["data_revision"]
            result = client.get(ENDPOINT)
            assert result.status_code == 200, result.text
            data = result.json()
            assert data["data_revision"] == revision
            assert (
                data["total"]["earned_credits"]
                == data["total"]["credited_credits"]
                == course_credits
            )
            assert data["total"]["shortage"] == 124 - course_credits
            cleared = client.put(
                "/api/me/grades",
                headers=headers,
                json={"expected_revision": revision, "grades": []},
            )
            assert cleared.status_code == 200, cleared.text
            revision = cleared.json()["data_revision"]
    finally:
        engine.dispose()


def test_saved_grades_evaluation_and_owner_isolation(auth_services, tmp_path, snapshot):  # noqa: F811
    client = auth_services
    engine = create_database_engine(f"sqlite:///{tmp_path / 'auth.db'}")
    try:
        ImportSubjectDataUseCase(SqliteSubjectDataUnitOfWork(engine)).execute(
            snapshot.subjects
        )
        ImportRequirementsUseCase(SqliteRequirementUnitOfWork(engine)).execute(
            snapshot.requirements
        )
        assert client.get(ENDPOINT).status_code == 401
        credentials = {"login_name": "evaluate_01", "password": PASSWORD}
        assert client.post("/api/auth/register", json=credentials).status_code == 201
        auth = client.post("/api/auth/login", json=credentials).json()
        headers = {"X-CSRF-Token": auth["csrf_token"]}
        missing = client.get(ENDPOINT)
        assert missing.status_code == 409 and "所属" in missing.json()["detail"]
        assert client.post(ENDPOINT).status_code == 405
        assert client.get(ENDPOINT + "?student_id=other").status_code == 422
        assert (
            client.put(
                "/api/me/program",
                headers=headers,
                json={
                    "program_id": str(snapshot.program_id),
                    "curriculum_id": str(snapshot.curriculum_id),
                    "expected_revision": 0,
                },
            ).status_code
            == 200
        )
        initial = client.get(ENDPOINT)
        assert initial.status_code == 200, initial.text
        assert initial.headers["cache-control"] == "no-store"
        assert initial.json()["result"] == "fail"
        assert initial.json()["total"]["shortage"] == 10
        attempts = [grade(uid(i)).model_dump() for i in (10, 11, 13, 15)]
        assert (
            client.put(
                "/api/me/grades",
                headers=headers,
                json={
                    "expected_revision": 1,
                    "grades": attempts,
                },
            ).status_code
            == 200
        )
        before = client.get("/api/me/grades").json()
        result = client.get(ENDPOINT)
        assert result.status_code == 200, result.text
        data = result.json()
        assert data["result"] == "pass"
        assert data["data_revision"] == 2
        assert data["curriculum"]["revision"] == 3
        assert data["total"]["credited_credits"] == 10
        assert data["missing_required_courses"] == []
        assert data["evaluated_at"]
        assert len(data["requirements"]) == 7
        assert client.get(ENDPOINT).json()["result"] == "pass"
        assert client.get("/api/me/grades").json() == before
        assert (
            client.put(
                "/api/me/grades",
                headers=headers,
                json={
                    "expected_revision": 2,
                    "grades": attempts[1:],
                },
            ).status_code
            == 200
        )
        assert client.get(ENDPOINT).json()["missing_required_courses"][0][
            "course_id"
        ] == str(uid(10))
        assert (
            client.post("/api/auth/logout", json={}, headers=headers).status_code == 200
        )
        other = {"login_name": "evaluate_02", "password": PASSWORD}
        client.post("/api/auth/register", json=other)
        second = client.post("/api/auth/login", json=other).json()
        second_headers = {"X-CSRF-Token": second["csrf_token"]}
        client.put(
            "/api/me/program",
            headers=second_headers,
            json={
                "program_id": str(snapshot.program_id),
                "curriculum_id": str(snapshot.curriculum_id),
                "expected_revision": 0,
            },
        )
        assert client.get(ENDPOINT).json()["total"]["earned_credits"] == 0
        assert_configuration_errors(client, engine)
    finally:
        engine.dispose()


def assert_configuration_errors(client, engine):
    # 適用年度の未確認は判定を妨げない。設定不足・DB障害はfailと区別する。
    with engine.begin() as connection:
        connection.execute(
            text("UPDATE curricula SET verification_status='unverified'")
        )
    unverified = client.get(ENDPOINT)
    assert unverified.status_code == 200
    assert unverified.json()["result"] == "fail"
    assert unverified.json()["curriculum"]["verification_status"] == "unverified"
    with engine.begin() as connection:
        connection.execute(text("DELETE FROM requirement_scopes"))
    assert client.get(ENDPOINT).status_code == 409
    with engine.begin() as connection:
        connection.execute(text("DROP TABLE requirement_scopes"))
    failed = client.get(ENDPOINT)
    assert failed.status_code == 503
    assert "SELECT" not in failed.text

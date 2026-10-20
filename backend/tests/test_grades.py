"""本人成績の全集合置換・回次の業務ルール・競合を実SQLiteで確認する。"""

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from test_auth import login, register
from test_profile import selection

from api.api_service.main import create_app
from config.settings import Settings
from modules.grades.grad_checker_grades.application.errors.grades import GradeError
from modules.grades.grad_checker_grades.application.grades import (
    GradeRepository,
    GradeSet,
    GradeUnitOfWork,
    StudentGrades,
)
from modules.grades.grad_checker_grades.domain.grade import (
    GradeCode,
    ResultStatus,
    is_valid_attempt_sequence,
)
from modules.grades.grad_checker_grades.infrastructure.grades import (
    SqliteGradeUnitOfWork,
)
from modules.grades.grad_checker_grades.public import SaveGradesUseCase
from modules.subjects.grad_checker_subjects.infrastructure.subject_data_import import (
    SqliteSubjectDataUnitOfWork,
    load_seed,
)
from modules.subjects.grad_checker_subjects.public import ImportSubjectDataUseCase
from tests.fakes import FakeUnitOfWork

BACKEND = Path(__file__).resolve().parents[1]
SEED = json.loads((BACKEND / "seeds/cs_2026.json").read_text())
COURSES = sorted(course["id"] for course in SEED["courses"])


@pytest.fixture
def grades_app(tmp_path):
    app = create_app(Settings(database_url=f"sqlite:///{tmp_path / 'grades.db'}"))
    with TestClient(app) as client:
        ImportSubjectDataUseCase(
            SqliteSubjectDataUnitOfWork(app.state.database_engine)
        ).execute(load_seed(BACKEND / "seeds/cs_2026.json"))
        register(client)
        yield app, client, login(client)


def call(client, identity, operation="get", **fields):
    return client.post(
        "/bridge/grades",
        json={"operation": operation, "token": identity["session_token"], **fields},
    ).json()


def attempt(course=0, number=1, grade="A", year=2026, term="first"):
    return {
        "course_id": COURSES[course],
        "attempt_no": number,
        "result_status": "pending" if grade is None else "finalized",
        "grade_code": grade,
        "academic_year": year,
        "term_code": term,
    }


def save(client, identity, grades, revision):
    return call(
        client,
        identity,
        "save",
        csrf=identity["csrf_token"],
        grade_set={"expected_revision": revision, "grades": grades},
    )


def test_attempt_sequence_rules():
    finalized, pending = ResultStatus.FINALIZED, ResultStatus.PENDING
    assert is_valid_attempt_sequence([(1, finalized, GradeCode.A)])
    assert is_valid_attempt_sequence([(1, pending, None)])
    assert is_valid_attempt_sequence(
        [(1, finalized, GradeCode.D), (2, finalized, GradeCode.X), (3, pending, None)]
    )
    for invalid in (
        [(2, finalized, GradeCode.A)],
        [(1, finalized, GradeCode.D), (3, finalized, GradeCode.A)],
        [(1, finalized, GradeCode.C), (2, finalized, GradeCode.A)],
        [(1, pending, None), (2, finalized, GradeCode.A)],
    ):
        assert not is_valid_attempt_sequence(invalid)


def test_full_set_replacement_and_owner_isolation(grades_app):
    _, client, identity = grades_app
    assert call(client, identity)["data"] == {"grades": [], "data_revision": 0}
    grades = [
        attempt(1, 1, "D", 2025, "second"),
        attempt(1, 2, "A", 2026, None),
        attempt(0, 1, None, None, None),
    ]
    saved = save(client, identity, grades, 0)["data"]
    expected = sorted(grades, key=lambda g: (g["course_id"], g["attempt_no"]))
    assert saved == {"grades": expected, "data_revision": 1}
    assert call(client, login(client))["data"] == saved
    register(client, "student_02")
    other = login(client, username="student_02")
    assert call(client, other)["data"] == {"grades": [], "data_revision": 0}
    # 訂正と省略による取消を1回の全集合保存で行う。
    corrected = save(client, identity, [attempt(0, 1, "B")], 1)["data"]
    assert corrected == {"grades": [attempt(0, 1, "B")], "data_revision": 2}
    assert save(client, identity, [], 2)["data"] == {"grades": [], "data_revision": 3}
    assert call(client, identity)["data"] == {"grades": [], "data_revision": 3}


def test_invalid_grade_sets_leave_grades_unchanged(grades_app):
    _, client, identity = grades_app
    before = save(client, identity, [attempt(0, 1, "D")], 0)["data"]
    unknown = {**attempt(), "course_id": "00000000-0000-4000-8000-000000000000"}
    for grades, revision, code in [
        ([attempt(), attempt()], 1, "duplicate_attempt"),
        ([attempt(0, 2)], 1, "invalid_attempt_sequence"),
        ([attempt(0, 1, "C"), attempt(0, 2, "A")], 1, "invalid_attempt_sequence"),
        ([attempt(0, 1, None), attempt(0, 2, "A")], 1, "invalid_attempt_sequence"),
        ([unknown], 1, "unknown_course"),
        ([attempt()], 0, "revision_conflict"),
        ([{**attempt(), "grade_code": None}], 1, "invalid_request"),
        ([{**attempt(), "term_code": "summer"}], 1, "invalid_request"),
        ([{**attempt(), "academic_year": 1.5}], 1, "invalid_request"),
        ([{**attempt(), "student_id": "other"}], 1, "invalid_request"),
    ]:
        assert save(client, identity, grades, revision)["error"]["code"] == code
        assert call(client, identity)["data"] == before
    forged = call(
        client,
        identity,
        "save",
        csrf="x" * 64,
        grade_set={"expected_revision": 1, "grades": []},
    )
    assert forged["error"]["code"] == "invalid_csrf"
    assert call(client, identity)["data"] == before
    assert (
        call(client, {"session_token": "x" * 43})["error"]["code"]
        == "invalid_credentials"
    )


def test_courses_outside_own_curriculum_can_be_saved(grades_app):
    _, client, identity = grades_app
    chosen = selection(client, identity)
    profile = client.post(
        "/bridge/profile",
        json={
            "operation": "save_program",
            "token": identity["session_token"],
            "csrf": identity["csrf_token"],
            "selection": chosen,
        },
    ).json()["data"]["profile"]
    own = {
        item["course_id"]
        for item in SEED["curriculum_courses"]
        if item["curriculum_id"] == chosen["curriculum_id"]
    }
    outside = COURSES.index(next(c for c in COURSES if c not in own))
    # 所属保存と成績保存は同じdata_revisionを使い、古い版の保存を拒否する。
    assert save(client, identity, [attempt()], 0)["error"]["code"] == (
        "revision_conflict"
    )
    saved = save(client, identity, [attempt(outside)], profile["data_revision"])
    assert saved["data"]["grades"] == [attempt(outside)]
    assert saved["data"]["data_revision"] == 2


def test_unchanged_attempts_keep_updated_at(grades_app):
    app, client, identity = grades_app
    save(client, identity, [attempt(0, 1, "D"), attempt(1)], 0)
    query = text(
        "SELECT course_id, attempt_no, updated_at FROM grade_attempts "
        "ORDER BY course_id, attempt_no"
    )
    with app.state.database_engine.connect() as connection:
        first = {(r[0], r[1]): r[2] for r in connection.execute(query)}
    save(client, identity, [attempt(0, 1, "D"), attempt(0, 2, "A"), attempt(1)], 1)
    with app.state.database_engine.connect() as connection:
        second = {(r[0], r[1]): r[2] for r in connection.execute(query)}
    assert set(second) == set(first) | {(COURSES[0], 2)}
    assert all(second[key] == value for key, value in first.items())


def test_concurrent_grade_saves_have_only_one_winner(grades_app):
    app, _, identity = grades_app
    student_id = identity["student"]["id"]

    def replace(grade):
        service = SaveGradesUseCase(SqliteGradeUnitOfWork(app.state.database_engine))
        try:
            grade_set = GradeSet(expected_revision=0, grades=[attempt(0, 1, grade)])
            return service.execute(student_id, grade_set)
        except GradeError as error:
            return error.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(replace, ["A", "B"]))
    assert results.count("revision_conflict") == 1


def test_database_failure_rolls_back_grades_and_revision(grades_app):
    app, client, identity = grades_app
    before = save(client, identity, [attempt(0, 1, "D")], 0)["data"]
    with app.state.database_engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TRIGGER reject_grade BEFORE INSERT ON grade_attempts "
                "BEGIN SELECT RAISE(ABORT, 'test failure'); END"
            )
        )
    result = save(client, identity, [attempt(0, 1, "D"), attempt(0, 2, "A")], 1)
    assert result["error"]["code"] == "grades_unavailable"
    assert call(client, identity)["data"] == before


def test_database_rejects_inconsistent_grade_rows(grades_app):
    app, _, identity = grades_app
    student_id = identity["student"]["id"]
    insert = text(
        "INSERT INTO grade_attempts (id, student_id, course_id, attempt_no, "
        "result_status, grade_code, updated_at) "
        "VALUES (:id, :student, :course, :number, :status, :grade, '2026-01-01')"
    )
    for index, (number, status, grade) in enumerate(
        [(1, "finalized", None), (1, "pending", "A"), (0, "finalized", "A")]
    ):
        with pytest.raises(Exception, match="CHECK"):
            with app.state.database_engine.begin() as connection:
                connection.execute(
                    insert,
                    {
                        "id": f"bad-{index}",
                        "student": student_id,
                        "course": COURSES[0],
                        "number": number,
                        "status": status,
                        "grade": grade,
                    },
                )


class FakeGradeRepository(GradeRepository):
    def __init__(self, uow: FakeUnitOfWork) -> None:
        self.uow = uow
        self.replaced: list[GradeSet] = []

    def get_grades(self, student_id: str) -> StudentGrades:
        self.uow.require_block()
        return StudentGrades(grades=[], data_revision=0)

    def replace_grades(self, student_id: str, grade_set: GradeSet) -> StudentGrades:
        self.uow.require_block()
        if grade_set.expected_revision != 0:
            raise GradeError("revision_conflict")
        self.replaced.append(grade_set)
        return StudentGrades(grades=grade_set.grades, data_revision=1)


class FakeGradeUnitOfWork(FakeUnitOfWork, GradeUnitOfWork):
    def __init__(self) -> None:
        super().__init__()
        self.repository = FakeGradeRepository(self)

    @property
    def grades(self) -> FakeGradeRepository:
        return self.repository


def test_invalid_attempt_sequence_is_rejected_before_the_transaction():
    uow = FakeGradeUnitOfWork()
    grades = [attempt(0, 1, "A"), attempt(0, 2, "B")]
    with pytest.raises(GradeError, match="invalid_attempt_sequence"):
        SaveGradesUseCase(uow).execute(
            "student",
            GradeSet.model_validate({"expected_revision": 0, "grades": grades}),
        )
    assert uow.events == []


def test_grade_replacement_commits_or_rolls_back_as_one_write():
    uow = FakeGradeUnitOfWork()
    service = SaveGradesUseCase(uow)
    grades = [attempt(0, 1, "A")]
    saved = service.execute(
        "student", GradeSet.model_validate({"expected_revision": 0, "grades": grades})
    )
    assert saved.data_revision == 1
    with pytest.raises(GradeError, match="revision_conflict"):
        service.execute(
            "student",
            GradeSet.model_validate({"expected_revision": 5, "grades": grades}),
        )
    assert uow.events == ["write", "commit", "write", "rollback"]

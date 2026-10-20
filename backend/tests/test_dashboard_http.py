"""概要の読取り、保存版の更新、本人分離と設定障害を実HTTPで確認する。"""

from concurrent.futures import ThreadPoolExecutor

import httpx
from sqlalchemy import text
from test_auth_http import (
    PASSWORD,
    auth_services,  # noqa: F401 -- pytest fixture or shared test data
)
from test_requirement_evaluation import (
    grade,
    snapshot,  # noqa: F401 -- pytest fixture or shared test data
    uid,
)

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

ENDPOINT = "/api/me/dashboard"


def test_dashboard_snapshot_read_only_and_errors(auth_services, tmp_path, snapshot):  # noqa: F811
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
        credentials = {"login_name": "dashboard_01", "password": PASSWORD}
        client.post("/api/auth/register", json=credentials).raise_for_status()
        login = client.post("/api/auth/login", json=credentials).json()
        headers = {"X-CSRF-Token": login["csrf_token"]}
        missing = client.get(ENDPOINT)
        assert missing.status_code == 409 and "所属" in missing.json()["detail"]
        assert client.post(ENDPOINT).status_code == 405
        assert client.get(ENDPOINT + "?student_id=other").status_code == 422
        client.put(
            "/api/me/program",
            headers=headers,
            json={
                "program_id": str(snapshot.program_id),
                "curriculum_id": str(snapshot.curriculum_id),
                "expected_revision": 0,
            },
        ).raise_for_status()
        empty = client.get(ENDPOINT)
        assert empty.status_code == 200, empty.text
        assert empty.headers["cache-control"] == "no-store"
        initial = empty.json()
        assert initial["grade_count"] == 0 and initial["result"] == "fail"
        assert initial["total"]["earned_credits"] == 0
        assert initial["total"]["shortage"] == 10
        assert initial["data_revision"] == 1
        assert initial["curriculum_revision"] == initial["curriculum"]["revision"] == 3
        assert "requirements" not in initial and "courses" not in initial
        assert initial["categories"][0]["result"] == "fail"
        # 概要の取得と成績保存が重なっても、版・件数・単位が混在しない。
        attempts = [grade(uid(i)).model_dump() for i in (10, 11, 13, 15)]
        with httpx.Client(
            base_url=str(client.base_url), cookies=client.cookies
        ) as reader:
            with ThreadPoolExecutor(max_workers=2) as pool:
                reading = pool.submit(reader.get, ENDPOINT)
                saving = pool.submit(
                    client.put,
                    "/api/me/grades",
                    headers=headers,
                    json={"expected_revision": 1, "grades": attempts},
                )
                saving.result().raise_for_status()
                racing = reading.result()
        assert racing.status_code == 200, racing.text
        data = racing.json()
        assert (
            data["data_revision"],
            data["grade_count"],
            data["total"]["earned_credits"],
        ) in {
            (1, 0, 0),
            (2, 4, 10),
        }
        for _ in range(3):
            response = client.get(ENDPOINT)
            response.raise_for_status()
            result = response.json()
            assert result["result"] == "pass" and result["grade_count"] == 4
            assert result["data_revision"] == 2
            assert result["total"]["credited_credits"] == 10
            assert result["categories"][0]["result"] == "pass"
        assert_read_only(client, headers, result)
        assert_other_owner_and_errors(client, engine, headers, snapshot)
    finally:
        engine.dispose()


def assert_read_only(client, headers, result):
    detail = client.get("/api/me/graduation-requirements").json()
    for field in (
        "result",
        "total",
        "categories",
        "data_revision",
        "curriculum",
        "rule_revisions",
        "warnings",
    ):
        assert result[field] == detail[field]
    assert client.get("/api/checks").json()["total_count"] == 0
    # 保存済み履歴がある状態でもGETは件数・内容を変えない。
    saved = client.post("/api/checks", headers=headers, json={"expected_revision": 2})
    saved.raise_for_status()
    old = saved.json()
    assert client.get(ENDPOINT).json()["result"] == "pass"
    assert client.get("/api/checks").json()["total_count"] == 1
    assert client.get("/api/checks/" + old["id"]).json() == old
    before = client.get("/api/me/grades").json()
    client.get(ENDPOINT).raise_for_status()
    assert client.get("/api/me/grades").json() == before


def assert_other_owner_and_errors(client, engine, headers, source):
    client.post("/api/auth/logout", headers=headers, json={}).raise_for_status()
    other = {"login_name": "dashboard_02", "password": PASSWORD}
    client.post("/api/auth/register", json=other).raise_for_status()
    auth = client.post("/api/auth/login", json=other).json()
    client.put(
        "/api/me/program",
        headers={"X-CSRF-Token": auth["csrf_token"]},
        json={
            "program_id": str(source.program_id),
            "curriculum_id": str(source.curriculum_id),
            "expected_revision": 0,
        },
    ).raise_for_status()
    assert client.get(ENDPOINT).json()["grade_count"] == 0
    assert client.get(ENDPOINT).json()["total"]["earned_credits"] == 0
    with engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE credit_rules SET verification_status='unverified', "
                "unresolved_reason='test pending rule'"
            )
        )
    # 未確認規則が必要ない成績0件では停止せず、超過換算が必要な場合だけ止める。
    assert client.get(ENDPOINT).status_code == 200
    client.put(
        "/api/me/grades",
        headers={"X-CSRF-Token": auth["csrf_token"]},
        json={
            "expected_revision": 1,
            "grades": [grade(uid(i)).model_dump() for i in (11, 12)],
        },
    ).raise_for_status()
    assert client.get(ENDPOINT).status_code == 409
    with engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE credit_rules SET verification_status='verified', "
                "unresolved_reason=NULL"
            )
        )
        connection.execute(text("DELETE FROM requirement_scopes"))
    assert client.get(ENDPOINT).status_code == 409
    with engine.begin() as connection:
        connection.execute(text("DROP TABLE requirement_scopes"))
    failed = client.get(ENDPOINT)
    assert failed.status_code == 503 and "SELECT" not in failed.text
    assert "result" not in failed.json()

"""追加シードからGo公開APIと本人専用の修了判定履歴までを実プロセスで検証する。"""

from sqlalchemy import text
from test_auth_http import PASSWORD, auth_services  # noqa: F401
from test_university_curricula import masters, snapshot_for  # noqa: F401

from modules.requirements.grad_checker_requirements.application.seed_import import (
    import_requirements,
)
from modules.requirements.grad_checker_requirements.infrastructure.seed import (
    SqliteRequirementUnitOfWork,
)
from modules.subjects.grad_checker_subjects.application.subject_data_import import (
    import_subject_data,
)
from modules.subjects.grad_checker_subjects.infrastructure.database import (
    create_database_engine,
)
from modules.subjects.grad_checker_subjects.infrastructure.subject_data_import import (
    SqliteSubjectDataUnitOfWork,
)


def test_complete_seed_to_owner_only_completion_snapshot(
    auth_services,  # noqa: F811
    tmp_path,
    masters,  # noqa: F811
):
    client = auth_services
    engine = create_database_engine(f"sqlite:///{tmp_path / 'auth.db'}")
    subjects, requirements = masters
    try:
        import_subject_data(SqliteSubjectDataUnitOfWork(engine), subjects)
        import_requirements(SqliteRequirementUnitOfWork(engine), requirements)
        assert not any(
            import_subject_data(SqliteSubjectDataUnitOfWork(engine), subjects).values()
        )
        assert not any(
            import_requirements(
                SqliteRequirementUnitOfWork(engine), requirements
            ).values()
        )
        s = snapshot_for(masters, "GR-CS-M", earned=True, answers=True)
        credentials = {"login_name": "completion_owner", "password": PASSWORD}
        assert client.post("/api/auth/register", json=credentials).status_code == 201
        auth = client.post("/api/auth/login", json=credentials).json()
        headers = {"X-CSRF-Token": auth["csrf_token"]}
        programs = client.get("/api/programs").json()["programs"]
        assert len(programs) == 38
        selected = next(
            p for p in programs if p["curriculum_id"] == str(s.curriculum_id)
        )
        assert selected["completion_policy"]["degree_level"] == "master"
        assert len(selected["completion_policy"]["non_credit_conditions"]) == 5
        assert (
            client.put(
                "/api/me/program",
                headers=headers,
                json={
                    "program_id": str(s.program_id),
                    "curriculum_id": str(s.curriculum_id),
                    "expected_revision": 0,
                },
            ).status_code
            == 200
        )
        assert (
            client.put(
                "/api/me/grades",
                headers=headers,
                json={
                    "expected_revision": 1,
                    "grades": [g.model_dump() for g in s.grades],
                },
            ).status_code
            == 200
        )
        assert (
            client.get("/api/me/graduation-requirements").json()["result"] == "pending"
        )
        payload = {
            "expected_revision": 2,
            "completion_answers": [a.model_dump() for a in s.completion_answers],
        }
        assert client.post("/api/checks", json=payload).status_code == 403
        saved = client.post("/api/checks", headers=headers, json=payload)
        assert saved.status_code == 201, saved.text
        saved = saved.json()
        assert saved["result"]["result"] == "pass"
        assert saved["input"]["completion_answers"] == payload["completion_answers"]
        assert all(
            c["status"] == "met" for c in saved["result"]["completion_conditions"]
        )
        assert client.get("/api/checks").json()["checks"][0]["result"] == "pass"
        assert client.get("/api/checks/" + saved["id"]).json() == saved
        payload["completion_answers"] = []
        pending = client.post("/api/checks", headers=headers, json=payload)
        assert pending.status_code == 201, pending.text
        assert pending.json()["result"]["result"] == "pending"
        assert client.get("/api/checks").json()["checks"][0]["result"] == "pending"
        assert (
            client.post(
                "/api/checks", headers=headers, json={**payload, "expected_revision": 1}
            ).status_code
            == 409
        )
        # マスタを変更しても過去の根拠・回答・結果は保存時のまま。
        with engine.begin() as connection:
            connection.execute(
                text("UPDATE completion_policies SET source_pages='test changed'")
            )
        assert client.get("/api/checks/" + saved["id"]).json() == saved
        assert_unsupported_program_stops(
            client, programs, headers, snapshot_for(masters, "HS-CE")
        )
        other = {"login_name": "completion_other", "password": PASSWORD}
        client.post("/api/auth/register", json=other).raise_for_status()
        client.post("/api/auth/login", json=other).raise_for_status()
        assert client.get("/api/checks/" + saved["id"]).status_code == 404
        assert client.get("/api/checks").json()["total_count"] == 0
    finally:
        engine.dispose()


def assert_unsupported_program_stops(client, programs, headers, unsupported):
    # 科目資料の年度が一致しない課程は、所属は選べても確定判定を作らない。
    assert (
        client.put(
            "/api/me/program",
            headers=headers,
            json={
                "program_id": str(unsupported.program_id),
                "curriculum_id": str(unsupported.curriculum_id),
                "expected_revision": 2,
            },
        ).status_code
        == 200
    )
    blocked = client.post("/api/checks", headers=headers, json={"expected_revision": 3})
    assert blocked.status_code == 409
    assert "未確認事項" in blocked.json()["detail"]
    reason = next(
        p for p in programs if p["curriculum_id"] == str(unsupported.curriculum_id)
    )["completion_policy"]["unresolved_reasons"]
    assert "2024" in " ".join(reason)
    assert client.get("/api/checks").json()["total_count"] == 2

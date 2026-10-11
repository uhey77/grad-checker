from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.config import Settings
from app.infrastructure.subject_data_import import load_seed, import_subject_data
from app.main import create_app

SEED_PATH = Path(__file__).resolve().parents[1] / "seeds" / "cs_2026.json"
BASE = "/api/dev/course-catalog"


@pytest.fixture
def catalog_client(tmp_path):
    app = create_app(
        Settings(
            database_url=f"sqlite:///{tmp_path / 'catalog.db'}",
            enable_subject_list_preview=True,
        )
    )
    with TestClient(app) as client:
        import_subject_data(app.state.database_engine, load_seed(SEED_PATH))
        yield client


def test_preview_is_disabled_by_default(tmp_path):
    app = create_app(Settings(database_url=f"sqlite:///{tmp_path / 'disabled.db'}"))
    with TestClient(app) as client:
        assert client.get(f"{BASE}/programs").status_code == 404
        assert client.get(f"{BASE}/{uuid4()}").status_code == 404
        assert client.post(f"{BASE}/programs").status_code == 405


def test_four_curricula_and_course_specific_types_are_read_from_db(catalog_client):
    programs = catalog_client.get(f"{BASE}/programs")
    assert programs.status_code == 200
    assert programs.headers["cache-control"] == "no-store"
    assert len(programs.json()) == 4
    for program in programs.json():
        response = catalog_client.get(f"{BASE}/{program['curriculum_id']}")
        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        result = response.json()
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


def test_response_reflects_database_not_bundled_seed(catalog_client):
    identifier = catalog_client.get(f"{BASE}/programs").json()[0]["curriculum_id"]
    with catalog_client.app.state.database_engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE courses SET name = 'DBから取得した科目' WHERE code = 'CS-C001'"
            )
        )
    response = catalog_client.get(f"{BASE}/{identifier}")
    assert any(
        course["name"] == "DBから取得した科目" for course in response.json()["courses"]
    )


def test_missing_and_invalid_curriculum_are_japanese_errors(catalog_client):
    missing = catalog_client.get(f"{BASE}/{uuid4()}")
    assert missing.status_code == 404
    assert missing.json() == {"detail": "選択したカリキュラムが見つかりません。"}
    invalid = catalog_client.get(f"{BASE}/invalid")
    assert invalid.status_code == 422
    assert invalid.json() == {"detail": "カリキュラムIDの形式が不正です。"}


def test_empty_master_and_database_failure_do_not_look_like_success(tmp_path):
    app = create_app(
        Settings(
            database_url=f"sqlite:///{tmp_path / 'empty.db'}",
            enable_subject_list_preview=True,
        )
    )
    with TestClient(app) as client:
        assert client.get(f"{BASE}/programs").json() == []
        with app.state.database_engine.begin() as connection:
            connection.execute(text("DROP TABLE curricula"))
        response = client.get(f"{BASE}/programs")
        assert response.status_code == 503
        assert isinstance(response.json()["detail"], str)
        assert "SELECT" not in response.json()["detail"]

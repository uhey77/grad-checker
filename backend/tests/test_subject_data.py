import json
import os
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from modules.subjects.grad_checker_subjects.application.errors.subject_data import (
    SeedError,
)
from modules.subjects.grad_checker_subjects.application.subject_data_validation import (
    SubjectDataSeed,
)
from modules.subjects.grad_checker_subjects.infrastructure.database import (
    create_database_engine,
    create_database_schema,
)
from modules.subjects.grad_checker_subjects.infrastructure.subject_data_import import (
    import_subject_data,
    load_seed,
)

BACKEND = Path(__file__).resolve().parents[1]
SEED_PATH = BACKEND / "seeds" / "cs_2026.json"


@pytest.fixture
def seed():
    return load_seed(SEED_PATH)


@pytest.fixture
def engine(tmp_path):
    database = create_database_engine(f"sqlite:///{tmp_path / 'test.db'}")
    create_database_schema(database)
    try:
        yield database
    finally:
        database.dispose()


def counts(engine):
    with engine.connect() as connection:
        return {
            name: connection.execute(text(f"SELECT count(*) FROM {name}")).scalar_one()
            for name in SubjectDataSeed.model_fields
        }


def test_cs_seed_matches_handbook_programs_and_required_credits(seed):
    programs = {program.id: program for program in seed.academic_programs}
    courses = {course.id: course for course in seed.courses}
    classifications = {item.id: item for item in seed.classifications}
    assert len(seed.courses) == 131
    assert len(seed.curricula) == 4
    assert all(course.credits > 0 for course in seed.courses)
    for curriculum in seed.curricula:
        program = programs[curriculum.program_id]
        associations = [
            item
            for item in seed.curriculum_courses
            if item.curriculum_id == curriculum.id
        ]
        social = program.code == "CS-SOCIAL"
        assert len(associations) == (120 if social else 126)
        required = Counter()
        types = {}
        for association in associations:
            course = courses[association.course_id]
            types[course.name] = association.course_type
            if association.course_type == "required":
                root = classifications[association.classification_id].code.split(".")[0]
                required[root] += course.credits
        # 冊子94の必修小計（先進情報58 / 社会情報55）と一致。
        assert required == {
            "general": 16,
            "foundation": 18 if social else 21,
            "specialized": 21,
        }
        assert types["WebプログラミングⅠ"] == ("selective" if social else "required")
        assert types["データ分析プログラミング"] == (
            "selective" if social else "elective"
        )
        assert types["データベース"] == ("elective" if social else "selective")
        assert types["人工知能"] == (
            "selective" if program.code == "CS-ADV-AI" else "elective"
        )
        assert types["インターネット"] == (
            "selective" if program.code == "CS-ADV-INFRA" else "elective"
        )
        assert types["ヒューマンインターフェイス"] == (
            "selective" if program.code == "CS-ADV-HUMAN" else "elective"
        )
        assert curriculum.verification_status == "unverified"
        assert curriculum.admission_year_from is None


def test_offerings_and_original_teaching_labels_are_preserved(seed):
    courses = {course.name: course for course in seed.courses}

    def offerings(name):
        return [
            item for item in seed.course_offerings if item.course_id == courses[name].id
        ]

    assert [x.semester_order for x in offerings("コンピュータアーキテクチャ")] == [
        3,
        4,
        5,
        6,
    ]
    assert [x.semester_order for x in offerings("集中実技Ⅱ")] == [3]
    assert all("学年共通" in x.source_note for x in offerings("データベース"))
    assert "クォーター" in offerings("生成AI活用入門")[0].source_note
    assert "GPA2.9" in offerings("社会情報専門演習Ⅰ")[0].source_note
    assert courses["コンピュータ概論Ⅰ"].teaching_type_label == "講義・演習"
    assert courses["集中実技Ⅰ"].teaching_type_label == "実技"


def test_seed_is_persistent_idempotent_and_handles_child_before_parent(engine, seed):
    reversed_seed = seed.model_copy(
        update={"classifications": list(reversed(seed.classifications))}
    )
    result = import_subject_data(engine, reversed_seed)
    assert result == {
        name: len(getattr(seed, name)) for name in SubjectDataSeed.model_fields
    }
    before = counts(engine)
    assert import_subject_data(engine, seed) == dict.fromkeys(
        SubjectDataSeed.model_fields, 0
    )
    assert counts(engine) == before
    # 新しいエンジンでも同じファイルに保存されている。
    reopened = create_database_engine(str(engine.url))
    try:
        assert counts(reopened) == before
    finally:
        reopened.dispose()


@pytest.mark.parametrize("credit_value", [0, -1, 1.5, 2.0, True, "2"])
def test_json_rejects_non_positive_or_coerced_credits(seed, credit_value):
    data = seed.model_dump(mode="json")
    data["courses"][0]["credits"] = credit_value
    with pytest.raises(ValidationError):
        SubjectDataSeed.model_validate(data)


@pytest.mark.parametrize(
    "case",
    [
        "duplicate",
        "unknown-course",
        "cross-curriculum",
        "cycle",
        "bad-level",
        "year-range",
        "verified-without-year",
        "duplicate-code",
    ],
)
def test_invalid_master_is_rejected_without_any_saved_rows(engine, seed, case):
    data = seed.model_dump(mode="json")
    if case == "duplicate":
        data["courses"].append(data["courses"][0].copy())
    elif case == "unknown-course":
        data["course_offerings"][0]["course_id"] = str(uuid4())
    elif case == "cross-curriculum":
        data["curriculum_courses"][0]["classification_id"] = data["classifications"][
            17
        ]["id"]
    elif case == "cycle":
        data["classifications"][0]["parent_id"] = data["classifications"][1]["id"]
    elif case == "bad-level":
        data["classifications"][1]["level"] = 3
    elif case == "year-range":
        data["curricula"][0].update(admission_year_from=2026, admission_year_to=2025)
    elif case == "verified-without-year":
        data["curricula"][0]["verification_status"] = "verified"
    elif case == "duplicate-code":
        data["courses"][1]["code"] = data["courses"][0]["code"]
    with pytest.raises(SeedError):
        import_subject_data(engine, SubjectDataSeed.model_validate(data))
    assert counts(engine) == dict.fromkeys(SubjectDataSeed.model_fields, 0)


def test_existing_conflict_is_not_overwritten_and_new_rows_are_not_added(engine, seed):
    import_subject_data(engine, seed)
    data = seed.model_dump(mode="json")
    data["academic_programs"].append(
        {"id": str(uuid4()), "code": "NEW", "faculty_name": "追加学部"}
    )
    data["courses"][0]["credits"] = 10
    before = counts(engine)
    with pytest.raises(SeedError, match="既存データ"):
        import_subject_data(engine, SubjectDataSeed.model_validate(data))
    assert counts(engine) == before
    with engine.connect() as connection:
        assert (
            connection.execute(
                text("SELECT credits FROM courses WHERE code = 'CS-C001'")
            ).scalar_one()
            == 2
        )


def test_incremental_seed_can_reference_existing_master(engine, seed):
    import_subject_data(engine, seed)
    data = {name: [] for name in SubjectDataSeed.model_fields}
    course = seed.courses[0].model_dump(mode="json")
    course.update(id=str(uuid4()), code="NEW-COURSE", name="テスト用の追加科目")
    data["courses"] = [course]
    assert (
        import_subject_data(engine, SubjectDataSeed.model_validate(data))["courses"]
        == 1
    )
    assert counts(engine)["courses"] == len(seed.courses) + 1


def test_save_failure_rolls_back_preceding_tables(engine, seed):
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TRIGGER test_failure BEFORE INSERT ON courses "
                "BEGIN SELECT RAISE(ABORT, 'test failure'); END"
            )
        )
    with pytest.raises(SeedError, match="全件の変更を取り消しました"):
        import_subject_data(engine, seed)
    assert counts(engine) == dict.fromkeys(SubjectDataSeed.model_fields, 0)


@pytest.mark.parametrize("invalid", [0, -2, 1.5, "invalid"])
def test_database_itself_rejects_invalid_credits(engine, seed, invalid):
    import_subject_data(engine, seed)
    with engine.begin() as connection:
        with pytest.raises(IntegrityError):
            connection.execute(
                text("UPDATE courses SET credits = :credits WHERE code = 'CS-C001'"),
                {"credits": invalid},
            )


def test_database_enforces_same_curriculum_references_restrict_and_nullable_uniqueness(
    engine, seed
):
    import_subject_data(engine, seed)
    root = str(seed.classifications[0].id)
    child = str(seed.classifications[1].id)
    foreign_root = str(seed.classifications[17].id)
    with engine.begin() as connection:
        for statement, parameters in (
            (
                "UPDATE classifications SET parent_id = :foreign WHERE id = :child",
                {"foreign": foreign_root, "child": child},
            ),
            (
                "UPDATE curriculum_courses SET classification_id = :foreign "
                "WHERE classification_id = :root",
                {"foreign": foreign_root, "root": child},
            ),
            ("DELETE FROM classifications WHERE id = :root", {"root": root}),
            ("UPDATE courses SET teaching_type = 'unknown'", {}),
            (
                "INSERT INTO course_offerings "
                "(id, course_id, term_code, semester_order, "
                "academic_year, source_note) "
                "SELECT 'new-id', course_id, term_code, semester_order, "
                "academic_year, source_note FROM course_offerings LIMIT 1",
                {},
            ),
        ):
            with pytest.raises(IntegrityError):
                connection.execute(text(statement), parameters)


def test_cli_and_japanese_input_errors(tmp_path):
    db = tmp_path / "cli.db"
    environment = dict(os.environ, DATABASE_URL=f"sqlite:///{db}")
    command = [sys.executable, "-m", "scripts.seed_subjects", "--file", str(SEED_PATH)]
    first = subprocess.run(
        command,
        cwd=BACKEND,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert first.returncode == 0, first.stderr
    assert '"courses": 131' in first.stdout
    second = subprocess.run(
        command,
        cwd=BACKEND,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert second.returncode == 0, second.stderr
    assert '"courses": 0' in second.stdout
    invalid = tmp_path / "invalid.json"
    invalid.write_text('{"unexpected": true}', encoding="utf-8")
    failure = subprocess.run(
        command[:-1] + [str(invalid)],
        cwd=BACKEND,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert failure.returncode == 1
    assert "シードの形式・型・値が不正" in failure.stderr
    invalid.write_text("{broken", encoding="utf-8")
    with pytest.raises(SeedError, match="形式・型・値"):
        load_seed(invalid)
    with pytest.raises(SeedError, match="読み込めません"):
        load_seed(tmp_path / "missing.json")


def test_seed_regeneration_is_reproducible(tmp_path):
    # リポジトリのシードを書き換えず、コピーした生成元とスクリプトで再現性を検証。
    for filename in ("cs_2026.source.json", "build_cs_seed.py"):
        shutil.copyfile(BACKEND / "seeds" / filename, tmp_path / filename)
    result = subprocess.run(
        [sys.executable, str(tmp_path / "build_cs_seed.py")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads((tmp_path / "cs_2026.json").read_text()) == json.loads(
        SEED_PATH.read_text()
    )

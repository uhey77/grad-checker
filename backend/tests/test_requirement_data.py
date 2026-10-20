"""CS4課程の出典整合、集合検証、DB制約、原子的な投入とCLIを確認する。"""

import json
import os
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import event, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.schema import CreateTable
from sqlmodel import Session, SQLModel, select

from modules.requirements.grad_checker_requirements.application.errors.seed import (
    RequirementSeedError,
)
from modules.requirements.grad_checker_requirements.application.seed import (
    RequirementSeed,
)
from modules.requirements.grad_checker_requirements.application.validation import (
    validate_requirements,
)
from modules.requirements.grad_checker_requirements.infrastructure import (
    cs_2026_revision,
)
from modules.requirements.grad_checker_requirements.infrastructure.models import (
    CreditRule,
)
from modules.requirements.grad_checker_requirements.infrastructure.schema import (
    create_requirement_schema,
)
from modules.requirements.grad_checker_requirements.infrastructure.seed import (
    SqliteRequirementUnitOfWork,
    load_requirement_seed,
)
from modules.requirements.grad_checker_requirements.public import (
    ImportRequirementsUseCase,
)
from modules.subjects.grad_checker_subjects.infrastructure.database import (
    create_database_engine,
    create_database_schema,
)
from modules.subjects.grad_checker_subjects.infrastructure.subject_data_import import (
    SqliteSubjectDataUnitOfWork,
    load_seed,
)
from modules.subjects.grad_checker_subjects.public import ImportSubjectDataUseCase
from seeds.build_cs_requirements_seed import build_seed

BACKEND = Path(__file__).resolve().parents[1]
SEED = BACKEND / "seeds/cs_requirements_2026.json"
SOURCE = BACKEND / "seeds/cs_requirements_2026.source.json"
SUBJECTS = BACKEND / "seeds/cs_2026.json"


@pytest.fixture
def seed():
    return load_requirement_seed(SEED)


@pytest.fixture
def subjects():
    return load_seed(SUBJECTS)


@pytest.fixture
def engine(tmp_path, subjects):
    database = create_database_engine(f"sqlite:///{tmp_path / 'requirements.db'}")
    create_database_schema(database)
    ImportSubjectDataUseCase(SqliteSubjectDataUnitOfWork(database)).execute(subjects)
    create_requirement_schema(database)
    try:
        yield database
    finally:
        database.dispose()


def counts(engine):
    with engine.connect() as connection:
        return {
            name: connection.execute(text(f"SELECT count(*) FROM {name}")).scalar_one()
            for name in RequirementSeed.model_fields
        }


def test_four_curricula_match_page_94(seed, subjects):
    # 固定の期待値は冊子94の2表を画像で照合。生成処理から算出しない。
    expected_groups = {
        "general.combined.selective": 10,
        "general.language.selective": 2,
        "general.information-math.selective": 2,
        "specialized.core.selective": 12,
        "specialized.experiment.selective": 3,
        "general.humanities.minimum": 2,
        "general.social.minimum": 2,
    }
    assert len(seed.graduation_requirements) == 80
    for curriculum in subjects.curricula:
        rows = {
            row.code: row
            for row in seed.graduation_requirements
            if row.curriculum_id == curriculum.id
        }
        assert len(rows) == 20
        assert rows["total"].required_credits == 124
        assert [
            rows[root + ".total"].required_credits
            for root in ("general", "foundation", "specialized")
        ] == [38, 42, 44]
        assert [
            rows[root + ".elective"].required_credits
            for root in ("general", "foundation", "specialized")
        ] == [8, 3, 8]
        social = curriculum.code.startswith("CS-SOCIAL")
        assert [
            rows[root + ".required"].required_credits
            for root in ("general", "foundation", "specialized")
        ] == [16, 18 if social else 21, 21]
        assert [
            rows["foundation." + group + ".selective"].required_credits
            for group in ("math", "management", "computer-business")
        ] == ([2, 4, 15] if social else [4, 2, 12])
        for code, value in expected_groups.items():
            assert rows[code].required_credits == value
        assert curriculum.verification_status == "unverified"
        assert curriculum.admission_year_from is None
    validate_requirements(seed, subjects)


def test_source_subtotals_and_required_group_cells_match_subjects(subjects):
    source = json.loads(SOURCE.read_text())
    old_source = json.loads((BACKEND / "seeds/cs_2026.source.json").read_text())
    assert source["sha256"] == old_source["sha256"]
    classes = {row.id: row.code for row in subjects.classifications}
    courses = {row.id: row for row in subjects.courses}
    for major in source["majors"].values():
        for key in ("required", "selective", "elective", "total"):
            assert (
                sum(section[key] for section in major["sections"])
                == major["totals"][key]
            )
        for section in major["sections"]:
            assert sum(row[1] or 0 for row in section["rows"]) == section["required"]
            assert sum(row[2] or 0 for row in section["rows"]) == section["selective"]
            for program in major["programs"]:
                curriculum = next(
                    x
                    for x in subjects.curricula
                    if x.code == program + "-HANDBOOK-2026"
                )
                for groups, required, _ in section["rows"]:
                    actual = sum(
                        courses[row.course_id].credits
                        for row in subjects.curriculum_courses
                        if row.curriculum_id == curriculum.id
                        and row.course_type == "required"
                        and classes[row.classification_id] in groups
                    )
                    assert actual == (required or 0)


def test_rules_preserve_unresolved_cases_and_single_shared_limit(seed):
    assert len(seed.credit_rules) == 16
    assert Counter(row.verification_status for row in seed.credit_rules) == {
        "verified": 12,
        "unverified": 4,
    }
    for rule in seed.credit_rules:
        if rule.code == "general.overflow":
            assert rule.verification_status == "verified"
            assert rule.unresolved_reason is None
            assert rule.revision == 2
        if rule.kind == "other_faculty":
            assert rule.verification_status == "unverified"
            assert rule.allocation_policy == "chronological_best_fit_v1"
            assert "大学規則として未確認" in rule.unresolved_reason
            assert not [x for x in seed.credit_rule_courses if x.rule_id == rule.id]
            limits = [x for x in seed.credit_rule_limits if x.rule_id == rule.id]
            assert len(limits) == 1 and limits[0].max_credits == 6


def test_generated_seed_is_reproducible():
    assert build_seed(
        json.loads(SOURCE.read_text()), json.loads(SUBJECTS.read_text())
    ) == json.loads(SEED.read_text())


def test_revision_updates_only_exact_old_rules_and_preserves_other_data(engine, seed):
    expected = {str(row.id): row.model_dump(mode="json") for row in seed.credit_rules}
    for previous, current in cs_2026_revision.REVISIONS:
        assert current == expected[str(current["id"])]
        index = next(
            i
            for i, row in enumerate(seed.credit_rules)
            if str(row.id) == previous["id"]
        )
        seed.credit_rules[index] = type(seed.credit_rules[index]).model_validate(
            previous
        )
    ImportRequirementsUseCase(SqliteRequirementUnitOfWork(engine)).execute(seed)
    before = counts(engine)
    # 独自編集した旧規則を勝手に置き換えない。
    customized = cs_2026_revision.REVISIONS[0][0]["id"]
    with engine.begin() as connection:
        connection.execute(
            text("UPDATE credit_rules SET source_note='独自の確認記録' WHERE id=:id"),
            {"id": customized},
        )
    create_requirement_schema(engine)
    create_requirement_schema(engine)
    with Session(engine) as session:
        for rule in session.exec(select(CreditRule)).all():
            if rule.id == customized:
                assert rule.revision == 1 and rule.source_note == "独自の確認記録"
            else:
                assert rule.model_dump() == expected[rule.id]
    assert counts(engine) == before


def test_legacy_schema_adds_policy_column_and_migrates_atomically(tmp_path, subjects):
    engine = create_database_engine(f"sqlite:///{tmp_path / 'legacy.db'}")
    try:
        create_database_schema(engine)
        ImportSubjectDataUseCase(SqliteSubjectDataUnitOfWork(engine)).execute(subjects)
        ddl = str(CreateTable(SQLModel.metadata.tables["credit_rules"]).compile(engine))
        ddl = re.sub(r"\s*allocation_policy VARCHAR,?", "", ddl)
        ddl = re.sub(r"\s*CHECK \(allocation_policy[^\n]+\n", "", ddl)
        with engine.begin() as connection:
            connection.execute(text(ddl))
            old = {
                key: value
                for key, value in cs_2026_revision.REVISIONS[0][0].items()
                if key != "allocation_policy"
            }
            connection.execute(
                text(
                    "INSERT INTO credit_rules ("
                    + ",".join(old)
                    + ") VALUES ("
                    + ",".join(":" + key for key in old)
                    + ")"
                ),
                old,
            )
        create_requirement_schema(engine)
        with engine.connect() as connection:
            row = (
                connection.execute(text("SELECT * FROM credit_rules")).mappings().one()
            )
            assert dict(row) == cs_2026_revision.REVISIONS[0][1]
    finally:
        engine.dispose()


def test_persistent_idempotent_and_parent_order_independent(engine, seed):
    seed.graduation_requirements.reverse()
    assert ImportRequirementsUseCase(SqliteRequirementUnitOfWork(engine)).execute(
        seed
    ) == {name: len(getattr(seed, name)) for name in RequirementSeed.model_fields}
    before = counts(engine)
    assert ImportRequirementsUseCase(SqliteRequirementUnitOfWork(engine)).execute(
        seed
    ) == dict.fromkeys(RequirementSeed.model_fields, 0)
    create_requirement_schema(engine)
    reopened = create_database_engine(str(engine.url))
    try:
        assert counts(reopened) == before
    finally:
        reopened.dispose()


@pytest.mark.parametrize("value", [-1, 1.5, 2.0, True, "2"])
def test_strict_integer_values(seed, value):
    for table, field in (
        ("graduation_requirements", "required_credits"),
        ("credit_rules", "revision"),
        ("credit_rule_limits", "max_credits"),
    ):
        data = seed.model_dump(mode="json")
        data[table][0][field] = value
        with pytest.raises(ValidationError):
            RequirementSeed.model_validate(data)


@pytest.mark.parametrize(
    "field,value",
    [("unknown", 1), ("kind", "unknown"), ("source_pages", "  "), ("id", "bad-id")],
)
def test_unknown_fields_and_invalid_contract(seed, field, value):
    data = seed.model_dump(mode="json")
    data["graduation_requirements"][0][field] = value
    with pytest.raises(ValidationError):
        RequirementSeed.model_validate(data)


def test_exactly_one_scope_and_reason_required(seed):
    data = seed.model_dump(mode="json")
    data["requirement_scopes"][0]["classification_id"] = None
    with pytest.raises(ValidationError):
        RequirementSeed.model_validate(data)
    data = seed.model_dump(mode="json")
    next(row for row in data["credit_rules"] if row["kind"] == "other_faculty")[
        "unresolved_reason"
    ] = None
    with pytest.raises(ValidationError):
        RequirementSeed.model_validate(data)


@pytest.mark.parametrize(
    "mutation",
    [
        "duplicate",
        "cross_curriculum",
        "cycle",
        "missing_course",
        "missing_scope",
        "wrong_required",
        "overlap",
        "cross_overflow",
        "missing_limit",
        "duplicate_limit",
        "unknown_rule",
    ],
)
def test_invalid_graph_rejected_without_writes(engine, seed, mutation):
    rows = seed.graduation_requirements
    if mutation == "duplicate":
        rows.append(rows[0])
    elif mutation == "cross_curriculum":
        rows[1].classification_id = rows[21].classification_id
    elif mutation == "cycle":
        rows[1].parent_id = rows[1].id
    elif mutation == "missing_course":
        next(x for x in seed.requirement_scopes if x.course_id).course_id = uuid4()
    elif mutation == "missing_scope":
        seed.requirement_scopes = [
            x for x in seed.requirement_scopes if x.requirement_id != rows[2].id
        ]
    elif mutation == "wrong_required":
        rows[2].required_credits += 1
    elif mutation == "overlap":
        scope = seed.requirement_scopes[0]
        seed.requirement_scopes.append(scope.model_copy(update={"id": uuid4()}))
    elif mutation == "cross_overflow":
        mapping = seed.credit_rule_courses[0]
        mapping.target_classification_id = next(
            x.classification_id
            for x in rows
            if x.curriculum_id == mapping.curriculum_id and x.code == "foundation.total"
        )
    elif mutation == "missing_limit":
        seed.credit_rule_limits.pop()
    elif mutation == "duplicate_limit":
        seed.credit_rule_limits.append(
            seed.credit_rule_limits[0].model_copy(
                update={"id": uuid4(), "limit_group_code": "second-limit"}
            )
        )
    elif mutation == "unknown_rule":
        seed.credit_rule_courses[0].rule_id = uuid4()
    with pytest.raises(RequirementSeedError):
        ImportRequirementsUseCase(SqliteRequirementUnitOfWork(engine)).execute(seed)
    assert counts(engine) == dict.fromkeys(RequirementSeed.model_fields, 0)


def test_existing_changes_rejected_and_omitted_rows_preserved(engine, seed):
    ImportRequirementsUseCase(SqliteRequirementUnitOfWork(engine)).execute(seed)
    before = counts(engine)
    empty = RequirementSeed.model_validate(
        {name: [] for name in RequirementSeed.model_fields}
    )
    assert ImportRequirementsUseCase(SqliteRequirementUnitOfWork(engine)).execute(
        empty
    ) == dict.fromkeys(RequirementSeed.model_fields, 0)
    seed.graduation_requirements[0].required_credits += 1
    with pytest.raises(RequirementSeedError, match="既存データ"):
        ImportRequirementsUseCase(SqliteRequirementUnitOfWork(engine)).execute(seed)
    assert counts(engine) == before
    with engine.connect() as connection:
        assert (
            connection.execute(
                text(
                    "SELECT required_credits FROM graduation_requirements "
                    "WHERE code = 'total'"
                )
            )
            .scalars()
            .all()
            == [124] * 4
        )


def test_db_failure_mid_import_rolls_back_all_tables(engine, seed):
    def fail_on_rules(_connection, _cursor, statement, parameters, _context, _many):
        if statement.startswith("INSERT INTO credit_rules"):
            raise IntegrityError(statement, parameters, Exception("injected failure"))

    event.listen(engine, "before_cursor_execute", fail_on_rules)
    try:
        with pytest.raises(RequirementSeedError, match="全件"):
            ImportRequirementsUseCase(SqliteRequirementUnitOfWork(engine)).execute(seed)
    finally:
        event.remove(engine, "before_cursor_execute", fail_on_rules)
    assert counts(engine) == dict.fromkeys(RequirementSeed.model_fields, 0)


@pytest.mark.parametrize(
    "sql",
    [
        "UPDATE graduation_requirements SET required_credits = -1 WHERE code = 'total'",
        "UPDATE graduation_requirements SET required_credits = 1.5 "
        "WHERE code = 'total'",
        "UPDATE credit_rule_limits SET max_credits = -1",
        "UPDATE credit_rules SET unresolved_reason = NULL "
        "WHERE verification_status = 'unverified'",
        "UPDATE requirement_scopes SET classification_id = NULL, course_id = NULL",
        "DELETE FROM graduation_requirements WHERE code = 'total'",
    ],
)
def test_database_constraints(engine, seed, sql):
    ImportRequirementsUseCase(SqliteRequirementUnitOfWork(engine)).execute(seed)
    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(text(sql))


def test_database_rejects_cross_curriculum_links(engine, seed):
    ImportRequirementsUseCase(SqliteRequirementUnitOfWork(engine)).execute(seed)
    other = seed.graduation_requirements[21].classification_id
    own = seed.graduation_requirements[1].id
    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE graduation_requirements SET classification_id = :other "
                "WHERE id = :own"
            ),
            {"other": str(other), "own": str(own)},
        )


def test_cli_requires_subjects_and_can_repeat(tmp_path):
    env = {**os.environ, "DATABASE_URL": f"sqlite:///{tmp_path / 'cli.db'}"}

    def run(module, path):
        return subprocess.run(
            [sys.executable, "-m", module, "--file", str(path)],
            cwd=BACKEND,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

    missing = run("scripts.seed_requirements", SEED)
    assert missing.returncode == 1 and "カリキュラム" in missing.stderr
    assert "Traceback" not in missing.stderr
    assert run("scripts.seed_subjects", SUBJECTS).returncode == 0
    first = run("scripts.seed_requirements", SEED)
    assert first.returncode == 0, first.stderr
    second = run("scripts.seed_requirements", SEED)
    assert second.returncode == 0, second.stderr
    assert '"graduation_requirements": 0' in second.stdout


def test_load_errors_are_actionable(tmp_path):
    with pytest.raises(RequirementSeedError, match="読み込めません"):
        load_requirement_seed(tmp_path / "missing.json")
    path = tmp_path / "bad.json"
    path.write_text('{"graduation_requirements": false}')
    with pytest.raises(RequirementSeedError, match="形式・型・値"):
        load_requirement_seed(path)

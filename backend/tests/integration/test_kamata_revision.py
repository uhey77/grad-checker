"""既存の本人データを含むDBで、既知の3規則だけを原子的に改訂する。"""

import json
import sqlite3

import pytest

from migrations.kamata_2026_revision import (
    FINGERPRINTS,
    JSON_FIELDS,
    SEED,
    fingerprint,
    revise,
)


def make_old_database(path):
    policies = [
        p
        for p in json.loads(SEED.read_text())["completion_policies"]
        if p["id"] in FINGERPRINTS
    ]
    reasons = {
        "e8dd1658-ee80-57f6-8bae-96ec543f68af": (
            "2026年公開の教育課程表本文は2024年度入学生用。"
            "2026年度の看護師・保健師経路の科目集合・必須選択条件を確認する必要がある。"
        ),
        "fcc2a500-cf3f-5783-93fe-fb5d89329183": (
            "2026年公開の教育課程表本文は2024年度入学生用・基礎必修12単位、"
            "2026年度卒業要件表は基礎必修20単位で不一致。2026年度科目集合の確認が必要。"
        ),
        "9caecb7f-29a3-50d4-b50e-de43c54dc04e": (
            "2026年公開の教育課程表本文は2024年度入学生用。"
            "2026年度の看護師・保健師経路の科目集合・必須選択条件を確認する必要がある。"
        ),
    }
    with sqlite3.connect(path) as db:
        fields = list(policies[0])
        db.execute(
            "CREATE TABLE completion_policies ("
            + ",".join(f'"{f}" TEXT' for f in fields)
            + ")"
        )
        db.execute("CREATE TABLE student_data (value TEXT)")
        db.execute("INSERT INTO student_data VALUES ('unchanged')")
        for policy in policies:
            policy.update(
                catalog_status="unverified",
                requirements_status="unverified",
                rules_status="unverified",
                unresolved_reasons=[reasons[policy["id"]]],
                credit_minimums=[],
            )
            assert fingerprint(policy) == FINGERPRINTS[policy["id"]][0]
            values = [
                json.dumps(policy[f], ensure_ascii=False)
                if f in JSON_FIELDS
                else policy[f]
                for f in fields
            ]
            db.execute(
                "INSERT INTO completion_policies VALUES ("
                + ",".join("?" for _ in fields)
                + ")",
                values,
            )


def test_revise_only_known_rows_and_allow_repeat(tmp_path):
    database = tmp_path / "test.db"
    make_old_database(database)
    assert revise(database) == 3
    assert revise(database) == 0
    with sqlite3.connect(database) as db:
        assert db.execute("SELECT value FROM student_data").fetchone() == ("unchanged",)
        assert db.execute(
            "SELECT count(*) FROM completion_policies WHERE catalog_status='verified'"
        ).fetchone() == (3,)


def test_unexpected_existing_policy_rolls_back_all_rows(tmp_path):
    database = tmp_path / "test.db"
    make_old_database(database)
    with sqlite3.connect(database) as db:
        db.execute(
            "UPDATE completion_policies SET source_pages = 'custom' WHERE id = ?",
            (next(iter(FINGERPRINTS)),),
        )
    with pytest.raises(ValueError, match="一致しません"):
        revise(database)
    with sqlite3.connect(database) as db:
        assert db.execute(
            "SELECT count(*) FROM completion_policies WHERE catalog_status='unverified'"
        ).fetchone() == (3,)

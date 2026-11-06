"""照合した蒲田3課程の規則だけを、指定された開発用SQLiteで更新する。"""

import argparse
import hashlib
import json
import sqlite3
from pathlib import Path

SEED = (
    Path(__file__).resolve().parents[1] / "seeds" / "university_requirements_2026.json"
)
FINGERPRINTS = {
    "e8dd1658-ee80-57f6-8bae-96ec543f68af": (
        "d920da558c0a70e78c1e64c719e0f5cefa35ae1ba9c3dca29380fe5e3ca3be74",
        "cb6536b618e6899b96864414654c7ff008a6b7ad9e2e7d3026ad75f50ec6bf6f",
    ),
    "fcc2a500-cf3f-5783-93fe-fb5d89329183": (
        "5e5cf3d708420dc92ea9c999a282d44ddb8cce0b464008f2b3cf9e2e33309fb3",
        "16ac3b86131acae6873ff8a0d61498b6236f9a3f932f4920ac1247f24749ef22",
    ),
    "9caecb7f-29a3-50d4-b50e-de43c54dc04e": (
        "bcae93d131bbe1d1756f5d8924822ca465efc386c4834f75455f7fc7f0b30d19",
        "e4a410d14fc3a3e821e43c22d7bd6f0e6e67a0e949647b5a750a69344e54f6c2",
    ),
}
JSON_FIELDS = (
    "unresolved_reasons",
    "credit_groups",
    "non_credit_conditions",
    "credit_minimums",
)


def fingerprint(value: dict) -> str:
    data = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(data.encode()).hexdigest()


def revise(database: Path) -> int:
    if not database.is_file():
        raise ValueError("既存のSQLiteファイルを指定してください。")
    seed = json.loads(SEED.read_text())
    policies = {
        p["id"]: p for p in seed["completion_policies"] if p["id"] in FINGERPRINTS
    }
    if set(policies) != set(FINGERPRINTS) or any(
        fingerprint(policies[key]) != hashes[1] for key, hashes in FINGERPRINTS.items()
    ):
        raise ValueError("改訂先データが照合済みの内容と一致しません。")
    connection = sqlite3.connect(f"file:{database.resolve()}?mode=rw", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("BEGIN IMMEDIATE")
        updates = []
        for key, (old_hash, new_hash) in FINGERPRINTS.items():
            row = connection.execute(
                "SELECT * FROM completion_policies WHERE id = ?", (key,)
            ).fetchone()
            if row is None:
                raise ValueError("改訂対象の課程が不足しています。")
            current = dict(row)
            for field in JSON_FIELDS:
                current[field] = json.loads(current[field])
            actual = fingerprint(current)
            if actual == new_hash:
                continue
            if actual != old_hash:
                raise ValueError("既存の課程規則が照合済みの旧データと一致しません。")
            updates.append(policies[key])
        for policy in updates:
            connection.execute(
                "UPDATE completion_policies SET catalog_status=?, "
                "requirements_status=?, "
                "rules_status=?, unresolved_reasons=?, credit_minimums=? WHERE id=?",
                (
                    policy["catalog_status"],
                    policy["requirements_status"],
                    policy["rules_status"],
                    json.dumps(policy["unresolved_reasons"], ensure_ascii=False),
                    json.dumps(policy["credit_minimums"], ensure_ascii=False),
                    policy["id"],
                ),
            )
        connection.commit()
        return len(updates)
    except BaseException:
        connection.rollback()
        raise
    finally:
        connection.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database", type=Path, required=True, help="開発用SQLiteのパス"
    )
    args = parser.parse_args()
    print(f"改訂した課程数: {revise(args.database)}")


if __name__ == "__main__":
    main()

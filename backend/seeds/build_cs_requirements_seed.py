"""冊子94・53の照合済み転記と科目シードから、CS4課程の要件シードを生成する。"""

import json
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

DIRECTORY = Path(__file__).resolve().parent


def identity(kind: str, code: str) -> str:
    return str(uuid5(NAMESPACE_URL, f"grad-checker:{kind}:{code}"))


def build_seed(source: dict, subjects: dict) -> dict:
    seed: dict[str, list] = {
        name: []
        for name in (
            "graduation_requirements",
            "requirement_scopes",
            "credit_rules",
            "credit_rule_courses",
            "credit_rule_limits",
        )
    }
    programs = {row["code"]: row["id"] for row in subjects["academic_programs"]}
    for major in source["majors"].values():
        for program in major["programs"]:
            curriculum = next(
                row
                for row in subjects["curricula"]
                if row["program_id"] == programs[program]
            )
            build_curriculum(seed, source, subjects, major, curriculum)
    return seed


def build_curriculum(
    seed: dict, source: dict, subjects: dict, major: dict, curriculum: dict
) -> None:
    curriculum_id = curriculum["id"]
    classes = {
        row["code"]: row
        for row in subjects["classifications"]
        if row["curriculum_id"] == curriculum_id
    }
    class_codes = {row["id"]: row["code"] for row in classes.values()}
    associations = [
        row
        for row in subjects["curriculum_courses"]
        if row["curriculum_id"] == curriculum_id
    ]

    def courses(group_codes: list[str], course_type: str) -> list[str]:
        return sorted(
            row["course_id"]
            for row in associations
            if row["course_type"] == course_type
            and any(
                class_codes[row["classification_id"]] == code
                or class_codes[row["classification_id"]].startswith(code + ".")
                for code in group_codes
            )
        )

    def requirement(  # noqa: PLR0917 - 表の条件・親・対象を同じ順序で指定する
        code: str,
        name: str,
        kind: str,
        credit_value: int,
        parent: str | None,
        classification: str | None,
        targets: list[str],
        target_kind: str,
    ) -> None:
        requirement_id = identity("requirement", curriculum_id + ":" + code)
        seed["graduation_requirements"].append(
            {
                "id": requirement_id,
                "curriculum_id": curriculum_id,
                "code": code,
                "name": name,
                "kind": kind,
                "required_credits": credit_value,
                "parent_id": identity("requirement", curriculum_id + ":" + parent)
                if parent
                else None,
                "classification_id": classes[classification]["id"]
                if classification
                else None,
                "display_order": sum(
                    row["curriculum_id"] == curriculum_id
                    for row in seed["graduation_requirements"]
                ),
                "source_document": source["document"],
                "source_pages": "冊子94 / PDF96",
            }
        )
        for target in targets:
            target_id = (
                classes[target]["id"] if target_kind == "classification" else target
            )
            seed["requirement_scopes"].append(
                {
                    "id": identity(
                        "requirement-scope",
                        requirement_id + ":" + target_kind + ":" + target_id,
                    ),
                    "curriculum_id": curriculum_id,
                    "requirement_id": requirement_id,
                    "classification_id": target_id
                    if target_kind == "classification"
                    else None,
                    "course_id": target_id if target_kind == "course" else None,
                }
            )

    roots = [section["classification"] for section in major["sections"]]
    requirement(
        "total",
        "総必要単位",
        "total",
        major["totals"]["total"],
        None,
        None,
        roots,
        "classification",
    )
    for section in major["sections"]:
        root = section["classification"]
        name = classes[root]["name"]
        requirement(
            root + ".total",
            name + "合計",
            "classification_total",
            section["total"],
            "total",
            root,
            [root],
            "classification",
        )
        requirement(
            root + ".required",
            name + "の必修",
            "required_courses",
            section["required"],
            root + ".total",
            root,
            courses([root], "required"),
            "course",
        )
        requirement(
            root + ".elective",
            name + "の選択",
            "elective_total",
            section["elective"],
            root + ".total",
            root,
            [root],
            "classification",
        )
        for groups, _, selective in section["rows"]:
            if selective is None:
                continue
            group_code = groups[0] if len(groups) == 1 else root + ".combined"
            group_name = "・".join(classes[group]["name"] for group in groups)
            requirement(
                group_code + ".selective",
                group_name + "の選択必修",
                "selective_group",
                selective,
                root + ".total",
                groups[0] if len(groups) == 1 else root,
                courses(groups, "selective"),
                "course",
            )
            for group in groups:
                if group in source["subminimums"]:
                    requirement(
                        group + ".minimum",
                        classes[group]["name"] + "の内訳最低単位",
                        "subminimum",
                        source["subminimums"][group],
                        group_code + ".selective",
                        group,
                        courses([group], "selective"),
                        "course",
                    )
        rule_id = identity("credit-rule", curriculum_id + ":overflow:" + root)
        seed["credit_rules"].append(
            {
                "id": rule_id,
                "curriculum_id": curriculum_id,
                "code": root + ".overflow",
                "kind": "selective_overflow",
                "verification_status": "unverified"
                if root == "general"
                else "verified",
                "source_document": source["document"],
                "source_pages": "冊子94注1・注2 / PDF96",
                "source_note": source["notes"]["overflow"],
                "unresolved_reason": source["unresolved_overflow"]
                if root == "general"
                else None,
                "revision": 1,
            }
        )
        seed["credit_rule_courses"].extend(
            {
                "curriculum_id": curriculum_id,
                "rule_id": rule_id,
                "course_id": course,
                "target_classification_id": classes[root]["id"],
            }
            for course in courses([root], "selective")
        )
    other = source["other_faculty"]
    rule_id = identity("credit-rule", curriculum_id + ":other-faculty")
    seed["credit_rules"].append(
        {
            "id": rule_id,
            "curriculum_id": curriculum_id,
            "code": "other-faculty",
            "kind": "other_faculty",
            "verification_status": "unverified",
            "source_document": source["document"],
            "source_pages": "冊子53(5) / PDF55",
            "source_note": other["summary"],
            "unresolved_reason": other["unresolved_reason"],
            "revision": 1,
        }
    )
    seed["credit_rule_limits"].append(
        {
            "id": identity("credit-rule-limit", rule_id + ":shared"),
            "rule_id": rule_id,
            "limit_group_code": "other-faculty-shared",
            "max_credits": other["max_credits"],
        }
    )


def main() -> None:
    source = json.loads(
        (DIRECTORY / "cs_requirements_2026.source.json").read_text(encoding="utf-8")
    )
    subjects = json.loads((DIRECTORY / "cs_2026.json").read_text(encoding="utf-8"))
    result = build_seed(source, subjects)
    (DIRECTORY / "cs_requirements_2026.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()

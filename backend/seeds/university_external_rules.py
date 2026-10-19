"""八王子4学部共通規則のうち、科目表で一意に照合できる講義だけを列挙する。"""

import json
from collections import defaultdict
from pathlib import Path

FACULTIES = {"応用生物学部", "コンピュータサイエンス学部", "メディア学部", "工学部"}


def add_external_rules(subjects: dict, requirements: dict, identity) -> None:
    directory = Path(__file__).resolve().parent
    cs_subjects = json.loads((directory / "cs_2026.json").read_text())
    cs_requirements = json.loads((directory / "cs_requirements_2026.json").read_text())
    programs = {
        p["id"]: p
        for p in cs_subjects["academic_programs"] + subjects["academic_programs"]
    }
    curricula = cs_subjects["curricula"] + subjects["curricula"]
    classes = {
        c["id"]: c for c in cs_subjects["classifications"] + subjects["classifications"]
    }
    placements = defaultdict(list)
    for row in cs_subjects["curriculum_courses"] + subjects["curriculum_courses"]:
        placements[row["course_id"]].append(row)
    candidates = eligible_courses(
        programs, classes, placements, cs_subjects["courses"] + subjects["courses"]
    )
    existing_rules = {
        r["curriculum_id"]: r
        for r in cs_requirements["credit_rules"]
        if r["kind"] == "other_faculty"
    }
    template = next(iter(existing_rules.values()))
    for curriculum in curricula:
        owner = programs[curriculum["program_id"]]
        if owner["faculty_name"] not in FACULTIES:
            continue
        roots = {
            c["name"]: c["id"]
            for c in classes.values()
            if c["curriculum_id"] == curriculum["id"] and c["parent_id"] is None
        }
        if "専門教育科目" not in roots:
            continue
        mappings = []
        existing = existing_rules.get(curriculum["id"])
        rule_id = (
            existing["id"]
            if existing
            else identity("credit-rule", curriculum["code"] + ":other-faculty")
        )
        for course, source, category in candidates:
            if source["faculty_name"] == owner["faculty_name"] and (
                not owner["department_name"]
                or source["department_name"] == owner["department_name"]
            ):
                continue
            target = (
                roots.get("専門基礎教育科目")
                if category == "foundation"
                else roots.get("専門教育科目")
            )
            # 工学部の専門基礎は専門教育の内側に分類される。
            if target is None and owner["faculty_name"] == "工学部":
                target = roots["専門教育科目"]
            if target is None:
                continue
            mappings.append(
                dict(
                    curriculum_id=curriculum["id"],
                    rule_id=rule_id,
                    course_id=course["id"],
                    target_classification_id=target,
                )
            )
        if not mappings:
            continue
        if not existing:
            requirements["credit_rules"].append(
                dict(template, id=rule_id, curriculum_id=curriculum["id"])
            )
            requirements["credit_rule_limits"].append(
                dict(
                    id=identity("credit-limit", rule_id),
                    rule_id=rule_id,
                    limit_group_code="other-faculty-common",
                    max_credits=6,
                )
            )
        requirements["credit_rule_courses"].extend(mappings)


def eligible_courses(
    programs: dict, classes: dict, placements: dict, courses: list
) -> list:
    candidates = []
    for course in courses:
        owner = programs[course["offering_program_id"]]
        if (
            owner["faculty_name"] not in FACULTIES
            or course["teaching_type"] != "lecture"
        ):
            continue
        # コースのいずれかで必修になる科目や分類が一意でない科目は推測しない。
        if any(p["course_type"] == "required" for p in placements[course["id"]]):
            continue
        categories = set()
        for placement in placements[course["id"]]:
            current = classes[placement["classification_id"]]
            path = []
            while current:
                path.append(current["name"])
                current = classes.get(current["parent_id"])
            if "専門基礎教育科目" in path or "専門基礎" in path:
                categories.add("foundation")
            elif "専門教育科目" in path:
                categories.add("specialized")
            else:
                categories.add("general")
        if len(categories) != 1 or "general" in categories:
            continue
        candidates.append((course, owner, next(iter(categories))))
    return candidates

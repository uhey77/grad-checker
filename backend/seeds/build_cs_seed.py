"""照合用の表転記からシードを再生成する。PDFライブラリは不要。

backendから python seeds/build_cs_seed.py で実行する。
source.jsonのcellsはPDF表の各セル（結合セルはnull）を保持している。
"""

import json
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

DIRECTORY = Path(__file__).resolve().parent


def identity(kind: str, code: str) -> str:
    return str(uuid5(NAMESPACE_URL, f"grad-checker:{kind}:{code}"))


def clean(value: str) -> str:
    return value.replace("\x08", " ").replace("\n", "").strip()


def main() -> None:
    source = json.loads((DIRECTORY / "cs_2026.source.json").read_text(encoding="utf-8"))
    seed = {
        key: []
        for key in (
            "academic_programs",
            "curricula",
            "classifications",
            "courses",
            "course_offerings",
            "curriculum_courses",
        )
    }
    # CS/CS-ADVは共通科目の開講元。選択用カリキュラムは末端4課程のみ。
    programs = (
        ("CS", None, None),
        ("CS-ADV", "先進情報専攻", None),
        ("CS-ADV-INFRA", "先進情報専攻", "情報基盤コース"),
        ("CS-ADV-HUMAN", "先進情報専攻", "人間情報コース"),
        ("CS-ADV-AI", "先進情報専攻", "人工知能コース"),
        ("CS-SOCIAL", "社会情報専攻", None),
    )
    selections = [code for code, _, _ in programs[2:]]
    for code, major, course in programs:
        seed["academic_programs"].append(
            {
                "id": identity("program", code),
                "code": code,
                "faculty_name": "コンピュータサイエンス学部",
                "department_name": None,
                "specialization_name": major,
                "course_name": course,
            }
        )
        if code in selections:
            seed["curricula"].append(
                {
                    "id": identity("curriculum", code + "-HANDBOOK-2026"),
                    "program_id": identity("program", code),
                    "code": code + "-HANDBOOK-2026",
                    "name": "2026年度便覧掲載 " + (course or major),
                    "revision": 1,
                    "admission_year_from": None,
                    "admission_year_to": None,
                    "source_document": source["document"],
                    "source_pages": "冊子83,85-88,94 / PDF85,87-90,96"
                    if code != "CS-SOCIAL"
                    else "冊子83-84,89-92,94 / PDF85-86,91-94,96",
                    "verification_status": "unverified",
                }
            )

    groups = (
        (
            "general",
            "実学基礎科目",
            (
                ("comprehensive", "総合"),
                ("humanities", "人文"),
                ("social", "社会"),
                ("science", "自然科学"),
                ("wellbeing", "ウェルビーイング"),
                ("language", "外国語"),
                ("information-math", "情報・数理"),
                ("career", "社会人基礎"),
                ("community", "社会連携"),
            ),
        ),
        (
            "foundation",
            "専門基礎教育科目",
            (
                ("math", "数理"),
                ("management", "マネジメント"),
                ("computer-business", "コンピュータ・ビジネス"),
            ),
        ),
        (
            "specialized",
            "専門教育科目",
            (
                ("core", "コア科目"),
                ("experiment", "実験・総合"),
            ),
        ),
    )
    group_codes = {}
    for program in selections:
        curriculum_id = identity("curriculum", program + "-HANDBOOK-2026")
        for order, (root_code, root_name, children) in enumerate(groups):
            root_id = identity("classification", program + ":" + root_code)
            seed["classifications"].append(
                {
                    "id": root_id,
                    "curriculum_id": curriculum_id,
                    "code": root_code,
                    "name": root_name,
                    "parent_id": None,
                    "level": 0,
                    "display_order": order,
                }
            )
            for child_order, (child_code, child_name) in enumerate(children):
                code = root_code + "." + child_code
                group_codes[child_name] = code
                seed["classifications"].append(
                    {
                        "id": identity("classification", program + ":" + code),
                        "curriculum_id": curriculum_id,
                        "code": code,
                        "name": child_name,
                        "parent_id": root_id,
                        "level": 1,
                        "display_order": child_order,
                    }
                )

    course_types = {
        "必": "required",
        "選必": "selective",
        "選": "elective",
        "": "elective",
    }
    teaching_types = {
        "講義": "lecture",
        "演習": "exercise",
        "実習": "practice",
        "実験": "experiment",
        "実技": "other",
        "講義・演習": "other",
    }
    by_name = {}
    offering_keys = {}
    for page in source["pages"]:
        booklet = page["booklet_page"]
        for order, entry in enumerate(page["rows"]):
            row = entry["cells"]
            name = clean(row[1]).replace("（※）", "")
            label = clean(row[-1]).replace(" ", "")
            credits = int(row[3])
            # 同学部の両専攻表の共通科目だけを照合して共有する。
            if name not in by_name:
                code = f"CS-C{len(by_name) + 1:03}"
                offering_program = "CS"
                if name.startswith("先進情報"):
                    offering_program = "CS-ADV"
                elif name.startswith("社会情報"):
                    offering_program = "CS-SOCIAL"
                course = {
                    "id": identity("course", code),
                    "code": code,
                    "name": name,
                    "credits": credits,
                    "offering_program_id": identity("program", offering_program),
                    "teaching_type": teaching_types[label],
                    "teaching_type_label": label,
                }
                by_name[name] = course
                seed["courses"].append(course)
            course = by_name[name]
            if (course["credits"], course["teaching_type_label"]) != (credits, label):
                raise ValueError(f"共通科目の単位または授業形態が一致しません: {name}")
            start = 8 if booklet == 88 else 5
            for slot, cell in enumerate(row[start : start + 8], start=1):
                if not cell:
                    continue
                mark = clean(cell)
                note = (
                    "担当教員の指示に従う（○）"
                    if "○" in mark
                    else "週時限数: " + mark.rstrip("*")
                )
                if "*" in mark:
                    note += (
                        "。クォーター開講（＊）"
                        if name == "生成AI活用入門"
                        else "。学年共通開講（＊）"
                    )
                if "（※）" in clean(row[1]):
                    note += "。1年次は前学期GPA2.9以上のみ履修可能（※）"
                offering = {
                    "course_id": course["id"],
                    "term_code": "first" if slot % 2 else "second",
                    "semester_order": slot,
                    "academic_year": None,
                    "source_note": note,
                }
                key = (course["id"], slot)
                if key in offering_keys:
                    if offering_keys[key] != offering:
                        raise ValueError(
                            f"共通科目の開講情報が一致しません: {name}, {slot}"
                        )
                else:
                    offering_keys[key] = offering
                    seed["course_offerings"].append(offering)
            targets = selections[:3] if page["major"] == "advanced" else selections[3:]
            for index, program in enumerate(targets):
                course_type = (
                    clean(row[5 + index] or "") if booklet == 88 else clean(row[2])
                )
                code = group_codes[entry["group"]]
                seed["curriculum_courses"].append(
                    {
                        "curriculum_id": identity(
                            "curriculum", program + "-HANDBOOK-2026"
                        ),
                        "course_id": course["id"],
                        "classification_id": identity(
                            "classification", program + ":" + code
                        ),
                        "course_type": course_types[course_type],
                        "display_order": booklet * 100 + order,
                    }
                )
    (DIRECTORY / "cs_2026.json").write_text(
        json.dumps(seed, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print({key: len(records) for key, records in seed.items()})


if __name__ == "__main__":
    main()

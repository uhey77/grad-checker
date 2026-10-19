"""2026年度の公式公開表の保存済み転記から課程・科目・要件を再生成する。

ネットワークやPDF解析を実行しない。原セル・出典・SHA-256はsource.jsonに保持する。
既存CSのID・科目共有関係は変更しない。他学部の同名科目は共有しない。
"""

import json
import re
import unicodedata
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from seeds.university_external_rules import add_external_rules

ROOT = Path(__file__).resolve().parent
TYPES = {
    "必": "required",
    "必修": "required",
    "選必": "selective",
    "選": "elective",
    "選択": "elective",
    "": "elective",
}
TEACHING = {
    "講義": "lecture",
    "演習": "exercise",
    "実習": "practice",
    "実験": "experiment",
}


def identity(kind: str, code: str) -> str:
    return str(uuid5(NAMESPACE_URL, f"grad-checker:{kind}:{code}"))


def clean(value: str | None) -> str:
    return (value or "").replace("\x08", " ").replace("\n", "").strip()


def number(value: str | None) -> int:
    return int(unicodedata.normalize("NFKC", clean(value)))


def add_existing_cs_policies(requirements: dict) -> None:
    """既存4課程も同じ確認状態の契約で表示し、科目・要件のIDは維持する。"""
    cs = json.loads((ROOT / "cs_2026.json").read_text())
    for curriculum in cs["curricula"]:
        requirements["completion_policies"].append(
            dict(
                id=identity("completion-policy", curriculum["code"]),
                curriculum_id=curriculum["id"],
                degree_level="bachelor",
                campus="hachioji",
                catalog_status="verified",
                requirements_status="verified",
                rules_status="verified",
                unresolved_reasons=[],
                source_document=curriculum["source_document"],
                source_pages=curriculum["source_pages"],
                credit_groups=[],
                non_credit_conditions=[],
                credit_minimums=[],
            )
        )


def main() -> None:  # noqa: PLR0915 - 公式表の固定対応を同じ生成処理に集約する
    documents = json.loads((ROOT / "university_2026.source.json").read_text())
    docs = {d["filename"]: d for d in documents}
    subject_keys = (
        "academic_programs",
        "curricula",
        "classifications",
        "courses",
        "course_offerings",
        "curriculum_courses",
    )
    subjects = {key: [] for key in subject_keys}
    requirements = {
        key: []
        for key in (
            "graduation_requirements",
            "requirement_scopes",
            "credit_rules",
            "credit_rule_courses",
            "credit_rule_limits",
            "completion_policies",
        )
    }
    # (内部コード、学部/研究科、学科、専攻、コース、PDF接尾辞、修了要件表ページ)
    programs = []
    for code, course in [
        ("MEDICINE", "生命医薬"),
        ("ENVIRONMENT", "地球環境"),
        ("FOOD", "食品"),
        ("COSMETICS", "化粧品"),
    ]:
        programs.append(
            ("BS-" + code, "応用生物学部", None, None, course + "コース", "bs", 1)
        )
    for code, course in [
        ("CONTENT", "メディアコンテンツ"),
        ("TECH", "メディア技術"),
        ("SOCIAL", "メディア社会"),
    ]:
        programs.append(
            ("MS-" + code, "メディア学部", None, None, course + "コース", "ms", 3)
        )
    for code, department, page in [
        ("ME", "機械工学科", 4),
        ("EL", "電気電子工学科", 5),
        ("AC", "応用化学科", 6),
    ]:
        programs.append(
            ("ES-" + code, "工学部", department, None, None, "es-" + code.lower(), page)
        )
    for code, course in [
        ("VISUAL", "視覚デザイン"),
        ("INFO", "情報デザイン"),
        ("INDUSTRIAL", "工業デザイン"),
        ("SPACE", "空間デザイン"),
    ]:
        programs.append(
            ("DS-" + code, "デザイン学部", None, None, course + "コース", "ds", 15)
        )
    for code, department, specialization, page in [
        ("NS", "看護学科", None, 8),
        ("CE", "臨床工学科", None, 9),
        ("R-PT", "リハビリテーション学科", "理学療法学専攻", 11),
        ("R-OT", "リハビリテーション学科", "作業療法学専攻", 12),
        ("R-ST", "リハビリテーション学科", "言語聴覚学専攻", 13),
        ("MT", "臨床検査学科", None, 14),
    ]:
        programs.append(
            (
                "HS-" + code,
                "医療保健学部",
                department,
                specialization,
                "看護師資格のみ" if code == "NS" else None,
                "hs-" + code.lower(),
                page,
            )
        )
    programs.append(
        (
            "HS-NS-PHN",
            "医療保健学部",
            "看護学科",
            None,
            "看護師・保健師資格",
            "hs-ns",
            7,
        )
    )
    grad_names = [
        ("BIO", "バイオ・情報メディア研究科", "バイオニクス専攻"),
        ("CS", "バイオ・情報メディア研究科", "コンピュータサイエンス専攻"),
        ("MS", "バイオ・情報メディア研究科", "メディアサイエンス専攻"),
        ("ES", "工学研究科", "サステイナブル工学専攻"),
        ("DS", "デザイン研究科", "デザイン専攻"),
        ("MT", "医療技術学研究科", "臨床検査学専攻"),
    ]
    for index, (code, school, major) in enumerate(grad_names):
        programs.append(
            (
                "GR-" + code + "-M",
                school,
                None,
                major,
                "修士課程",
                "grad",
                index + 1 if index < 4 else index + 2,
            )
        )
        if index < 4:
            programs.append(
                ("GR-" + code + "-D", school, None, major, "博士後期課程", "grad", 5)
            )
    for code, school, major in grad_names[:3]:
        programs.append(
            (
                "GR-" + code + "-M-EN",
                school,
                None,
                major,
                "修士課程（英語プログラム）",
                "grad",
                5,
            )
        )
    counts = {}
    shared_courses = set()
    offering_programs = set()
    for code, faculty, department, specialization, course, suffix, req_page in programs:
        grad = code.startswith("GR-")
        doctoral = code.endswith("-D")
        english = code.endswith("-M-EN")
        doc = docs[f"kyouikukatei_2026_3-3-2_{suffix}.pdf"]
        offering_code = "GR-" + code.split("-")[1] + "-M" if grad else suffix.upper()
        if (
            not grad
            and offering_code != code
            and not any(
                p["code"] == offering_code for p in subjects["academic_programs"]
            )
        ):
            subjects["academic_programs"].append(
                dict(
                    id=identity("program", offering_code),
                    code=offering_code,
                    faculty_name=faculty,
                    department_name=department,
                    specialization_name=specialization,
                    course_name=None,
                )
            )
            offering_programs.add(offering_code)
        curriculum = identity("curriculum", code + "-HANDBOOK-2026")
        source = doc["url"]
        subjects["academic_programs"].append(
            dict(
                id=identity("program", code),
                code=code,
                faculty_name=faculty,
                department_name=department,
                specialization_name=specialization,
                course_name=course,
            )
        )
        subjects["curricula"].append(
            dict(
                id=curriculum,
                program_id=identity("program", code),
                code=code + "-HANDBOOK-2026",
                name="2026年度公開教育課程表 "
                + " ".join(filter(None, [faculty, department, specialization, course])),
                revision=1,
                admission_year_from=None,
                admission_year_to=None,
                source_document=source,
                source_pages="PDF "
                + (str(req_page) if grad else "1-" + str(len(doc["pages"]))),
                verification_status="unverified",
            )
        )
        reasons = []
        if english:
            reasons.append(
                "英語プログラムの科目名・単位一覧は公開されているが、日本語課程との科目同一性、必修研究科目、選択必修と算入規則の対応は未確認。独自に同一科目として統合しない。"
            )
        if doctoral:
            reasons.append(
                "博士後期の専攻別学位申請要件は公開表の例示だけでは確定できない。特別研究の単位数も掲載されていない。学部・修士の単位条件は流用しない。"
            )
        if suffix == "hs-ce":
            reasons.append(
                "2026年公開の教育課程表本文は2024年度入学生用・基礎必修12単位、2026年度卒業要件表は基礎必修20単位で不一致。2026年度科目集合の確認が必要。"
            )
        if suffix == "hs-ns":
            reasons.append(
                "2026年公開の教育課程表本文は2024年度入学生用。2026年度の看護師・保健師経路の科目集合・必須選択条件を確認する必要がある。"
            )
        # 公開教育課程表は教員指示等も保持する。自動的な履修可否の判断はしない。
        roots = {}
        classes = {}
        rows = []
        course_records: dict[str, dict[str, Any]] = {}
        group_buckets = {}
        for page in (
            []
            if doctoral or english
            else [doc["pages"][req_page - 1]]
            if grad
            else doc["pages"]
        ):
            for table in page["tables"]:
                headers = [clean(x) for x in table[0]]
                if grad and req_page <= 4:
                    ni, ti, ci, start = 1, None, 4, None
                else:
                    ni = next(
                        i
                        for i, h in enumerate(headers)
                        if h in ("授業科目名", "授業科目の名称")
                    )
                    ti = headers.index("種別")
                    ci = headers.index("単位数")
                    start = next(i for i, h in enumerate(headers) if "週時限数" in h)
                root_name = ""
                group_name = ""
                group_parts = {}
                bucket = None
                threshold = None
                if not grad:
                    if suffix in ("bs", "ms"):
                        root_name = (
                            "実学基礎科目"
                            if page["pdf_page"] <= 2
                            else "専門基礎教育科目"
                            if page["pdf_page"] < (4 if suffix == "bs" else 5)
                            else "専門教育科目"
                        )
                    elif suffix.startswith("es-"):
                        root_name = (
                            "実学基礎科目" if page["pdf_page"] <= 2 else "専門教育科目"
                        )
                for row_index, row in enumerate(table[1:], 1):
                    if not clean(row[ni]) or clean(row[ni]) in (
                        "授業科目名",
                        "授業科目",
                        "授業科目の名称",
                    ):
                        continue
                    raw_credit = unicodedata.normalize("NFKC", clean(row[ci])).strip(
                        "〔〕 "
                    )
                    if not raw_credit.isdecimal():
                        raise ValueError(
                            (code, page["pdf_page"], row_index, "単位セル", row)
                        )
                    if grad and req_page <= 4:
                        if row[0]:
                            root_name = (
                                clean(row[0])
                                .split("［")[0]
                                .split("[")[0]
                                .replace("※", "")
                            )
                        group_name = root_name
                        raw_type = (
                            "必修"
                            if "◎" in "".join(x or "" for x in row[2:4])
                            else "選必"
                            if "○" in "".join(x or "" for x in row[2:4])
                            else "選択"
                        )
                    else:
                        raw_type = clean(row[ti])
                        if suffix == "bs" and page["pdf_page"] >= 3:
                            idx = (
                                (5 if code == "BS-FOOD" else 6)
                                if page["pdf_page"] == 3
                                else {
                                    "BS-MEDICINE": 6,
                                    "BS-ENVIRONMENT": 7,
                                    "BS-FOOD": 8,
                                    "BS-COSMETICS": 9,
                                }[code]
                            )
                            raw_type = clean(row[idx]).strip("〔〕 ")
                            if raw_type == "-":
                                continue
                        if (
                            suffix.startswith("hs-")
                            or suffix == "ds"
                            or (grad and req_page >= 6)
                        ):
                            if row[0]:
                                root_name = clean(row[0])
                        group_columns = range(
                            1
                            if (suffix.startswith("hs-") or suffix == "ds" or grad)
                            else 0,
                            ni,
                        )
                        for gi in group_columns:
                            if row[gi]:
                                group_parts = {
                                    key: value
                                    for key, value in group_parts.items()
                                    if key <= gi
                                }
                                group_parts[gi] = clean(row[gi])
                        group_name = "／".join(group_parts.values())
                        if not group_name:
                            group_name = root_name
                        if start is not None and start > ci + 1:
                            cell = row[ci + 1]
                            if cell is not None:
                                nums = re.findall(
                                    r"\d+", unicodedata.normalize("NFKC", clean(cell))
                                )
                                # 人文・社会の2は内訳。10/8は別の選択必修群。
                                if "人文" in clean(cell):
                                    threshold = 10 if "10" in nums else 8
                                else:
                                    threshold = int(nums[0]) if nums else None
                                bucket = (
                                    f"p{page['pdf_page']}-r{row_index}"
                                    if threshold is not None
                                    else None
                                )
                    if raw_type not in TYPES:
                        raise ValueError((code, "種別", raw_type))
                    if not root_name:
                        raise ValueError((code, "分類なし", row))
                    root_id = identity("classification", code + ":" + root_name)
                    roots[root_name] = root_id
                    if root_id not in classes:
                        classes[root_id] = dict(
                            id=root_id,
                            curriculum_id=curriculum,
                            code=f"root-{len(roots)}",
                            name=root_name,
                            parent_id=None,
                            level=0,
                            display_order=len(classes),
                        )
                    group_id = root_id
                    path_name = root_name
                    parts = list(group_parts.values()) if group_parts else [group_name]
                    for depth, part in enumerate(parts, 1):
                        if part == root_name:
                            continue
                        path_name += ":" + part
                        child_id = identity("classification", code + ":" + path_name)
                        if child_id not in classes:
                            classes[child_id] = dict(
                                id=child_id,
                                curriculum_id=curriculum,
                                code=f"group-{len(classes)}",
                                name=part,
                                parent_id=group_id,
                                level=depth,
                                display_order=len(classes),
                            )
                        group_id = child_id
                    name = clean(row[ni])
                    # 注記は科目名から切り離し、原セルと開講注記に残す。
                    name = re.sub(r"\s*[※＊*].*$", "", name).strip()
                    course_code = (
                        offering_code + "-" + f"P{page['pdf_page']:02d}R{row_index:03d}"
                    )
                    cid = identity("course", course_code)
                    label = (
                        clean(row[-1])
                        if not (grad and req_page <= 4)
                        else "授業形態の記載なし"
                    )
                    item = dict(
                        id=cid,
                        code=course_code,
                        name=name,
                        credits=int(raw_credit),
                        offering_program_id=identity("program", offering_code),
                        teaching_type=TEACHING.get(label, "other"),
                        teaching_type_label=label,
                    )
                    course_records[cid] = item
                    if cid not in shared_courses:
                        subjects["courses"].append(item)
                        shared_courses.add(cid)
                    association: dict[str, Any] = dict(
                        curriculum_id=curriculum,
                        course_id=cid,
                        classification_id=group_id,
                        course_type=TYPES[raw_type],
                        display_order=len(rows),
                    )
                    subjects["curriculum_courses"].append(association)
                    rows.append((association, root_name, group_name, bucket, threshold))
                    if association["course_type"] == "selective" and bucket:
                        group_buckets.setdefault(
                            (root_name, bucket, threshold), []
                        ).append(cid)
                    if start is not None:
                        # 前後の見出しを左から補間。Qはsource_noteに保持する。
                        semester = 0
                        for column in range(start, len(row) - 1):
                            term = clean(table[2][column])
                            if term in ("前", "後", "前期", "後期"):
                                semester += 1
                            val = clean(row[column])
                            if not val:
                                continue
                            if not semester:
                                raise ValueError((code, "開講期不明", row))
                            subjects["course_offerings"].append(
                                dict(
                                    course_id=cid,
                                    term_code="first" if semester % 2 else "second",
                                    semester_order=semester,
                                    academic_year=None,
                                    source_note=(
                                        f"{doc['filename']} "
                                        f"PDF{page['pdf_page']} "
                                        f"原列{column + 1}: {val}。"
                                        "担当教員の指示・クォーター等の注記は原表を確認。"
                                    ),
                                )
                            )
        # クォーター2列を同一の前後期にまとめ、両方の原列注記は失わせない。
        subjects["classifications"].extend(classes.values())
        policy: dict[str, Any] = dict(
            id=identity("completion-policy", code),
            curriculum_id=curriculum,
            degree_level="doctoral" if doctoral else "master" if grad else "bachelor",
            campus="kamata"
            if suffix.startswith("hs-")
            or suffix == "ds"
            or code in ("GR-DS-M", "GR-MT-M")
            else "hachioji",
            catalog_status="unverified"
            if suffix in ("hs-ce", "hs-ns") or doctoral or english
            else "verified",
            requirements_status="unverified" if reasons else "verified",
            rules_status="unverified" if reasons else "verified",
            unresolved_reasons=reasons,
            source_document=source,
            source_pages="PDF "
            + (str(req_page) if grad else "1-" + str(len(doc["pages"]))),
            credit_groups=[],
            non_credit_conditions=[],
            credit_minimums=[],
        )
        if grad:
            for i, (root_name, _root_id) in enumerate(roots.items()):
                chosen = [a for a, r, _, _, _ in rows if r == root_name]
                required = [
                    a["course_id"] for a in chosen if a["course_type"] == "required"
                ]
                if req_page <= 4:
                    minimum = (
                        14
                        if required
                        else (4 if code == "GR-ES-M" else 2)
                        if chosen[0]["course_type"] == "selective"
                        else 12
                        if code == "GR-ES-M"
                        else 14
                    )
                elif req_page == 6:
                    minimum = 16 if root_name == "専門科目" else 14
                else:
                    minimum = {"専門基礎科目": 12, "専門領域科目": 4, "研究科目": 14}[
                        root_name
                    ]
                policy["credit_groups"].append(
                    dict(
                        code=f"group-{i}",
                        name=root_name,
                        course_ids=[a["course_id"] for a in chosen],
                        required_credits=minimum,
                        required_course_ids=required,
                        max_credits=minimum
                        if chosen[0]["course_type"] == "selective"
                        else None,
                        overflow_target="group-1"
                        if code == "GR-ES-M" and chosen[0]["course_type"] == "selective"
                        else None,
                    )
                )
            if code == "GR-MT-M":
                group = next(
                    g for g in policy["credit_groups"] if g["name"] == "専門領域科目"
                )
                policy["credit_groups"].remove(group)
                for label in ("講義", "演習"):
                    ids = [
                        cid
                        for cid in group["course_ids"]
                        if course_records[cid]["teaching_type_label"] == label
                    ]
                    policy["credit_groups"].append(
                        dict(
                            code="specialist-" + label,
                            name="専門領域 " + ("特論" if label == "講義" else "演習"),
                            course_ids=ids,
                            required_credits=2,
                            required_course_ids=[],
                            max_credits=None,
                            overflow_target=None,
                        )
                    )
            noncredits = [
                (
                    "duration",
                    "在学期間の条件（通常2年以上。短期修了は大学の認定条件を確認）"
                    if req_page <= 4
                    else "在学期間の条件（2年以上）",
                ),
                ("supervision", "必要な研究指導"),
                (
                    "thesis",
                    "修士作品・修士論文の審査合格"
                    if code == "GR-DS-M"
                    else "修士論文の審査合格",
                ),
            ]
            if code == "GR-MT-M":
                # 医療技術の公開修了要件は在学・論文審査・最終試験を列挙する。
                # 他研究科の「必要な研究指導」を追加条件として推測しない。
                noncredits = [(c, n) for c, n in noncredits if c != "supervision"]
            if code != "GR-DS-M":
                noncredits.append(("final_exam", "最終試験の合格"))
            if req_page <= 4:
                noncredits.append(("presentation", "在学中1回以上の学会等での対外発表"))
            if doctoral:
                noncredits = [
                    ("duration", "博士後期課程の在学期間条件（通常3年以上）"),
                    ("supervision", "必要な研究指導"),
                    ("thesis", "博士論文の審査合格"),
                    ("final_exam", "最終試験の合格"),
                    ("application", "専攻別の学位申請要件"),
                ]
            policy["non_credit_conditions"] = [
                dict(
                    code=c,
                    name=n,
                    source_document=docs["grad_sotsugyoyoken_2026_3-4-2.pdf"]["url"],
                    source_pages="PDF1-2",
                )
                for c, n in noncredits
            ]
        else:
            # 照合した選択必修群・必修集合・区分小計を既存モデルへ展開する。
            requirement_doc = docs["sotsugyoyoken_2026_3-4-1.pdf"]
            table = requirement_doc["pages"][req_page - 1]["tables"][
                1 if code == "BS-FOOD" else 0
            ]
            root_list = list(roots)
            subtotals = [r for r in table[1:] if "小計" in [clean(v) for v in r[:3]]]
            if len(subtotals) != len(root_list):
                policy["requirements_status"] = "unverified"
                policy["unresolved_reasons"].append(
                    "卒業要件表の区分小計と科目表の分類対応を追加照合する必要がある。"
                )

            def add(  # noqa: PLR0917 - 転記する要件行の固定列
                codepart,
                name,
                kind,
                credit_value,
                root=None,
                parent=None,
                cids=None,
                class_ids=None,
                *,
                program_code=code,
                curriculum_id=curriculum,
                source_url=requirement_doc["url"],
                source_page=req_page,
            ):
                rid = identity("requirement", program_code + ":" + codepart)
                requirements["graduation_requirements"].append(
                    dict(
                        id=rid,
                        curriculum_id=curriculum_id,
                        code=codepart,
                        name=name,
                        kind=kind,
                        required_credits=credit_value,
                        classification_id=root,
                        parent_id=parent,
                        display_order=len(requirements["graduation_requirements"]),
                        source_document=source_url,
                        source_pages="PDF" + str(source_page),
                    )
                )
                for target in cids or class_ids or []:
                    requirements["requirement_scopes"].append(
                        dict(
                            id=identity("scope", rid + ":" + target),
                            curriculum_id=curriculum_id,
                            requirement_id=rid,
                            course_id=target if cids else None,
                            classification_id=None if cids else target,
                        )
                    )
                return rid

            total_match = re.search(r"\d+", clean(table[-1][-1]))
            if total_match is None:
                raise ValueError((code, "総必要単位なし"))
            total = number(total_match.group())
            total_id = add(
                "total", "総必要単位", "total", total, class_ids=list(roots.values())
            )
            for i, root_name in enumerate(root_list):
                root_id = roots[root_name]
                if i >= len(subtotals):
                    continue
                subtotal = subtotals[i]
                root_min = re.search(r"\d+", clean(subtotal[-1]))
                if code == "HS-R-ST" and i > 0:
                    # 選択3は専門基礎共通＋専門発展をまたぐ一つの条件。
                    # 区分小計は必修分を保持し、3を両区分へ重複要求しない。
                    root_min = re.search(r"\d+", clean(subtotal[-3]))
                if root_min is None:
                    continue
                root_req = add(
                    f"root-{i}",
                    root_name + "合計",
                    "classification_total",
                    int(root_min.group()),
                    root_id,
                    total_id,
                    class_ids=[root_id],
                )
                required = [
                    a["course_id"]
                    for a, r, _, _, _ in rows
                    if r == root_name and a["course_type"] == "required"
                ]
                required_total = sum(course_records[c]["credits"] for c in required)
                printed_required = re.search(
                    r"\d+",
                    clean(
                        subtotal[-4]
                        if len(table[0]) == 6
                        else subtotal[-4]
                        if len(table[0]) == 7
                        else subtotal[-3]
                    ),
                )
                if printed_required and required_total != int(printed_required.group()):
                    policy["requirements_status"] = "unverified"
                    policy["unresolved_reasons"].append(
                        f"{root_name}の必修小計が科目表{required_total}と卒業要件表{printed_required.group()}で一致しない。"
                    )
                if required:
                    add(
                        f"root-{i}-required",
                        root_name + "必修",
                        "required_courses",
                        required_total,
                        root_id,
                        root_req,
                        cids=required,
                    )
                elective_cell = subtotal[-2]
                elective_min = re.search(r"\d+", clean(elective_cell))
                if code == "HS-R-ST" and i > 0:
                    elective_min = None
                add(
                    f"root-{i}-elective",
                    root_name + "選択",
                    "elective_total",
                    int(elective_min.group()) if elective_min else 0,
                    root_id,
                    root_req,
                    class_ids=[root_id],
                )
                for (r, bucket, threshold), cids in group_buckets.items():
                    if r != root_name:
                        continue
                    group_req = add(
                        f"{i}-{bucket}",
                        root_name
                        + " 選択必修（"
                        + "・".join(
                            dict.fromkeys(
                                g
                                for a, r, g, b, _ in rows
                                if r == root_name
                                and b == bucket
                                and a["course_id"] in cids
                            )
                        )
                        + "）",
                        "selective_group",
                        threshold,
                        root_id,
                        root_req,
                        cids=cids,
                    )
                    rule_id = identity("credit-rule", code + ":" + bucket)
                    requirements["credit_rules"].append(
                        dict(
                            id=rule_id,
                            curriculum_id=curriculum,
                            code=bucket,
                            kind="selective_overflow",
                            verification_status="verified",
                            source_document=source,
                            source_pages="PDF1-" + str(len(doc["pages"])),
                            source_note="科目区分ごとの選択必修超過を同区分の選択へ換算する。",
                            unresolved_reason=None,
                            revision=1,
                            allocation_policy=None,
                        )
                    )
                    requirements["credit_rule_courses"].extend(
                        dict(
                            curriculum_id=curriculum,
                            rule_id=rule_id,
                            course_id=c,
                            target_classification_id=root_id,
                        )
                        for c in cids
                    )
                    humanities = [
                        a["course_id"]
                        for a, r, g, b, _ in rows
                        if r == root_name and b == bucket and g in ("人文", "社会")
                    ]
                    if humanities:
                        for subgroup in ("人文", "社会"):
                            ids = [
                                a["course_id"]
                                for a, r, g, b, _ in rows
                                if r == root_name and b == bucket and g == subgroup
                            ]
                            add(
                                f"{i}-{bucket}-{subgroup}",
                                subgroup + "2単位以上",
                                "subminimum",
                                2,
                                root_id,
                                group_req,
                                cids=ids,
                            )
            if code == "HS-R-ST":
                policy["credit_minimums"].append(
                    dict(
                        code="specialist-common-development",
                        name="専門基礎共通・専門発展の選択合計3単位以上",
                        course_ids=[
                            a["course_id"]
                            for a, r, g, _, _ in rows
                            if a["course_type"] == "elective"
                            and (
                                (r == "専門基礎科目" and "共通" in g)
                                or (r == "専門科目" and "発展" in g)
                            )
                        ],
                        required_credits=3,
                        source_document=requirement_doc["url"],
                        source_pages="PDF13 注記",
                    )
                )
            selective = {
                a["course_id"]
                for a, _, _, _, _ in rows
                if a["course_type"] == "selective"
            }
            covered = {
                s["course_id"]
                for s in requirements["requirement_scopes"]
                if s["curriculum_id"] == curriculum
                and next(
                    r
                    for r in requirements["graduation_requirements"]
                    if r["id"] == s["requirement_id"]
                )["kind"]
                == "selective_group"
            }
            if selective != covered:
                policy["requirements_status"] = "unverified"
                policy["unresolved_reasons"].append(
                    "選択必修の所定単位数の結合セル・群対応に追加照合が必要。"
                )
            if policy["unresolved_reasons"]:
                policy["rules_status"] = "unverified"
        requirements["completion_policies"].append(policy)
        counts[code] = len(rows)
    add_existing_cs_policies(requirements)
    add_external_rules(subjects, requirements, identity)
    merged = {}
    for offering in subjects["course_offerings"]:
        key = (offering["course_id"], offering["term_code"], offering["semester_order"])
        if key in merged:
            if offering["source_note"] not in merged[key]["source_note"]:
                merged[key]["source_note"] += " / " + offering["source_note"]
        else:
            merged[key] = offering
    subjects["course_offerings"] = list(merged.values())
    for name, data in [
        ("university_2026.json", subjects),
        ("university_requirements_2026.json", requirements),
    ]:
        (ROOT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    print(counts)


if __name__ == "__main__":
    main()

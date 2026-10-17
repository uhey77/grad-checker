"""既知の旧CS2026規則と完全一致する行だけを、原本再確認後の規則へ更新する。"""

from sqlalchemy import Connection, update
from sqlmodel import SQLModel

from .models import CreditRule

GENERAL_PREVIOUS = {
    "code": "general.overflow",
    "kind": "selective_overflow",
    "verification_status": "unverified",
    "source_document": ("東京工科大学 2026年度学生便覧（八王子キャンパス）"),
    "source_pages": "冊子94注1・注2 / PDF96",
    "source_note": (
        "所定の単位数を超えて修得した選択必修科目の単位数"
        "は、科目区分ごとの選択科目の単位数に換算する。"
    ),
    "unresolved_reason": (
        "Q02: 総合等10単位超過時に人文・社会の内訳が不足する場合の換算は未確認。"
    ),
    "revision": 1,
    "allocation_policy": None,
}
GENERAL_CURRENT = {
    **GENERAL_PREVIOUS,
    "verification_status": "verified",
    "unresolved_reason": None,
    "revision": 2,
}

EXTERNAL_PREVIOUS = {
    "code": "other-faculty",
    "kind": "other_faculty",
    "verification_status": "unverified",
    "source_document": ("東京工科大学 2026年度学生便覧（八王子キャンパス）"),
    "source_pages": "冊子53(5) / PDF55",
    "source_note": (
        "同じキャンパスの他学部他学科の専門基礎教育・専門"
        "教育に属する選択または選択必修の講義科目。専門基"
        "礎・専門教育それぞれの選択に算入し、合計6単位ま"
        "で。超過分は自由科目。演習・実習・実験を除く。"
    ),
    "unresolved_reason": (
        "Q09: 複数算入先にまたがる上限超過時の配分順"
        "序、および対象他学部科目の照合・転記は未完了。"
    ),
    "revision": 1,
    "allocation_policy": None,
}
EXTERNAL_CURRENT = {
    **EXTERNAL_PREVIOUS,
    "unresolved_reason": (
        "配分順序は大学規則として未確認。アプリでは取得順"
        "・同時期は卒業要件を満たしやすい配分を採用する。"
        "対象他学部科目の照合・転記は未完了。"
    ),
    "revision": 2,
    "allocation_policy": ("chronological_best_fit_v1"),
}

REVISIONS = [
    (
        dict(
            GENERAL_PREVIOUS,
            id="c1750143-40e1-5796-8eec-adf4b84e351d",
            curriculum_id="597ff086-7eca-5bed-bf14-cccccf2fd9cd",
        ),
        dict(
            GENERAL_CURRENT,
            id="c1750143-40e1-5796-8eec-adf4b84e351d",
            curriculum_id="597ff086-7eca-5bed-bf14-cccccf2fd9cd",
        ),
    ),
    (
        dict(
            EXTERNAL_PREVIOUS,
            id="3d7327dd-d374-5699-9f71-3473cde4893d",
            curriculum_id="597ff086-7eca-5bed-bf14-cccccf2fd9cd",
        ),
        dict(
            EXTERNAL_CURRENT,
            id="3d7327dd-d374-5699-9f71-3473cde4893d",
            curriculum_id="597ff086-7eca-5bed-bf14-cccccf2fd9cd",
        ),
    ),
    (
        dict(
            GENERAL_PREVIOUS,
            id="807d9321-1177-5d0f-bc0f-a08d19d88638",
            curriculum_id="f1be3b63-dd45-5109-8cff-384a2199960e",
        ),
        dict(
            GENERAL_CURRENT,
            id="807d9321-1177-5d0f-bc0f-a08d19d88638",
            curriculum_id="f1be3b63-dd45-5109-8cff-384a2199960e",
        ),
    ),
    (
        dict(
            EXTERNAL_PREVIOUS,
            id="a5e3ecd2-c579-5bfd-b020-eb4b4269104c",
            curriculum_id="f1be3b63-dd45-5109-8cff-384a2199960e",
        ),
        dict(
            EXTERNAL_CURRENT,
            id="a5e3ecd2-c579-5bfd-b020-eb4b4269104c",
            curriculum_id="f1be3b63-dd45-5109-8cff-384a2199960e",
        ),
    ),
    (
        dict(
            GENERAL_PREVIOUS,
            id="286f33f5-e44b-551f-87d7-9516b9035a6d",
            curriculum_id="92e775e5-2873-5f6e-86d8-3e3a20124330",
        ),
        dict(
            GENERAL_CURRENT,
            id="286f33f5-e44b-551f-87d7-9516b9035a6d",
            curriculum_id="92e775e5-2873-5f6e-86d8-3e3a20124330",
        ),
    ),
    (
        dict(
            EXTERNAL_PREVIOUS,
            id="15689ee5-885d-532a-8cca-797d6fb8dc1f",
            curriculum_id="92e775e5-2873-5f6e-86d8-3e3a20124330",
        ),
        dict(
            EXTERNAL_CURRENT,
            id="15689ee5-885d-532a-8cca-797d6fb8dc1f",
            curriculum_id="92e775e5-2873-5f6e-86d8-3e3a20124330",
        ),
    ),
    (
        dict(
            GENERAL_PREVIOUS,
            id="2c3ed3bf-6426-5cb6-8196-baa32cd33713",
            curriculum_id="b2e10541-6d9e-507d-95e0-17b77b9f0e84",
        ),
        dict(
            GENERAL_CURRENT,
            id="2c3ed3bf-6426-5cb6-8196-baa32cd33713",
            curriculum_id="b2e10541-6d9e-507d-95e0-17b77b9f0e84",
        ),
    ),
    (
        dict(
            EXTERNAL_PREVIOUS,
            id="d67aeb16-3dbb-55a4-8a34-7b0d48a87060",
            curriculum_id="b2e10541-6d9e-507d-95e0-17b77b9f0e84",
        ),
        dict(
            EXTERNAL_CURRENT,
            id="d67aeb16-3dbb-55a4-8a34-7b0d48a87060",
            curriculum_id="b2e10541-6d9e-507d-95e0-17b77b9f0e84",
        ),
    ),
]


def revise_cs_2026(connection: Connection) -> None:
    table = SQLModel.metadata.tables[CreditRule.__tablename__]
    for previous, current in REVISIONS:
        connection.execute(
            update(table)
            .where(*(table.c[key] == value for key, value in previous.items()))
            .values(**current)
        )

"""課程ごとの対応範囲と大学院固有の修了条件。学部単位条件から独立させる。"""

from typing import Literal, Self
from uuid import UUID

from pydantic import Field, model_validator

from modules.subjects.grad_checker_subjects.application.subject_data_validation import (
    NonemptyText,
    NonnegativeInteger,
    SeedRecord,
)


class NonCreditCondition(SeedRecord):
    code: NonemptyText
    name: NonemptyText
    source_document: NonemptyText
    source_pages: NonemptyText


class CompletionAnswer(SeedRecord):
    code: NonemptyText = Field(max_length=100)
    status: Literal["met", "not_met", "unknown"]


class AdditionalCreditMinimum(NonCreditCondition):
    """複数の分類をまたぐ、総単位に重複加算しない内訳条件。"""

    course_ids: list[UUID] = Field(min_length=1)
    required_credits: NonnegativeInteger


class CompletionCreditGroup(SeedRecord):
    code: NonemptyText
    name: NonemptyText
    course_ids: list[UUID] = Field(min_length=1)
    required_credits: NonnegativeInteger
    required_course_ids: list[UUID] = Field(default_factory=list)
    # Noneは上限なし。修士ジェネリックスキルの超過は自由科目となる。
    max_credits: NonnegativeInteger | None = None
    overflow_target: str | None = None


class CompletionPolicyData(SeedRecord):
    id: UUID
    curriculum_id: UUID
    degree_level: Literal["bachelor", "master", "doctoral"]
    campus: Literal["hachioji", "kamata"]
    catalog_status: Literal["verified", "unverified"]
    requirements_status: Literal["verified", "unverified"]
    rules_status: Literal["verified", "unverified"]
    unresolved_reasons: list[NonemptyText] = Field(default_factory=list)
    source_document: NonemptyText
    source_pages: NonemptyText
    credit_groups: list[CompletionCreditGroup] = Field(default_factory=list)
    non_credit_conditions: list[NonCreditCondition] = Field(default_factory=list)
    credit_minimums: list[AdditionalCreditMinimum] = Field(default_factory=list)

    @model_validator(mode="after")
    def consistent(self) -> Self:
        ready = all(
            s == "verified"
            for s in (self.catalog_status, self.requirements_status, self.rules_status)
        )
        if ready == bool(self.unresolved_reasons):
            raise ValueError(
                "未整備課程には理由が必要で、対応済み課程には未確認事項を残せません。"
            )
        codes = [g.code for g in self.credit_groups]
        condition_codes = [c.code for c in self.non_credit_conditions]
        if len(set(codes)) != len(codes) or len(set(condition_codes)) != len(
            condition_codes
        ):
            raise ValueError("修了条件のコードが重複しています。")
        if self.degree_level == "bachelor" and (codes or condition_codes):
            raise ValueError("学部の条件は卒業要件マスタを使用してください。")
        if self.credit_minimums and self.degree_level != "bachelor":
            raise ValueError("大学院の単位条件は修了単位区分を使用してください。")
        minimum_codes = [c.code for c in self.credit_minimums]
        if len(set(minimum_codes)) != len(minimum_codes) or any(
            len(set(c.course_ids)) != len(c.course_ids) for c in self.credit_minimums
        ):
            raise ValueError("内訳条件のコードまたは対象科目が重複しています。")
        if ready and self.degree_level != "bachelor" and not condition_codes:
            raise ValueError("大学院には単位以外の修了条件が必要です。")
        if ready and self.degree_level == "master" and not self.credit_groups:
            raise ValueError("確認済み修士課程には単位区分が必要です。")
        seen: set[UUID] = set()
        for group in self.credit_groups:
            if len(set(group.course_ids)) != len(group.course_ids) or seen & set(
                group.course_ids
            ):
                raise ValueError("修了単位区分の対象科目が重複しています。")
            seen.update(group.course_ids)
            if not set(group.required_course_ids) <= set(group.course_ids):
                raise ValueError("必修科目が区分の対象外です。")
            if (
                group.max_credits is not None
                and group.max_credits < group.required_credits
            ):
                raise ValueError("算入上限が必要単位数より小さい値です。")
            if group.overflow_target is not None and (
                group.overflow_target not in codes
                or group.overflow_target == group.code
                or group.max_credits is None
            ):
                raise ValueError("超過算入先または上限が不正です。")
        by_code = {g.code: g for g in self.credit_groups}
        for group in self.credit_groups:
            if group.overflow_target is not None:
                target = by_code[group.overflow_target]
                if target.max_credits is not None or target.overflow_target is not None:
                    raise ValueError("超過換算は上限のない区分へ一度だけ行います。")
        return self

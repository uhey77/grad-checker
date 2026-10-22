"""卒業要件・算入規則・課程別修了条件のテーブル。課程をまたぐ参照はDBでも拒否する。"""

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Column,
    ForeignKeyConstraint,
    UniqueConstraint,
)
from sqlmodel import Field, SQLModel

from modules.subjects.infrastructure.persistence.models.subject_models import (
    integer_check,
    text_check,
)


class GraduationRequirement(SQLModel, table=True):
    __tablename__ = "graduation_requirements"
    __table_args__ = (
        UniqueConstraint("curriculum_id", "code"),
        UniqueConstraint("curriculum_id", "id"),
        ForeignKeyConstraint(
            ["curriculum_id", "classification_id"],
            ["classifications.curriculum_id", "classifications.id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["curriculum_id", "parent_id"],
            ["graduation_requirements.curriculum_id", "graduation_requirements.id"],
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "kind IN ('total', 'classification_total', 'required_courses', "
            "'selective_group', 'subminimum', 'elective_total')"
        ),
        CheckConstraint("parent_id IS NULL OR parent_id != id"),
        CheckConstraint(
            "(kind = 'total' AND parent_id IS NULL AND classification_id IS NULL) "
            "OR (kind != 'total' AND parent_id IS NOT NULL "
            "AND classification_id IS NOT NULL)"
        ),
        integer_check("required_credits"),
        integer_check("display_order"),
        text_check("code"),
        text_check("name"),
        text_check("source_document"),
        text_check("source_pages"),
    )
    id: str = Field(primary_key=True)
    curriculum_id: str = Field(foreign_key="curricula.id", ondelete="RESTRICT")
    code: str
    name: str
    kind: str
    required_credits: int
    classification_id: str | None = None
    parent_id: str | None = None
    display_order: int = 0
    source_document: str
    source_pages: str


class RequirementScope(SQLModel, table=True):
    __tablename__ = "requirement_scopes"
    __table_args__ = (
        UniqueConstraint("requirement_id", "classification_id"),
        UniqueConstraint("requirement_id", "course_id"),
        ForeignKeyConstraint(
            ["curriculum_id", "requirement_id"],
            ["graduation_requirements.curriculum_id", "graduation_requirements.id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["curriculum_id", "classification_id"],
            ["classifications.curriculum_id", "classifications.id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["curriculum_id", "course_id"],
            ["curriculum_courses.curriculum_id", "curriculum_courses.course_id"],
            ondelete="RESTRICT",
        ),
        CheckConstraint("(classification_id IS NULL) != (course_id IS NULL)"),
    )
    id: str = Field(primary_key=True)
    curriculum_id: str
    requirement_id: str
    classification_id: str | None = None
    course_id: str | None = None


class CreditRule(SQLModel, table=True):
    __tablename__ = "credit_rules"
    __table_args__ = (
        UniqueConstraint("curriculum_id", "code"),
        UniqueConstraint("curriculum_id", "id"),
        CheckConstraint("kind IN ('selective_overflow', 'other_faculty')"),
        CheckConstraint("verification_status IN ('verified', 'unverified')"),
        CheckConstraint(
            "(verification_status = 'unverified' AND unresolved_reason IS NOT NULL) "
            "OR (verification_status = 'verified' AND unresolved_reason IS NULL)"
        ),
        integer_check("revision", 1),
        text_check("code"),
        text_check("source_document"),
        text_check("source_pages"),
        text_check("source_note"),
        text_check("unresolved_reason", True),
        CheckConstraint(
            "allocation_policy IS NULL OR (kind = 'other_faculty' "
            "AND allocation_policy = 'chronological_best_fit_v1')"
        ),
    )
    id: str = Field(primary_key=True)
    curriculum_id: str = Field(foreign_key="curricula.id", ondelete="RESTRICT")
    code: str
    kind: str
    verification_status: str
    source_document: str
    source_pages: str
    source_note: str
    unresolved_reason: str | None = None
    revision: int
    allocation_policy: str | None = None


class CreditRuleCourse(SQLModel, table=True):
    __tablename__ = "credit_rule_courses"
    __table_args__ = (
        ForeignKeyConstraint(
            ["curriculum_id", "rule_id"],
            ["credit_rules.curriculum_id", "credit_rules.id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["curriculum_id", "target_classification_id"],
            ["classifications.curriculum_id", "classifications.id"],
            ondelete="RESTRICT",
        ),
    )
    curriculum_id: str
    rule_id: str = Field(primary_key=True)
    course_id: str = Field(
        primary_key=True, foreign_key="courses.id", ondelete="RESTRICT"
    )
    target_classification_id: str


class CreditRuleLimit(SQLModel, table=True):
    __tablename__ = "credit_rule_limits"
    __table_args__ = (
        UniqueConstraint("rule_id", "limit_group_code"),
        text_check("limit_group_code"),
        integer_check("max_credits"),
    )
    id: str = Field(primary_key=True)
    rule_id: str = Field(foreign_key="credit_rules.id", ondelete="RESTRICT")
    limit_group_code: str
    max_credits: int


class CompletionPolicy(SQLModel, table=True):
    __tablename__ = "completion_policies"
    __table_args__ = (UniqueConstraint("curriculum_id"),)
    id: str = Field(primary_key=True)
    curriculum_id: str = Field(foreign_key="curricula.id", ondelete="RESTRICT")
    degree_level: str
    campus: str
    catalog_status: str
    requirements_status: str
    rules_status: str
    unresolved_reasons: list[str] = Field(sa_column=Column(JSON, nullable=False))
    source_document: str
    source_pages: str
    credit_groups: list[dict] = Field(sa_column=Column(JSON, nullable=False))
    non_credit_conditions: list[dict] = Field(sa_column=Column(JSON, nullable=False))
    credit_minimums: list[dict] = Field(
        default_factory=list, sa_column=Column(JSON, nullable=False)
    )


REQUIREMENT_TABLES = [
    SQLModel.metadata.tables[model.__tablename__]
    for model in (
        GraduationRequirement,
        RequirementScope,
        CreditRule,
        CreditRuleCourse,
        CreditRuleLimit,
        CompletionPolicy,
    )
]

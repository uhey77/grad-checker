"""卒業単位条件と算入規則の種類。"""

from enum import StrEnum


class RequirementKind(StrEnum):
    TOTAL = "total"
    CLASSIFICATION_TOTAL = "classification_total"
    REQUIRED_COURSES = "required_courses"
    SELECTIVE_GROUP = "selective_group"
    SUBMINIMUM = "subminimum"
    ELECTIVE_TOTAL = "elective_total"


class CreditRuleKind(StrEnum):
    SELECTIVE_OVERFLOW = "selective_overflow"
    OTHER_FACULTY = "other_faculty"

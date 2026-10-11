"""マスタで使用する区分。Web・永続化ライブラリに依存しない。"""

from enum import StrEnum


class VerificationStatus(StrEnum):
    UNVERIFIED = "unverified"
    VERIFIED = "verified"


class TeachingType(StrEnum):
    LECTURE = "lecture"
    EXERCISE = "exercise"
    PRACTICE = "practice"
    EXPERIMENT = "experiment"
    OTHER = "other"


class CourseType(StrEnum):
    REQUIRED = "required"
    SELECTIVE = "selective"
    ELECTIVE = "elective"

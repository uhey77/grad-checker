"""講義・演習など、科目の授業形態。"""

from enum import StrEnum


class TeachingType(StrEnum):
    LECTURE = "lecture"
    EXERCISE = "exercise"
    PRACTICE = "practice"
    EXPERIMENT = "experiment"
    OTHER = "other"

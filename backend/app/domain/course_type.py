"""課程ごとの必修・選択区分。"""

from enum import StrEnum


class CourseType(StrEnum):
    REQUIRED = "required"
    SELECTIVE = "selective"
    ELECTIVE = "elective"

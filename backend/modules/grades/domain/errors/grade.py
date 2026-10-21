from typing import Literal


class InvalidCourseAttemptsError(Exception):
    def __init__(
        self, code: Literal["duplicate_attempt", "invalid_attempt_sequence"]
    ) -> None:
        super().__init__(code)
        self.code = code

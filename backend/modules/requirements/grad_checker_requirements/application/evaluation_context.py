"""判定前のマスタ検証と課程別対象集合の展開。"""

from uuid import UUID

from modules.grades.grad_checker_grades.application.errors.grades import GradeError
from modules.grades.grad_checker_grades.application.grades import (
    GradeAttempt,
    check_attempts,
)
from modules.requirements.grad_checker_requirements.domain.requirement import (
    RequirementKind,
)

from .errors.evaluation import (
    EvaluationError,
)
from .errors.seed import (
    RequirementSeedError,
)
from .evaluation_models import (
    EvaluationSnapshot,
)
from .validation import (
    inside,
    validate_requirements,
)


def invalid_master(reason: str) -> EvaluationError:
    return EvaluationError("invalid_evaluation_master", reason)


class EvaluationContext:
    def __init__(self, snapshot: EvaluationSnapshot) -> None:
        self.snapshot = snapshot
        try:
            ordered = validate_requirements(snapshot.requirements, snapshot.subjects)
        except RequirementSeedError as error:
            raise invalid_master(str(error)) from error
        curricula = {row.id: row for row in snapshot.subjects.curricula}
        curriculum = curricula.get(snapshot.curriculum_id)
        if curriculum is None or curriculum.program_id != snapshot.program_id:
            raise invalid_master("所属と適用カリキュラムが一致しません。")
        if curriculum.verification_status != "verified":
            raise EvaluationError(
                "unverified_curriculum", "カリキュラムの適用入学年度が未確認です。"
            )
        self.curriculum = curriculum
        self.courses = {row.id: row for row in snapshot.subjects.courses}
        self.classes = {row.id: row for row in snapshot.subjects.classifications}
        self.associations = {
            row.course_id: row
            for row in snapshot.subjects.curriculum_courses
            if row.curriculum_id == curriculum.id
        }
        self.conditions = sorted(
            (row for row in ordered if row.curriculum_id == curriculum.id),
            key=lambda row: (row.display_order, str(row.id)),
        )
        self.rules = {
            row.id: row
            for row in snapshot.requirements.credit_rules
            if row.curriculum_id == curriculum.id
        }
        self.targets: dict[UUID, set[UUID]] = {row.id: set() for row in self.conditions}
        for scope in snapshot.requirements.requirement_scopes:
            if scope.curriculum_id != curriculum.id:
                continue
            if scope.course_id is not None:
                self.targets[scope.requirement_id].add(scope.course_id)
            elif scope.classification_id is not None:
                self.targets[scope.requirement_id].update(
                    self.class_courses(scope.classification_id)
                )
        self.validate_coverage()
        self.latest = self.latest_grades()

    def class_courses(self, classification_id: UUID) -> set[UUID]:
        return {
            row.course_id
            for row in self.associations.values()
            if inside(self.classes, row.classification_id, classification_id)
        }

    def root(self, classification_id: UUID) -> UUID:
        current = self.classes[classification_id]
        while current.parent_id is not None:
            current = self.classes[current.parent_id]
        return current.id

    def validate_coverage(self) -> None:
        totals = [r for r in self.conditions if r.kind == RequirementKind.TOTAL]
        if len(totals) != 1 or not self.associations:
            raise invalid_master("総単位条件または課程別科目が不足しています。")
        if self.targets[totals[0].id] != set(self.associations):
            raise invalid_master("総単位条件が課程の全科目を含んでいません。")
        roots = {self.root(row.classification_id) for row in self.associations.values()}
        for kind in (
            RequirementKind.CLASSIFICATION_TOTAL,
            RequirementKind.ELECTIVE_TOTAL,
        ):
            rows = [row for row in self.conditions if row.kind == kind]
            if len(rows) != len(roots) or {r.classification_id for r in rows} != roots:
                raise invalid_master(
                    "各最上位区分の合計・選択条件が不足または重複しています。"
                )
            for row in rows:
                assert row.classification_id is not None
                if self.targets[row.id] != self.class_courses(row.classification_id):
                    raise invalid_master("区分合計・選択条件の対象分類が不完全です。")
        for kind, course_type in (
            (RequirementKind.REQUIRED_COURSES, "required"),
            (RequirementKind.SELECTIVE_GROUP, "selective"),
        ):
            covered: set[UUID] = set()
            for row in self.conditions:
                if row.kind != kind:
                    continue
                if covered & self.targets[row.id]:
                    raise invalid_master("必修または選択必修の条件が重複しています。")
                covered.update(self.targets[row.id])
            expected = {
                row.course_id
                for row in self.associations.values()
                if row.course_type == course_type
            }
            if covered != expected:
                raise invalid_master("必修または選択必修の条件が不足しています。")

    def latest_grades(self) -> dict[UUID, GradeAttempt]:
        latest: dict[UUID, GradeAttempt] = {}
        # UUIDの表記揺れでも同一科目の履修回次として検証する。
        normalized = []
        for grade in self.snapshot.grades:
            try:
                course_id = UUID(grade.course_id)
            except ValueError as error:
                raise EvaluationError("invalid_grades", "科目IDが不正です。") from error
            if course_id not in self.courses:
                raise EvaluationError(
                    "unknown_course", "成績に未知の科目が含まれています。"
                )
            normalized.append(grade.model_copy(update={"course_id": str(course_id)}))
            previous = latest.get(course_id)
            if previous is None or previous.attempt_no < grade.attempt_no:
                latest[course_id] = grade
        try:
            check_attempts(normalized)
        except GradeError as error:
            raise EvaluationError(error.code, "成績の履修回次が不正です。") from error
        return latest

"""判定・判定履歴のユースケースのトランザクション範囲をFakeのUnit of Workで検証する。"""

from uuid import UUID, uuid4

import pytest

from modules.requirements.grad_checker_requirements.application import (
    evaluation_models,
    student_evaluation,
)
from modules.requirements.grad_checker_requirements.application.check_results import (
    CheckRepository,
    CheckRequest,
    CheckService,
    CheckUnitOfWork,
    SavedCheck,
)
from modules.requirements.grad_checker_requirements.application.errors import (
    evaluation as evaluation_errors,
)
from tests.fakes import FakeUnitOfWork


class FakeEvaluationRepository(student_evaluation.EvaluationRepository):
    def __init__(self, uow: FakeUnitOfWork, data_revision: int) -> None:
        self.uow = uow
        self.snapshot = evaluation_models.EvaluationSnapshot.model_construct(
            data_revision=data_revision
        )

    def get_snapshot(self, student_id: str) -> evaluation_models.EvaluationSnapshot:
        self.uow.require_block()
        return self.snapshot


class FakeCheckRepository(CheckRepository):
    def __init__(self, uow: FakeUnitOfWork) -> None:
        self.uow = uow
        self.added: list[SavedCheck] = []

    def add(self, student_id: str, check: SavedCheck) -> None:
        self.uow.require_block()
        self.added.append(check)

    def get(self, student_id: str, check_id: UUID) -> SavedCheck | None:
        self.uow.require_block()
        return None


class FakeCheckUnitOfWork(FakeUnitOfWork, CheckUnitOfWork):
    def __init__(self, data_revision: int = 1) -> None:
        super().__init__()
        self.evaluations = FakeEvaluationRepository(self, data_revision)
        self.saved = FakeCheckRepository(self)

    @property
    def evaluation(self) -> FakeEvaluationRepository:
        return self.evaluations

    @property
    def checks(self) -> FakeCheckRepository:
        return self.saved


class FakeEvaluationUnitOfWork(FakeUnitOfWork, student_evaluation.EvaluationUnitOfWork):
    def __init__(self) -> None:
        super().__init__()
        self.evaluations = FakeEvaluationRepository(self, data_revision=1)

    @property
    def evaluation(self) -> FakeEvaluationRepository:
        return self.evaluations


def test_stale_revision_rolls_back_without_saving_a_check():
    uow = FakeCheckUnitOfWork(data_revision=2)
    with pytest.raises(evaluation_errors.EvaluationError, match="revision_conflict"):
        CheckService(uow).create_check("student", CheckRequest(expected_revision=1))
    assert uow.events == ["write", "rollback"]
    assert uow.saved.added == []


def test_missing_check_is_read_without_writing():
    uow = FakeCheckUnitOfWork()
    with pytest.raises(evaluation_errors.EvaluationError, match="check_not_found"):
        CheckService(uow).get_check("student", uuid4())
    assert uow.events == ["read"]


def test_evaluation_reads_a_snapshot_and_computes_outside_the_transaction(
    monkeypatch,
):
    uow = FakeEvaluationUnitOfWork()
    computed = []

    def evaluate(snapshot, evaluated_at):
        # 判定の計算はトランザクションを閉じてから行う。
        assert not uow.active
        computed.append(snapshot)
        return "result"

    monkeypatch.setattr(student_evaluation, "evaluate_student", evaluate)
    service = student_evaluation.EvaluationService(uow)
    assert service.evaluate("student") == "result"
    assert uow.events == ["read"]
    assert computed == [uow.evaluations.snapshot]

"""判定・判定履歴のユースケースのトランザクション範囲をFakeのUnit of Workで検証する。"""

from uuid import UUID, uuid4

import pytest

from modules.requirements.application.dto import check_results as check_results_dto
from modules.requirements.application.dto import evaluation as evaluation_models
from modules.requirements.application.errors import evaluation as evaluation_errors
from modules.requirements.application.ports import check_results as check_results_ports
from modules.requirements.application.queries import (
    student_evaluation as student_evaluation_ports,
)
from modules.requirements.application.uow.check_results import CheckUnitOfWork
from modules.requirements.application.uow.student_evaluation import EvaluationUnitOfWork
from modules.requirements.public import (
    CreateCheckUseCase,
    EvaluateGraduationUseCase,
    GetCheckUseCase,
    ListChecksUseCase,
)
from tests.support.fakes import FakeUnitOfWork, FixedClock


class FakeEvaluationRepository(student_evaluation_ports.EvaluationRepository):
    def __init__(self, uow: FakeUnitOfWork, data_revision: int) -> None:
        self.uow = uow
        self.snapshot = evaluation_models.EvaluationSnapshot.model_construct(
            data_revision=data_revision
        )

    def get_snapshot(self, student_id: str) -> evaluation_models.EvaluationSnapshot:
        self.uow.require_block()
        return self.snapshot


class FakeCheckRepository(check_results_ports.CheckRepository):
    def __init__(self, uow: FakeUnitOfWork) -> None:
        self.uow = uow
        self.added: list[check_results_dto.SavedCheck] = []

    def add(self, student_id: str, check: check_results_dto.SavedCheck) -> None:
        self.uow.require_block()
        self.added.append(check)

    def get(
        self, student_id: str, check_id: UUID
    ) -> check_results_dto.SavedCheck | None:
        self.uow.require_block()
        return None

    def count(self, student_id: str) -> int:
        self.uow.require_block()
        return 0

    def list_page(self, student_id: str, page: check_results_dto.CheckPage) -> list:
        self.uow.require_block()
        return []


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


class FakeEvaluationUnitOfWork(FakeUnitOfWork, EvaluationUnitOfWork):
    def __init__(self) -> None:
        super().__init__()
        self.evaluations = FakeEvaluationRepository(self, data_revision=1)

    @property
    def evaluation(self) -> FakeEvaluationRepository:
        return self.evaluations


def test_stale_revision_rolls_back_without_saving_a_check():
    uow = FakeCheckUnitOfWork(data_revision=2)
    with pytest.raises(evaluation_errors.EvaluationError, match="revision_conflict"):
        CreateCheckUseCase(uow, FixedClock()).execute(
            "student", check_results_dto.CheckRequest(expected_revision=1)
        )
    assert uow.events == ["write", "rollback"]
    assert uow.saved.added == []


def test_missing_check_is_read_without_writing():
    uow = FakeCheckUnitOfWork()
    with pytest.raises(evaluation_errors.EvaluationError, match="check_not_found"):
        GetCheckUseCase(uow).execute("student", uuid4())
    assert uow.events == ["read"]


def test_check_list_counts_and_reads_in_one_read_block():
    uow = FakeCheckUnitOfWork()
    page = ListChecksUseCase(uow).execute(
        "student", check_results_dto.CheckPage(limit=5, offset=10)
    )
    assert (page.checks, page.limit, page.offset, page.total_count) == ([], 5, 10, 0)
    assert uow.events == ["read"]


def test_evaluation_reads_a_snapshot_and_computes_outside_the_transaction(
    monkeypatch,
):
    uow = FakeEvaluationUnitOfWork()
    computed = []
    times = []

    def evaluate(snapshot, evaluated_at):
        # 判定の計算はトランザクションを閉じてから行う。
        assert not uow.active
        computed.append(snapshot)
        times.append(evaluated_at)
        return "result"

    monkeypatch.setattr(
        "modules.requirements.application.use_cases.evaluate_graduation.evaluate_student",
        evaluate,
    )
    clock = FixedClock()
    service = EvaluateGraduationUseCase(uow, clock)
    assert service.execute("student") == "result"
    assert uow.events == ["read"]
    assert computed == [uow.evaluations.snapshot]
    assert times == [clock.value]

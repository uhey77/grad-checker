from collections.abc import Sequence
from uuid import UUID

from modules.requirements.domain.value_objects.credits import AllocationTarget


def allocate_best_fit(
    targets: Sequence[AllocationTarget], limit: int
) -> dict[UUID, int]:
    """達成条件数を最大化し、次に不足単位を最小化。同点は分類コード順で固定。"""
    ordered = sorted(targets, key=lambda target: target.code)
    # 共通上限ごとの最良状態を残し、科目数に対する全組合せ探索を避ける。
    states: dict[int, tuple[int, int, tuple[int, ...]]] = {0: (0, 0, ())}
    for target in ordered:
        following: dict[int, tuple[int, int, tuple[int, ...]]] = {}
        for used, (passed, shortage, values) in states.items():
            for value in range(min(target.available_credits, limit - used) + 1):
                fulfilled, deficit = target.score(value)
                candidate = (passed + fulfilled, shortage + deficit, (*values, value))
                count = used + value
                if count not in following or candidate > following[count]:
                    following[count] = candidate
        states = following
    return dict(zip((target.id for target in ordered), states[limit][2], strict=True))

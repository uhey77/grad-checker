"""科目分類を上位へ辿り、最上位から並べた経路を作る。"""

from modules.subjects.infrastructure.persistence.models.subject_models import (
    Classification,
)


def classification_path(
    classifications: dict[str, Classification], start: str
) -> list[Classification] | None:
    """分類の欠落・循環がある場合はNone。呼出し側の業務エラーへ変換する。"""
    path = []
    visited = set()
    current: str | None = start
    while current is not None:
        if current in visited or current not in classifications:
            return None
        visited.add(current)
        classification = classifications[current]
        path.append(classification)
        current = classification.parent_id
    return list(reversed(path))

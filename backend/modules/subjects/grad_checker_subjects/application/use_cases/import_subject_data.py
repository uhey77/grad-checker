"""ImportSubjectDataUseCaseの処理手順とトランザクション境界。"""

from ..dto.subject_data import SubjectDataSeed
from ..errors.subject_data import SeedError
from ..ports.subject_data_import import SubjectDataUnitOfWork
from ..services.subject_data_import import TABLES, record_key
from ..services.subject_data_validation import validate_subject_data


class ImportSubjectDataUseCase:
    def __init__(self, uow: SubjectDataUnitOfWork) -> None:
        self.uow = uow

    def execute(self, seed: SubjectDataSeed) -> dict[str, int]:
        # 入力内の重複を先に拒否する。参照は既存DBを使えるため、ここでは検証しない。
        for name in TABLES:
            keys = [record_key(record) for record in getattr(seed, name)]
            if len(keys) != len(set(keys)):
                raise SeedError(f"{name}の投入データが重複しています。")
        # 検証から投入完了まで書込みロックを保持し、並行シードの競合を防ぐ。
        with self.uow.write():
            existing = self.uow.subject_data.load()
            combined: dict[str, list] = {}
            additions: dict[str, list] = {}
            for name in TABLES:
                current = getattr(existing, name)
                by_key = {record_key(record): record for record in current}
                new = []
                for record in getattr(seed, name):
                    key = record_key(record)
                    if key in by_key:
                        if by_key[key] != record:
                            raise SeedError(
                                f"{name}の既存データと内容が異なります。通常のシードでは更新できません。"
                            )
                    else:
                        new.append(record)
                combined[name] = current + new
                additions[name] = new
            ordered = validate_subject_data(SubjectDataSeed(**combined))
            # 親分類も同じテーブルなので、親から順に追加する。
            new_classifications = {record.id for record in additions["classifications"]}
            additions["classifications"] = [
                record for record in ordered if record.id in new_classifications
            ]
            self.uow.subject_data.insert(SubjectDataSeed(**additions))
        return {name: len(additions[name]) for name in TABLES}

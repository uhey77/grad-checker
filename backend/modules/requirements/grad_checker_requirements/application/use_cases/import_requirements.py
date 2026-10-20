"""ImportRequirementsUseCaseの処理手順とトランザクション境界。"""

from modules.requirements.grad_checker_requirements.application.errors.seed import (
    RequirementSeedError,
)
from modules.requirements.grad_checker_requirements.application.seed import (
    RequirementSeed,
)
from modules.requirements.grad_checker_requirements.application.validation import (
    unique,
    validate_requirements,
)

from ..seed_import import (
    TABLES,
    RequirementUnitOfWork,
    record_key,
)


class ImportRequirementsUseCase:
    def __init__(self, uow: RequirementUnitOfWork) -> None:
        self.uow = uow

    def execute(self, seed: RequirementSeed) -> dict[str, int]:
        # model_copy等から渡されても、入口で型・値の検証を省略しない。
        seed = RequirementSeed.model_validate_json(seed.model_dump_json())
        for name in TABLES:
            unique(getattr(seed, name), record_key, name)
        # 科目マスタの読取りから投入完了まで、書込みロックで並行シードを防ぐ。
        with self.uow.write():
            subjects = self.uow.requirements.subjects()
            existing = self.uow.requirements.load()
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
                            raise RequirementSeedError(
                                f"{name}の既存データと内容が異なります。通常のシードでは更新できません。"
                            )
                    else:
                        new.append(record)
                combined[name] = current + new
                additions[name] = new
            ordered = validate_requirements(RequirementSeed(**combined), subjects)
            # 親要件も同じテーブルなので、親から順に追加する。
            new_ids = {record.id for record in additions["graduation_requirements"]}
            additions["graduation_requirements"] = [
                row for row in ordered if row.id in new_ids
            ]
            self.uow.requirements.insert(RequirementSeed(**additions))
        return {name: len(additions[name]) for name in TABLES}

"""ListChecksUseCaseの処理手順とトランザクション境界。"""

from modules.requirements.application.dto.check_results import CheckList, CheckPage
from modules.requirements.application.uow.check_results import CheckUnitOfWork


class ListChecksUseCase:
    def __init__(self, uow: CheckUnitOfWork) -> None:
        self.uow = uow

    def execute(self, student_id: str, page: CheckPage) -> CheckList:
        # 件数と一覧を同じ読取りスナップショットで数え、ページ境界をずらさない。
        with self.uow.read():
            total_count = self.uow.checks.count(student_id)
            checks = self.uow.checks.list_page(student_id, page)
        return CheckList(
            checks=checks,
            limit=page.limit,
            offset=page.offset,
            total_count=total_count,
        )

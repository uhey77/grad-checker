"""GetSubjectListUseCaseの処理手順とトランザクション境界。"""

from uuid import UUID

from ..dto.subject_list import SubjectList
from ..ports.subject_list import SubjectListUnitOfWork


class GetSubjectListUseCase:
    def __init__(self, uow: SubjectListUnitOfWork) -> None:
        self.uow = uow

    def execute(self, curriculum_id: UUID) -> SubjectList:
        with self.uow.read():
            return self.uow.subject_list.get_subject_list(curriculum_id)

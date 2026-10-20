"""ListSubjectProgramsUseCaseの処理手順とトランザクション境界。"""

from ..dto.subject_list import SubjectListProgram
from ..ports.subject_list import SubjectListUnitOfWork


class ListSubjectProgramsUseCase:
    def __init__(self, uow: SubjectListUnitOfWork) -> None:
        self.uow = uow

    def execute(self) -> list[SubjectListProgram]:
        with self.uow.read():
            return self.uow.subject_list.list_programs()

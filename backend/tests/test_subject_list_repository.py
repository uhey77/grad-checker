from uuid import UUID

import pytest

from modules.subjects.grad_checker_subjects.application.subject_list import (
    SubjectList,
    SubjectListProgram,
    SubjectListRepository,
)


class MissingSubjectListRepository(SubjectListRepository):
    def list_programs(self) -> list[SubjectListProgram]:
        return []


class MissingProgramsRepository(SubjectListRepository):
    def get_subject_list(self, curriculum_id: UUID) -> SubjectList:
        raise NotImplementedError


@pytest.mark.parametrize(
    "repository_class",
    [SubjectListRepository, MissingSubjectListRepository, MissingProgramsRepository],
)
def test_incomplete_repository_cannot_be_instantiated(repository_class):
    with pytest.raises(TypeError, match="abstract"):
        repository_class()

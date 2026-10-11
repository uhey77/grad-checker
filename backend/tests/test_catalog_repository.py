from uuid import UUID

import pytest

from app.application.course_catalog import CatalogProgram, CatalogRepository, CourseCatalog


class MissingCatalogRepository(CatalogRepository):
    def list_programs(self) -> list[CatalogProgram]:
        return []


class MissingProgramsRepository(CatalogRepository):
    def get_catalog(self, curriculum_id: UUID) -> CourseCatalog:
        raise NotImplementedError


@pytest.mark.parametrize(
    "repository_class",
    [CatalogRepository, MissingCatalogRepository, MissingProgramsRepository],
)
def test_incomplete_repository_cannot_be_instantiated(repository_class):
    with pytest.raises(TypeError, match="abstract"):
        repository_class()

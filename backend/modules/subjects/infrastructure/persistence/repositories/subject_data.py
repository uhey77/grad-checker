"""課程・科目データのシード読込みと、投入済みデータの読取り・追加。"""

from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session, select

from modules.subjects.application.dto.subject_data import (
    AcademicProgramData,
    ClassificationData,
    CurriculumData,
    CurriculumSubjectData,
    SubjectData,
    SubjectDataSeed,
    SubjectOfferingData,
)
from modules.subjects.application.errors.subject_data import SeedError
from modules.subjects.application.ports.subject_data_import import SubjectDataStore
from modules.subjects.infrastructure.persistence.models.subject_models import (
    AcademicProgram,
    Classification,
    Curriculum,
    CurriculumSubject,
    Subject,
    SubjectOffering,
)

TABLE_MAPPING = (
    ("academic_programs", AcademicProgram, AcademicProgramData),
    ("curricula", Curriculum, CurriculumData),
    ("classifications", Classification, ClassificationData),
    ("courses", Subject, SubjectData),
    ("course_offerings", SubjectOffering, SubjectOfferingData),
    ("curriculum_courses", CurriculumSubject, CurriculumSubjectData),
)


def unavailable(_error: SQLAlchemyError) -> SeedError:
    return SeedError(
        "課程・科目データを保存できません。DB接続・制約・競合を確認してください。全件の変更を取り消しました。"
    )


def load_seed(path: Path) -> SubjectDataSeed:
    try:
        return SubjectDataSeed.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError) as error:
        raise SeedError("シードファイルをUTF-8で読み込めません。") from error
    except ValidationError as error:
        locations = [
            ".".join(map(str, entry["loc"])) or "JSON" for entry in error.errors()
        ]
        raise SeedError(
            "シードの形式・型・値が不正です。確認箇所: " + ", ".join(locations)
        ) from error


class SqliteSubjectDataStore(SubjectDataStore):
    def __init__(self, session: Session) -> None:
        self.db = session

    def load(self) -> SubjectDataSeed:
        return SubjectDataSeed.model_validate(
            {
                name: [
                    schema.model_validate(
                        row.model_dump(include=set(schema.model_fields))
                    )
                    for row in self.db.exec(select(model)).all()
                ]
                for name, model, schema in TABLE_MAPPING
            }
        )

    def insert(self, additions: SubjectDataSeed) -> None:
        for name, model, _ in TABLE_MAPPING:
            for record in getattr(additions, name):
                data = record.model_dump(mode="json")
                if name == "course_offerings":
                    identity = (
                        f"grad-checker:offering:{data['course_id']}:"
                        f"{data['term_code']}:{data['semester_order']}:"
                        f"{data['academic_year']}"
                    )
                    data["id"] = str(uuid5(NAMESPACE_URL, identity))
                self.db.add(model(**data))
                # 親分類も同じテーブルなので、順序を明示してFKを満たす。
                self.db.flush()

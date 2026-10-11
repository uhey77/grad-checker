"""検証済みマスタの原子的な追加投入。同じ内容の再投入は変更しない。"""

from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from pydantic import ValidationError
from sqlalchemy import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session, select

from app.application.errors.master_seed import SeedError
from app.application.master_seed import (
    AcademicProgramData,
    ClassificationData,
    CourseData,
    CourseOfferingData,
    CurriculumCourseData,
    CurriculumData,
    MasterSeed,
    validate_master,
)
from app.infrastructure.master_models import (
    AcademicProgram,
    Classification,
    Course,
    CourseOffering,
    Curriculum,
    CurriculumCourse,
)

TABLE_MAPPING = (
    ("academic_programs", AcademicProgram, AcademicProgramData),
    ("curricula", Curriculum, CurriculumData),
    ("classifications", Classification, ClassificationData),
    ("courses", Course, CourseData),
    ("course_offerings", CourseOffering, CourseOfferingData),
    ("curriculum_courses", CurriculumCourse, CurriculumCourseData),
)


def record_key(
    record: AcademicProgramData
    | CurriculumData
    | ClassificationData
    | CourseData
    | CourseOfferingData
    | CurriculumCourseData,
) -> tuple:
    if isinstance(record, CourseOfferingData):
        return (
            record.course_id,
            record.term_code,
            record.semester_order,
            record.academic_year,
        )
    if isinstance(record, CurriculumCourseData):
        return record.curriculum_id, record.course_id
    return (record.id,)


def load_seed(path: Path) -> MasterSeed:
    try:
        return MasterSeed.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError) as error:
        raise SeedError("シードファイルをUTF-8で読み込めません。") from error
    except ValidationError as error:
        locations = [
            ".".join(map(str, entry["loc"])) or "JSON" for entry in error.errors()
        ]
        raise SeedError(
            "シードの形式・型・値が不正です。確認箇所: " + ", ".join(locations)
        ) from error


def seed_master(engine: Engine, seed: MasterSeed) -> dict[str, int]:
    # 入力内の重複を先に拒否する。参照は既存DBを使えるため、ここでは検証しない。
    for name, _, _ in TABLE_MAPPING:
        keys = [record_key(record) for record in getattr(seed, name)]
        if len(keys) != len(set(keys)):
            raise SeedError(f"{name}の投入データが重複しています。")
    inserted = {name: 0 for name, _, _ in TABLE_MAPPING}
    try:
        with Session(engine) as session:
            # 検証から投入完了まで書込ロックを保持し、並行シードの競合を防ぐ。
            session.connection().exec_driver_sql("BEGIN IMMEDIATE")
            combined = {}
            additions = {}
            for name, model, schema in TABLE_MAPPING:
                existing = [
                    schema.model_validate(
                        row.model_dump(include=set(schema.model_fields))
                    )
                    for row in session.exec(select(model)).all()
                ]
                by_key = {record_key(record): record for record in existing}
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
                combined[name] = existing + new
                additions[name] = new
            ordered = validate_master(MasterSeed(**combined))
            new_classifications = {record.id for record in additions["classifications"]}
            additions["classifications"] = [
                record for record in ordered if record.id in new_classifications
            ]
            for name, model, _ in TABLE_MAPPING:
                for record in additions[name]:
                    data = record.model_dump(mode="json")
                    if name == "course_offerings":
                        identity = f"grad-checker:offering:{record.course_id}:{record.term_code}:{record.semester_order}:{record.academic_year}"
                        data["id"] = str(uuid5(NAMESPACE_URL, identity))
                    session.add(model(**data))
                    # 親分類も同じテーブルなので、順序を明示してFKを満たす。
                    session.flush()
                    inserted[name] += 1
            session.commit()
    except SQLAlchemyError as error:
        raise SeedError(
            "マスタを保存できません。DB接続・制約・競合を確認してください。全件の変更を取り消しました。"
        ) from error
    return inserted

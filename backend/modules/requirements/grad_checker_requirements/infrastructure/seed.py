"""要件マスタの読込みと原子的な追加投入。既存行の変更・削除は拒否する。"""

from pathlib import Path

from pydantic import ValidationError
from sqlalchemy import Engine
from sqlmodel import Session, select

from modules.requirements.grad_checker_requirements.application.errors.seed import (
    RequirementSeedError,
)
from modules.requirements.grad_checker_requirements.application.seed import (
    CreditRuleCourseData,
    CreditRuleData,
    CreditRuleLimitData,
    RequirementData,
    RequirementScopeData,
    RequirementSeed,
)
from modules.requirements.grad_checker_requirements.application.validation import (
    unique,
    validate_requirements,
)
from modules.requirements.grad_checker_requirements.infrastructure.models import (
    CreditRule,
    CreditRuleCourse,
    CreditRuleLimit,
    GraduationRequirement,
    RequirementScope,
)
from modules.shared.grad_checker_shared.infrastructure.transactions import (
    write_transaction,
)
from modules.subjects.grad_checker_subjects.application.subject_data_validation import (
    SubjectDataSeed,
)
from modules.subjects.grad_checker_subjects.infrastructure.subject_data_import import (
    TABLE_MAPPING as SUBJECT_MAPPING,
)

TABLE_MAPPING = (
    ("graduation_requirements", GraduationRequirement, RequirementData),
    ("requirement_scopes", RequirementScope, RequirementScopeData),
    ("credit_rules", CreditRule, CreditRuleData),
    ("credit_rule_courses", CreditRuleCourse, CreditRuleCourseData),
    ("credit_rule_limits", CreditRuleLimit, CreditRuleLimitData),
)


def record_key(record) -> tuple:
    if isinstance(record, CreditRuleCourseData):
        return record.rule_id, record.course_id
    return (record.id,)


def load_requirement_seed(path: Path) -> RequirementSeed:
    try:
        return RequirementSeed.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError) as error:
        raise RequirementSeedError("要件シードをUTF-8で読み込めません。") from error
    except ValidationError as error:
        locations = [
            ".".join(map(str, entry["loc"])) or "JSON" for entry in error.errors()
        ]
        raise RequirementSeedError(
            "要件シードの形式・型・値が不正です。確認箇所: " + ", ".join(locations)
        ) from error


def import_requirements(engine: Engine, seed: RequirementSeed) -> dict[str, int]:
    # model_copy等から渡されても、入口で型・値の検証を省略しない。
    seed = RequirementSeed.model_validate_json(seed.model_dump_json())
    for name, _, _ in TABLE_MAPPING:
        unique(getattr(seed, name), record_key, name)
    inserted = {name: 0 for name, _, _ in TABLE_MAPPING}
    with (
        Session(engine) as session,
        write_transaction(
            session,
            lambda _: RequirementSeedError(
                "要件マスタを保存できません。DB接続・制約・競合を確認してください。全件を取り消しました。"
            ),
        ),
    ):
        subjects = SubjectDataSeed.model_validate(
            {
                name: [
                    schema.model_validate(
                        row.model_dump(include=set(schema.model_fields))
                    )
                    for row in session.exec(select(model)).all()
                ]
                for name, model, schema in SUBJECT_MAPPING
            }
        )
        combined = {}
        additions = {}
        for name, model, schema in TABLE_MAPPING:
            existing = [
                schema.model_validate(row.model_dump())
                for row in session.exec(select(model)).all()
            ]
            by_key = {record_key(record): record for record in existing}
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
            combined[name] = existing + new
            additions[name] = new
        ordered = validate_requirements(RequirementSeed(**combined), subjects)
        new_ids = {record.id for record in additions["graduation_requirements"]}
        additions["graduation_requirements"] = [
            row for row in ordered if row.id in new_ids
        ]
        for name, model, _ in TABLE_MAPPING:
            for record in additions[name]:
                session.add(model(**record.model_dump(mode="json")))
                session.flush()
                inserted[name] += 1
    return inserted

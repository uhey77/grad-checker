"""要件マスタのシード読込みと、投入済みデータの読取り・追加。"""

from pathlib import Path

from pydantic import ValidationError
from sqlalchemy import Engine
from sqlalchemy.exc import SQLAlchemyError
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
from modules.requirements.grad_checker_requirements.infrastructure.models import (
    CreditRule,
    CreditRuleCourse,
    CreditRuleLimit,
    GraduationRequirement,
    RequirementScope,
)
from modules.shared.grad_checker_shared.infrastructure.unit_of_work import (
    SqlUnitOfWork,
)
from modules.subjects.grad_checker_subjects.application.subject_data_validation import (
    SubjectDataSeed,
)
from modules.subjects.grad_checker_subjects.infrastructure.subject_data_import import (
    SqliteSubjectDataStore,
)

TABLE_MAPPING = (
    ("graduation_requirements", GraduationRequirement, RequirementData),
    ("requirement_scopes", RequirementScope, RequirementScopeData),
    ("credit_rules", CreditRule, CreditRuleData),
    ("credit_rule_courses", CreditRuleCourse, CreditRuleCourseData),
    ("credit_rule_limits", CreditRuleLimit, CreditRuleLimitData),
)


def unavailable(_error: SQLAlchemyError) -> RequirementSeedError:
    return RequirementSeedError(
        "要件マスタを保存できません。DB接続・制約・競合を確認してください。全件を取り消しました。"
    )


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


class SqliteRequirementDataStore:
    def __init__(self, session: Session) -> None:
        self.db = session

    def subjects(self) -> SubjectDataSeed:
        return SqliteSubjectDataStore(self.db).load()

    def load(self) -> RequirementSeed:
        return RequirementSeed.model_validate(
            {
                name: [
                    schema.model_validate(row.model_dump())
                    for row in self.db.exec(select(model)).all()
                ]
                for name, model, schema in TABLE_MAPPING
            }
        )

    def insert(self, additions: RequirementSeed) -> None:
        for name, model, _ in TABLE_MAPPING:
            for record in getattr(additions, name):
                self.db.add(model(**record.model_dump(mode="json")))
                # 親要件も同じテーブルなので、順序を明示してFKを満たす。
                self.db.flush()


class SqliteRequirementUnitOfWork(SqlUnitOfWork):
    def __init__(self, engine: Engine) -> None:
        super().__init__(engine, unavailable)

    @property
    def requirements(self) -> SqliteRequirementDataStore:
        return SqliteRequirementDataStore(self.session)

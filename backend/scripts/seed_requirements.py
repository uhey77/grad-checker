"""卒業要件・規則の追加投入CLI。科目シード投入後に使用する。"""

import argparse
import json
import sys
from pathlib import Path

from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from config.settings import Settings
from modules.requirements.grad_checker_requirements.application.errors.seed import (
    RequirementSeedError,
)
from modules.requirements.grad_checker_requirements.application.seed_import import (
    import_requirements,
)
from modules.requirements.grad_checker_requirements.infrastructure.schema import (
    create_requirement_schema,
)
from modules.requirements.grad_checker_requirements.infrastructure.seed import (
    SqliteRequirementUnitOfWork,
    load_requirement_seed,
)
from modules.subjects.grad_checker_subjects.infrastructure.database import (
    create_database_engine,
    create_database_schema,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="卒業要件・算入規則を検証し、1トランザクションで追加投入します。"
    )
    parser.add_argument("--file", type=Path, required=True, help="UTF-8のJSONシード")
    arguments = parser.parse_args()
    engine = None
    try:
        seed = load_requirement_seed(arguments.file)
        engine = create_database_engine(Settings().database_url)
        create_database_schema(engine)
        create_requirement_schema(engine)
        result = import_requirements(SqliteRequirementUnitOfWork(engine), seed)
    except (
        RequirementSeedError,
        SQLAlchemyError,
        ValueError,
        ValidationError,
    ) as error:
        print(
            str(error)
            if isinstance(error, RequirementSeedError)
            else "DBの設定・初期化またはマスタの検証に失敗しました。",
            file=sys.stderr,
        )
        return 1
    finally:
        if engine is not None:
            engine.dispose()
    print("投入が完了しました。追加件数: " + json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

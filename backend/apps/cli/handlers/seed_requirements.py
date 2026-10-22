"""卒業要件・規則の追加投入CLI。科目シード投入後に使用する。"""

import argparse
import json
import sys
from pathlib import Path

from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from apps.settings import Settings
from modules.requirements.application.errors.seed import RequirementSeedError
from modules.requirements.composition import build_import_use_case
from modules.requirements.infrastructure.persistence.repositories.seed import (
    load_requirement_seed,
)
from modules.requirements.infrastructure.persistence.schema import (
    create_requirement_schema,
)
from modules.subjects.infrastructure.persistence.database import create_database_schema
from shared.infrastructure.persistence.database import create_database_engine


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="卒業要件・算入規則を検証し、1トランザクションで追加投入します。"
    )
    parser.add_argument("--file", type=Path, required=True, help="UTF-8のJSONシード")
    arguments = parser.parse_args(argv)
    engine = None
    try:
        seed = load_requirement_seed(arguments.file)
        engine = create_database_engine(Settings().database_url)
        create_database_schema(engine)
        create_requirement_schema(engine)
        result = build_import_use_case(engine).execute(seed)
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

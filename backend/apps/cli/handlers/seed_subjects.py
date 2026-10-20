"""開発者向け課程・科目データ投入CLI: python -m apps.cli seed-subjects --file PATH。"""

import argparse
import json
import sys
from pathlib import Path

from sqlalchemy.exc import SQLAlchemyError

from apps.settings import Settings
from modules.subjects.application.errors.subject_data import SeedError
from modules.subjects.composition import build_import_use_case
from modules.subjects.infrastructure.persistence.database import create_database_schema
from modules.subjects.infrastructure.persistence.repositories.subject_data import (
    load_seed,
)
from shared.infrastructure.persistence.database import create_database_engine


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="JSONの課程・科目データを検証し、全件を1トランザクションで追加投入します。"
    )
    parser.add_argument("--file", type=Path, required=True, help="UTF-8のJSONシード")
    arguments = parser.parse_args(argv)
    engine = None
    try:
        seed = load_seed(arguments.file)
        engine = create_database_engine(Settings().database_url)
        create_database_schema(engine)
        result = build_import_use_case(engine).execute(seed)
    except (SeedError, SQLAlchemyError, ValueError) as error:
        message = (
            str(error)
            if isinstance(error, SeedError)
            else "DBの設定または初期化に失敗しました。"
        )
        print(message, file=sys.stderr)
        return 1
    finally:
        if engine is not None:
            engine.dispose()
    print("投入が完了しました。追加件数: " + json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

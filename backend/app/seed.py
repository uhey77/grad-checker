"""開発者向け課程・科目データ投入CLI: python -m app.seed --file PATH。"""

import argparse
import json
import sys
from pathlib import Path

from sqlalchemy.exc import SQLAlchemyError

from app.application.errors.course_catalog_seed import SeedError
from app.config import Settings
from app.infrastructure.database import create_database_engine, create_database_schema
from app.infrastructure.course_catalog_seed import load_seed, seed_course_catalog


def main() -> int:
    parser = argparse.ArgumentParser(
        description="JSONの課程・科目データを検証し、全件を1トランザクションで追加投入します。"
    )
    parser.add_argument("--file", type=Path, required=True, help="UTF-8のJSONシード")
    arguments = parser.parse_args()
    engine = None
    try:
        seed = load_seed(arguments.file)
        engine = create_database_engine(Settings().database_url)
        create_database_schema(engine)
        result = seed_course_catalog(engine, seed)
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

"""開発者向けCLI。投入処理は各モジュールのUseCaseへ委譲する。"""

import argparse

from apps.cli.handlers import seed_requirements, seed_subjects


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="科目・卒業要件マスタの追加投入")
    parser.add_argument("command", choices=("seed-subjects", "seed-requirements"))
    arguments, remaining = parser.parse_known_args(argv)
    handler = (
        seed_subjects if arguments.command == "seed-subjects" else seed_requirements
    )
    return handler.main(remaining)

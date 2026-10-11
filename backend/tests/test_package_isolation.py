"""個別に同期した環境で、業務モジュールの逆依存がないことを検証する。"""

import os
import subprocess
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]


def test_subjects_environment_runs_without_api_dependencies(tmp_path: Path) -> None:
    python = (
        BACKEND
        / "modules/subjects/.venv"
        / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    )
    code = """
import importlib.util
from grad_checker_subjects.application.subject_list import list_subject_programs
from grad_checker_subjects.infrastructure.database import (
    create_database_engine, create_database_schema,
)
from grad_checker_subjects.infrastructure.subject_list import (
    SqliteSubjectListRepository,
)
from sqlmodel import Session
assert importlib.util.find_spec('fastapi') is None
assert importlib.util.find_spec('uvicorn') is None
assert importlib.util.find_spec('api_service') is None
assert importlib.util.find_spec('grad_checker_config') is None
engine = create_database_engine('sqlite:///:memory:')
try:
    create_database_schema(engine)
    with Session(engine) as session:
        assert list_subject_programs(SqliteSubjectListRepository(session)) == []
finally:
    engine.dispose()
"""
    # 一時ディレクトリから隔離モードで起動し、作業場所によるimportを避ける。
    subprocess.run([str(python), "-I", "-c", code], cwd=tmp_path, check=True)


def test_config_environment_runs_without_subjects_or_api(tmp_path: Path) -> None:
    python = (
        BACKEND
        / "config/.venv"
        / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    )
    code = """
import importlib.util
from grad_checker_config.settings import Settings, DEFAULT_DATABASE_PATH
assert importlib.util.find_spec('fastapi') is None
assert importlib.util.find_spec('sqlmodel') is None
assert importlib.util.find_spec('grad_checker_subjects') is None
assert importlib.util.find_spec('api_service') is None
assert Settings(database_url='sqlite:///:memory:').database_url == 'sqlite:///:memory:'
assert DEFAULT_DATABASE_PATH.parent.name == 'data'
assert DEFAULT_DATABASE_PATH.parent.parent.name == 'backend'
"""
    subprocess.run([str(python), "-I", "-c", code], cwd=tmp_path, check=True)

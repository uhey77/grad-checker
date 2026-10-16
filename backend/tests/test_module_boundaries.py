"""業務モジュールの依存方向と共有設定を検証する。"""

import ast
from pathlib import Path

from config.settings import DEFAULT_DATABASE_PATH, Settings

BACKEND = Path(__file__).resolve().parents[1]


def imported_modules(package: str) -> list[tuple[Path, list[str]]]:
    result = []
    for source in (BACKEND / package).rglob("*.py"):
        tree = ast.parse(source.read_text(), filename=str(source))
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module)
        result.append((source, imports))
    return result


def test_subjects_do_not_import_api_or_configuration() -> None:
    for source, imports in imported_modules("modules/subjects/grad_checker_subjects"):
        forbidden = ("api", "config", "fastapi", "uvicorn")
        assert not [name for name in imports if name.split(".")[0] in forbidden], source
        # 科目モジュールは本人データを扱うモジュールへ依存しない。
        assert not [
            name
            for name in imports
            if name.startswith(
                ("modules.accounts", "modules.grades", "modules.requirements")
            )
        ], source


def test_grades_follow_layer_dependencies() -> None:
    package = "modules/grades/grad_checker_grades"
    for source, imports in imported_modules(package):
        forbidden = ("api", "config", "fastapi", "uvicorn")
        assert not [name for name in imports if name.split(".")[0] in forbidden], source
        layer = source.relative_to(BACKEND / package).parts[0]
        if layer in ("domain", "application"):
            assert not [
                name
                for name in imports
                if ".infrastructure" in name or name.split(".")[0] in ("sqlmodel",)
            ], source
        if layer == "domain":
            assert not [name for name in imports if ".application" in name], source


def test_shared_module_does_not_depend_on_business_modules() -> None:
    package = "modules/shared/grad_checker_shared"
    for source, imports in imported_modules(package):
        forbidden = ("api", "config", "fastapi", "uvicorn")
        assert not [name for name in imports if name.split(".")[0] in forbidden], source
        # 共通処理は業務モジュールを参照せず、業務エラーへの変換は呼出し側が渡す。
        assert not [
            name
            for name in imports
            if name.startswith("modules.") and not name.startswith("modules.shared")
        ], source
        layer = source.relative_to(BACKEND / package).parts[0]
        if layer == "application":
            assert not [
                name
                for name in imports
                if ".infrastructure" in name
                or name.split(".")[0] in ("sqlalchemy", "sqlmodel")
            ], source


def test_requirements_follow_layer_dependencies() -> None:
    package = "modules/requirements/grad_checker_requirements"
    for source, imports in imported_modules(package):
        forbidden = ("api", "config", "fastapi", "uvicorn")
        assert not [name for name in imports if name.split(".")[0] in forbidden], source
        layer = source.relative_to(BACKEND / package).parts[0]
        if layer in ("domain", "application"):
            assert not [
                name
                for name in imports
                if ".infrastructure" in name
                or name.split(".")[0] in ("sqlalchemy", "sqlmodel")
            ], source
        if layer == "domain":
            assert not [name for name in imports if ".application" in name], source


def test_shared_settings_default_to_backend_data(monkeypatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert DEFAULT_DATABASE_PATH == BACKEND / "data/grad_checker.db"
    assert Settings().database_url == f"sqlite:///{DEFAULT_DATABASE_PATH}"
    assert (
        Settings(database_url="sqlite:///:memory:").database_url == "sqlite:///:memory:"
    )

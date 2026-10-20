"""業務モジュールの依存方向と共有設定を検証する。"""

import ast
from importlib.util import resolve_name
from pathlib import Path

import pytest

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
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if node.level:
                    parent = ".".join(source.parent.relative_to(BACKEND).parts)
                    module = resolve_name("." * node.level + module, parent)
                imports.append(module)
        result.append((source, imports))
    return result


@pytest.mark.parametrize("module", ["accounts", "grades", "requirements", "subjects"])
def test_all_business_layers_and_public_contracts(module: str) -> None:
    package = f"modules/{module}/grad_checker_{module}"
    prefix = package.replace("/", ".")
    for source, imports in imported_modules(package):
        layer = source.relative_to(BACKEND / package).parts[0]
        for name in imports:
            if layer in ("domain", "application"):
                assert name.split(".")[0] not in (
                    "api",
                    "config",
                    "fastapi",
                    "uvicorn",
                    "sqlalchemy",
                    "sqlmodel",
                ), (source, name)
                assert ".infrastructure" not in name, (source, name)
            if layer == "domain":
                assert ".application" not in name and not name.endswith(".public"), (
                    source,
                    name,
                )
            if layer == "infrastructure":
                assert ".presentation" not in name, (source, name)
            # モジュール間の業務契約はpublicに限定する。
            if (
                name.startswith("modules.")
                and not name.startswith((prefix + ".", "modules.shared."))
                and (".application" in name or ".domain" in name)
            ):
                pytest.fail(f"{source}: internal module contract {name}")
            if layer == "public.py":
                assert ".infrastructure" not in name, (source, name)


def test_bridge_presentation_only_uses_public_business_contracts() -> None:
    for source, imports in imported_modules("api/api_service/presentation"):
        for name in imports:
            assert name.split(".")[0] not in ("sqlalchemy", "sqlmodel", "config"), (
                source,
                name,
            )
            if name.startswith("modules."):
                assert name.endswith(".public") or name.startswith(
                    "modules.shared.grad_checker_shared.application."
                ), (source, name)


def test_application_time_is_supplied_as_a_dependency() -> None:
    for source in (BACKEND / "modules").rglob("*.py"):
        if "application" in source.parts:
            assert "datetime.now(" not in source.read_text(), source


def test_business_models_do_not_use_dataclasses() -> None:
    for source, imports in imported_modules("modules"):
        assert "dataclasses" not in imports, source


@pytest.mark.parametrize("module", ["accounts", "grades", "requirements", "subjects"])
def test_public_operations_are_individual_use_cases(module: str) -> None:
    package = BACKEND / f"modules/{module}/grad_checker_{module}"
    public = ast.parse((package / "public.py").read_text())
    exported = {
        alias.name
        for node in public.body
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    }
    cases = []
    for source in (package / "application/use_cases").glob("*.py"):
        for node in ast.parse(source.read_text()).body:
            if isinstance(node, ast.ClassDef):
                cases.append(node.name)
                assert node.name.endswith("UseCase"), source
                assert node.name in exported, source
                methods = {
                    item.name
                    for item in node.body
                    if isinstance(item, ast.FunctionDef)
                    and not item.name.startswith("_")
                }
                assert methods == {"execute"}, source
    assert cases, module
    assert not any(name.endswith("Service") for name in exported), module


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


@pytest.mark.parametrize("module", ["subjects", "accounts"])
def test_application_does_not_depend_on_database(module: str) -> None:
    package = f"modules/{module}/grad_checker_{module}"
    for source, imports in imported_modules(package):
        layer = source.relative_to(BACKEND / package).parts[0]
        if layer in ("domain", "application"):
            assert not [
                name
                for name in imports
                if ".infrastructure" in name
                or name.split(".")[0] in ("sqlalchemy", "sqlmodel")
            ], source


def test_only_unit_of_work_controls_transactions() -> None:
    # リポジトリはトランザクションの開始・確定・取消をUnit of Workに任せる。
    shared = BACKEND / "modules/shared/grad_checker_shared"
    for source in (BACKEND / "modules").rglob("*.py"):
        if source.is_relative_to(shared):
            continue
        code = source.read_text()
        for statement in (".commit(", ".rollback(", 'exec_driver_sql("BEGIN'):
            assert statement not in code, source


def test_application_contracts_are_abstract_base_classes() -> None:
    # 取得・保存の契約はABCで定義し、実装とFakeに継承で明示させる。
    for source in (BACKEND / "modules").rglob("*.py"):
        if "application" in source.parts:
            assert "Protocol" not in source.read_text(), source


def test_shared_settings_default_to_backend_data(monkeypatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert DEFAULT_DATABASE_PATH == BACKEND / "data/grad_checker.db"
    assert Settings().database_url == f"sqlite:///{DEFAULT_DATABASE_PATH}"
    assert (
        Settings(database_url="sqlite:///:memory:").database_url == "sqlite:///:memory:"
    )

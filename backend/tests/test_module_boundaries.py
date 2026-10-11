"""業務モジュールの依存方向と共有設定を検証する。"""

import ast
from pathlib import Path

from config.settings import DEFAULT_DATABASE_PATH, Settings

BACKEND = Path(__file__).resolve().parents[1]


def test_subjects_do_not_import_api_or_configuration() -> None:
    for source in (BACKEND / "modules/subjects/grad_checker_subjects").rglob("*.py"):
        tree = ast.parse(source.read_text(), filename=str(source))
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module)
        forbidden = ("api", "config", "fastapi", "uvicorn")
        assert not [name for name in imports if name.split(".")[0] in forbidden], source


def test_shared_settings_default_to_backend_data(monkeypatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert DEFAULT_DATABASE_PATH == BACKEND / "data/grad_checker.db"
    assert Settings().database_url == f"sqlite:///{DEFAULT_DATABASE_PATH}"
    assert (
        Settings(database_url="sqlite:///:memory:").database_url == "sqlite:///:memory:"
    )

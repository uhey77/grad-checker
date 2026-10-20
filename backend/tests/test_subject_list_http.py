"""実プロセスのGo外部API → Pythonユースケース → 一時SQLiteを検証する。"""

import json
import os
import shutil
import socket
import subprocess
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4

import pytest
from sqlalchemy import text

from modules.subjects.grad_checker_subjects.infrastructure.database import (
    create_database_engine,
    create_database_schema,
)
from modules.subjects.grad_checker_subjects.infrastructure.subject_data_import import (
    SqliteSubjectDataUnitOfWork,
    load_seed,
)
from modules.subjects.grad_checker_subjects.public import ImportSubjectDataUseCase

BACKEND = Path(__file__).resolve().parents[1]
BASE = "/api/dev/subject-list"


def unused_port():
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


def request(port, path, payload=None, method=None):
    data = None if payload is None else json.dumps(payload).encode()
    req = Request(
        f"http://127.0.0.1:{port}{path}",
        data=data,
        method=method,
        headers={"Content-Type": "application/json"} if data else {},
    )
    try:
        response = urlopen(req, timeout=2)
    except HTTPError as error:
        response = error
    with response:
        body = response.read()
        return response.status, json.loads(body), response.headers


def wait_for_server(process, log_path, probe):
    for _ in range(100):
        if process.poll() is not None:
            pytest.fail(log_path.read_text())
        try:
            if probe():
                return
        except OSError, URLError:
            pass
        time.sleep(0.05)
    pytest.fail("Server startup timed out: " + log_path.read_text())


@pytest.fixture
def services(tmp_path_factory):
    go = shutil.which("go")
    if go is None:
        pytest.skip("Goが必要です。GoをPATHに追加してbackend-testを実行してください。")
    directory = tmp_path_factory.mktemp("subject-list-http")
    binary = directory / ("api.exe" if os.name == "nt" else "api")
    subprocess.run(
        [go, "build", "-o", str(binary), "."], cwd=BACKEND / "api", check=True
    )
    db_url = f"sqlite:///{directory / 'test.db'}"
    engine = create_database_engine(db_url)
    create_database_schema(engine)
    ImportSubjectDataUseCase(SqliteSubjectDataUnitOfWork(engine)).execute(
        load_seed(BACKEND / "seeds/cs_2026.json")
    )
    ports = [unused_port() for _ in range(3)]
    python_port, external_port, disabled_port = ports
    processes = []
    logs = []
    try:
        commands = [
            [
                str(
                    BACKEND
                    / ".venv"
                    / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
                ),
                "-m",
                "uvicorn",
                "api.api_service.main:app",
                "--app-dir",
                str(BACKEND),
                "--host",
                "127.0.0.1",
                "--port",
                str(python_port),
            ],
            [
                str(binary),
                "-listen",
                f"127.0.0.1:{external_port}",
                "-python-url",
                f"http://127.0.0.1:{python_port}",
                "-subject-list-preview",
            ],
            [
                str(binary),
                "-listen",
                f"127.0.0.1:{disabled_port}",
                "-python-url",
                f"http://127.0.0.1:{python_port}",
            ],
        ]
        for index, command in enumerate(commands):
            path = directory / f"server-{index}.log"
            log = path.open("w")
            logs.append(log)
            process = subprocess.Popen(
                command,
                cwd=BACKEND,
                env={**os.environ, "DATABASE_URL": db_url},
                stdout=log,
                stderr=subprocess.STDOUT,
            )
            processes.append(process)
            if index == 0:

                def probe():
                    return (
                        request(
                            python_port,
                            "/bridge/subject-list",
                            {"operation": "list_programs"},
                        )[0]
                        == 200
                    )
            else:
                port = ports[index]

                def probe(port=port):
                    return request(port, "/api/health")[0] == 200

            wait_for_server(process, path, probe)
        yield python_port, external_port, disabled_port, engine
    finally:
        for process in processes:
            process.terminate()
        for process in processes:
            try:
                process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=3)
        for log in logs:
            log.close()
        engine.dispose()


def test_external_results_match_python_use_cases(services):
    python_port, external_port, _, _engine = services
    status, programs, headers = request(external_port, BASE + "/programs")
    assert status == 200
    assert headers["Cache-Control"] == "no-store"
    assert len(programs) == 4
    assert (
        programs
        == request(python_port, "/bridge/subject-list", {"operation": "list_programs"})[
            1
        ]["data"]
    )
    for program in programs:
        identifier = program["curriculum_id"]
        status, result, headers = request(external_port, BASE + "/" + identifier)
        assert status == 200
        assert len(result["courses"]) == (
            120 if program["specialization_name"] == "社会情報専攻" else 126
        )
        assert (
            result
            == request(
                python_port,
                "/bridge/subject-list",
                {"operation": "get_subject_list", "curriculum_id": identifier},
            )[1]["data"]
        )
        assert headers["Cache-Control"] == "no-store"


def test_external_validation_and_bridge_boundary(services):
    python_port, external_port, disabled_port, _engine = services
    assert request(external_port, BASE + "/invalid")[:2] == (
        422,
        {"detail": "カリキュラムIDの形式が不正です。"},
    )
    assert request(external_port, BASE + "/" + str(uuid4()))[:2] == (
        404,
        {"detail": "選択したカリキュラムが見つかりません。"},
    )
    assert request(external_port, BASE + "/programs", method="POST")[0] == 405
    assert request(disabled_port, BASE + "/programs")[0] == 404
    assert request(python_port, BASE + "/programs")[0] == 404
    assert (
        request(external_port, "/bridge/subject-list", {"operation": "list_programs"})[
            0
        ]
        == 404
    )


def test_database_errors_are_mapped_by_go(services):
    python_port, external_port, _, engine = services
    identifier = request(external_port, BASE + "/programs")[1][0]["curriculum_id"]
    with engine.begin() as connection:
        first, second = (
            connection.execute(
                text(
                    "SELECT DISTINCT classification_id FROM curriculum_courses "
                    "WHERE curriculum_id = :id LIMIT 2"
                ),
                {"id": identifier},
            )
            .scalars()
            .all()
        )
        connection.execute(
            text(
                "UPDATE classifications SET parent_id = "
                "CASE WHEN id = :first THEN :second ELSE :first END "
                "WHERE id IN (:first, :second)"
            ),
            {"first": first, "second": second},
        )
    assert request(
        python_port,
        "/bridge/subject-list",
        {"operation": "get_subject_list", "curriculum_id": identifier},
    )[1] == {"error": {"code": "classification_inconsistent"}}
    assert request(external_port, BASE + "/" + identifier)[0] == 409
    with engine.begin() as connection:
        connection.execute(text("DROP TABLE curriculum_courses"))
    assert request(
        python_port,
        "/bridge/subject-list",
        {"operation": "get_subject_list", "curriculum_id": identifier},
    )[1] == {"error": {"code": "subject_list_unavailable"}}
    assert request(external_port, BASE + "/" + identifier)[:2] == (
        503,
        {"detail": "科目データを読み込めません。時間をおいて再試行してください。"},
    )

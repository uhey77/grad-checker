"""200科目のGo外部API・ブリッジ・Python判定・DBを計測する開発専用CLI。

実行: uv run --locked python -m scripts.benchmark_graduation --iterations 10
本番/開発DBには接続せず、一時ディレクトリにSQLiteとサーバーを作成する。
"""

import argparse
import json
import os
import platform
import shutil
import socket
import sqlite3
import statistics
import subprocess
import sys
import tempfile
import time
from contextlib import ExitStack
from datetime import UTC, datetime
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

import httpx
from sqlalchemy import text

from modules.accounts.grad_checker_accounts.infrastructure.schema import (
    create_account_schema,
)
from modules.grades.grad_checker_grades.infrastructure.schema import create_grade_schema
from modules.requirements.grad_checker_requirements.application import (
    student_evaluation,
)
from modules.requirements.grad_checker_requirements.infrastructure.evaluation import (
    SqliteEvaluationUnitOfWork,
)
from modules.requirements.grad_checker_requirements.infrastructure.schema import (
    create_requirement_schema,
)
from modules.requirements.grad_checker_requirements.infrastructure.seed import (
    SqliteRequirementUnitOfWork,
    load_requirement_seed,
)
from modules.requirements.grad_checker_requirements.public import (
    ImportRequirementsUseCase,
)
from modules.subjects.grad_checker_subjects.application.subject_data_validation import (
    SubjectDataSeed,
)
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
ORIGIN = "http://127.0.0.1:5173"
TARGET_COURSES = 200


def make_seed() -> tuple[SubjectDataSeed, str, str, list[str]]:
    """便覧の1課程を、任意IDの選択科目を補ってちょうど200件にする。"""
    seed = load_seed(BACKEND / "seeds/cs_2026.json")
    curriculum = seed.curricula[0]
    program_id = str(curriculum.program_id)
    curriculum_id = str(curriculum.id)
    data = seed.model_dump(mode="json")
    associations = [
        row
        for row in data["curriculum_courses"]
        if row["curriculum_id"] == curriculum_id
    ]
    electives = [row for row in associations if row["course_type"] == "elective"]
    courses = {row["id"]: row for row in data["courses"]}
    if not electives or len(associations) > TARGET_COURSES:
        raise ValueError("選択科目または対象課程の件数が想定外です。")
    for index in range(TARGET_COURSES - len(associations)):
        template = electives[index % len(electives)]
        source = courses[template["course_id"]]
        identifier = str(uuid5(NAMESPACE_URL, f"grad-checker:perf:45:{index}"))
        data["courses"].append(
            {
                **source,
                "id": identifier,
                "code": f"PERF45-{index:03d}",
                "name": f"性能確認用選択科目{index + 1:03d}",
            }
        )
        data["curriculum_courses"].append(
            {
                **template,
                "course_id": identifier,
                "display_order": 50000 + index,
            }
        )
    selected = [
        row["course_id"]
        for row in data["curriculum_courses"]
        if row["curriculum_id"] == curriculum_id
    ]
    assert len(selected) == TARGET_COURSES and len(set(selected)) == TARGET_COURSES
    return SubjectDataSeed.model_validate(data), program_id, curriculum_id, selected


def port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def timed(call):
    start = time.perf_counter_ns()
    result = call()
    return (time.perf_counter_ns() - start) / 1_000_000, result


def summary(samples: list[float]) -> dict[str, float]:
    ordered = sorted(samples)
    return {
        "min_ms": round(ordered[0], 3),
        "median_ms": round(statistics.median(ordered), 3),
        "p95_ms": round(ordered[max(0, (95 * len(ordered) + 99) // 100 - 1)], 3),
        "max_ms": round(ordered[-1], 3),
    }


def request(client, method: str, url: str, **kwargs):
    response = client.request(method, url, **kwargs)
    response.raise_for_status()
    return response.json()


def wait_ready(client, url, process, log):
    for _ in range(150):
        if process.poll() is not None:
            raise RuntimeError(f"起動失敗: {log.read_text(encoding='utf-8')}")
        try:
            if client.get(url, timeout=0.3).status_code == 200:
                return
        except httpx.RequestError, httpx.TimeoutException:
            pass
        time.sleep(0.1)
    raise RuntimeError(f"起動タイムアウト: {log.read_text(encoding='utf-8')}")


def run(iterations: int) -> dict:  # noqa: PLR0912, PLR0914, PLR0915
    if iterations < 2:
        raise ValueError("反復は2回以上指定してください。")
    go = shutil.which("go")
    if go is None:
        raise RuntimeError("Goが必要です。Goのインストールを確認してください。")
    seed, program_id, curriculum_id, selected = make_seed()
    requirements = load_requirement_seed(BACKEND / "seeds/cs_requirements_2026.json")
    with tempfile.TemporaryDirectory(prefix="grad-checker-perf-") as directory:
        temp = Path(directory)
        engine = create_database_engine(f"sqlite:///{temp / 'benchmark.db'}")
        try:
            # 実サーバー起動前にマスタを既存の正式シード手順で投入する。
            # 一時DBを初期化した後、サーバー起動時にも既存スキーマを確認する。
            create_database_schema(engine)
            create_account_schema(engine)
            create_grade_schema(engine)
            create_requirement_schema(engine)
            ImportSubjectDataUseCase(SqliteSubjectDataUnitOfWork(engine)).execute(seed)
            ImportRequirementsUseCase(SqliteRequirementUnitOfWork(engine)).execute(
                requirements
            )
            binary = temp / "grad-checker-api"
            subprocess.run(
                [go, "build", "-o", str(binary), "./api"], cwd=BACKEND, check=True
            )
            python_port, go_port = port(), port()
            while python_port == go_port:
                go_port = port()
            env = {
                **os.environ,
                "DATABASE_URL": f"sqlite:///{temp / 'benchmark.db'}",
                "PUBLIC_ORIGIN": ORIGIN,
            }
            commands = [
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "api.api_service.main:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(python_port),
                ],
                [
                    str(binary),
                    "-listen",
                    f"127.0.0.1:{go_port}",
                    "-python-url",
                    f"http://127.0.0.1:{python_port}",
                ],
            ]
            with ExitStack() as stack:
                processes = []
                for index, command in enumerate(commands):
                    log_path = temp / f"service-{index}.log"
                    log = stack.enter_context(log_path.open("w+", encoding="utf-8"))
                    process = subprocess.Popen(
                        command,
                        cwd=BACKEND,
                        env=env,
                        stdout=log,
                        stderr=subprocess.STDOUT,
                    )
                    processes.append(process)
                    stack.callback(stop_process, process)
                    with httpx.Client() as probe:
                        if index == 0:
                            # FastAPIの公開healthはないためbridgeを待つ。
                            for _ in range(150):
                                if process.poll() is not None:
                                    raise RuntimeError("Python起動失敗")
                                try:
                                    r = probe.post(
                                        f"http://127.0.0.1:{python_port}/bridge/auth",
                                        json={"operation": "config"},
                                        timeout=0.4,
                                    )
                                    if r.status_code == 200:
                                        break
                                except httpx.RequestError:
                                    pass
                                time.sleep(0.1)
                            else:
                                raise RuntimeError("Python起動タイムアウト")
                        else:
                            wait_ready(
                                probe,
                                f"http://127.0.0.1:{go_port}/api/health",
                                process,
                                log_path,
                            )
                with httpx.Client(
                    base_url=f"http://127.0.0.1:{go_port}",
                    headers={"Origin": ORIGIN},
                    timeout=30,
                ) as client:
                    credentials = {
                        "login_name": "benchmark45",
                        "password": "benchmark-password-123",
                    }
                    request(client, "POST", "/api/auth/register", json=credentials)
                    auth = request(client, "POST", "/api/auth/login", json=credentials)
                    headers = {"X-CSRF-Token": auth["csrf_token"]}
                    session_token = client.cookies["grad_checker_session"]
                    profile = request(
                        client,
                        "PUT",
                        "/api/me/program",
                        headers=headers,
                        json={
                            "program_id": program_id,
                            "curriculum_id": curriculum_id,
                            "expected_revision": 0,
                        },
                    )
                    grades = [
                        {
                            "course_id": key,
                            "attempt_no": 1,
                            "result_status": "finalized",
                            "grade_code": "A",
                            "academic_year": 2026,
                            "term_code": "first",
                        }
                        for key in selected
                    ]
                    saved = request(
                        client,
                        "PUT",
                        "/api/me/grades",
                        headers=headers,
                        json={
                            "grades": grades,
                            "expected_revision": profile["data_revision"],
                        },
                    )
                    revision = saved["data_revision"]
                    bridge = httpx.Client(
                        base_url=f"http://127.0.0.1:{python_port}", timeout=30
                    )
                    stack.callback(bridge.close)
                    times = {
                        key: []
                        for key in (
                            "external_get",
                            "external_post",
                            "bridge_get",
                            "db_snapshot",
                            "python_evaluation",
                        )
                    }
                    db_uow = SqliteEvaluationUnitOfWork(engine)
                    # 初回計測はウォームアップと分離してコールドリクエストとして記録。
                    cold, first = timed(
                        lambda: request(
                            client, "GET", "/api/me/graduation-requirements"
                        )
                    )
                    assert first["data_revision"] == revision
                    bridge_payload = {"token": session_token}
                    for _ in range(iterations):
                        value, data = timed(
                            lambda: request(
                                client, "GET", "/api/me/graduation-requirements"
                            )
                        )
                        assert data["data_revision"] == revision
                        times["external_get"].append(value)
                        value, data = timed(
                            lambda: request(
                                client,
                                "POST",
                                "/api/checks",
                                headers=headers,
                                json={"expected_revision": revision},
                            )
                        )
                        assert data["input"]["data_revision"] == revision
                        times["external_post"].append(value)
                        value, data = timed(
                            lambda: request(
                                bridge,
                                "POST",
                                "/bridge/graduation-requirements",
                                json=bridge_payload,
                            )
                        )
                        assert data["data"]["data_revision"] == revision
                        times["bridge_get"].append(value)

                        def read_snapshot():
                            with db_uow.read():
                                return db_uow.evaluation.get_snapshot(
                                    auth["student"]["id"]
                                )

                        value, data = timed(read_snapshot)
                        times["db_snapshot"].append(value)
                        value, data = timed(
                            lambda snapshot=data: student_evaluation.evaluate_student(
                                snapshot, datetime.now(UTC)
                            )
                        )
                        assert data.data_revision == revision
                        times["python_evaluation"].append(value)
                    with engine.connect() as conn:
                        history = conn.execute(
                            text("SELECT count(*) FROM check_results")
                        ).scalar_one()
                    assert history == iterations
                    return {
                        "environment": {
                            "os": platform.platform(),
                            "python": platform.python_version(),
                            "go": subprocess.check_output(
                                [go, "version"], text=True
                            ).strip(),
                            "sqlite": sqlite3.sqlite_version,
                            "cpu": platform.processor() or "unknown",
                        },
                        "dataset": {
                            "curriculum_courses": len(selected),
                            "master_courses_all": len(seed.courses),
                            "grade_attempts": len(grades),
                            "stored_checks": history,
                            "synthetic_electives": TARGET_COURSES - 126,
                            "seed": "cs_2026.json + cs_requirements_2026.json",
                        },
                        "conditions": {
                            "cold": "初回GET（プロセス起動とマスタ投入完了後）",
                            "warm": f"同一プロセスで各API {iterations}回",
                            "scope": (
                                "localhost Go→bridge HTTP→Python→SQLite; "
                                "POSTはcommitまで"
                            ),
                            "segments": "区間は独立測定で、合計して全体時間にはしない",
                        },
                        "cold_external_get_ms": round(cold, 3),
                        "warm": {
                            key: summary(samples) for key, samples in times.items()
                        },
                        "satisfies_1s": all(
                            max(times[key]) <= 1000
                            for key in ("external_get", "external_post")
                        ),
                    }
        finally:
            engine.dispose()


def stop_process(process):
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iterations", type=int, default=10)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run(args.iterations)
    serialized = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    print(serialized)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized, encoding="utf-8")
    return 0 if result["satisfies_1s"] else 1


if __name__ == "__main__":
    sys.exit(main())

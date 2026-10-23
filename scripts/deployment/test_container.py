"""ローカルのTLS PostgreSQLと512MiBコンテナで本番構成を検証する。"""

import json
import subprocess
import sys
import time
from pathlib import Path
from uuid import uuid4

import httpx

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))


def docker(*args, check=True):
    result = subprocess.run(
        ["docker", *args], capture_output=True, text=True, check=check
    )
    return result.stdout.strip()


def wait(url, timeout=180):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            if httpx.get(url, timeout=4).status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(0.5)
    raise RuntimeError("Container readiness timed out")


def main():
    from migrations.schema import initialize_schema
    from modules.requirements.infrastructure.persistence.unit_of_work import (
        SqliteRequirementUnitOfWork,
    )
    from modules.requirements.public import ImportRequirementsUseCase
    from modules.subjects.infrastructure.persistence.unit_of_work import (
        SqliteSubjectDataUnitOfWork,
    )
    from modules.subjects.public import ImportSubjectDataUseCase
    from shared.infrastructure.persistence.database import create_database_engine
    from tests.unit.test_requirement_evaluation import snapshot as snapshot_fixture

    image = sys.argv[1] if len(sys.argv) > 1 else "grad-checker-production:test"
    suffix = uuid4().hex[:12]
    network, postgres, app = (
        f"grad-checker-{kind}-{suffix}" for kind in ("net", "pg", "api")
    )
    engine = None
    try:
        docker("network", "create", network)
        docker(
            "run",
            "--detach",
            "--name",
            postgres,
            "--network",
            network,
            "--network-alias",
            "postgres",
            "-p",
            "127.0.0.1::5432",
            "-e",
            "POSTGRES_HOST_AUTH_METHOD=trust",
            "-e",
            "POSTGRES_DB=smoke",
            "--entrypoint",
            "sh",
            "postgres:18",
            "-ec",
            "if [ ! -f /tmp/server.key ]; then "
            "openssl req -new -x509 -nodes -days 1 -subj /CN=postgres "
            "-out /tmp/server.crt -keyout /tmp/server.key >/dev/null 2>&1; fi; "
            "chown postgres:postgres /tmp/server.key; chmod 600 /tmp/server.key; "
            "exec docker-entrypoint.sh postgres -c ssl=on "
            "-c ssl_cert_file=/tmp/server.crt -c ssl_key_file=/tmp/server.key",
        )
        pg_port = docker("port", postgres, "5432").rsplit(":", 1)[1]
        for _ in range(100):
            if (
                subprocess.run(
                    [
                        "docker",
                        "exec",
                        postgres,
                        "pg_isready",
                        "-h",
                        "127.0.0.1",
                        "-U",
                        "postgres",
                    ],
                    capture_output=True,
                ).returncode
                == 0
            ):
                break
            time.sleep(0.5)
        else:
            raise RuntimeError("Test PostgreSQL failed to start")
        engine = create_database_engine(
            f"postgresql://postgres@127.0.0.1:{pg_port}/smoke?sslmode=require"
        )
        initialize_schema(engine, apply=True)
        snapshot = getattr(snapshot_fixture, "__wrapped__")()
        ImportSubjectDataUseCase(SqliteSubjectDataUnitOfWork(engine)).execute(
            snapshot.subjects
        )
        ImportRequirementsUseCase(SqliteRequirementUnitOfWork(engine)).execute(
            snapshot.requirements
        )
        origin = "https://grad-checker-chi.vercel.app"
        docker(
            "run",
            "--detach",
            "--name",
            app,
            "--network",
            network,
            "--memory",
            "512m",
            "--cpus",
            "1",
            "-p",
            "127.0.0.1::8080",
            "-e",
            "DATABASE_URL=postgresql://postgres@postgres/smoke?sslmode=require",
            "-e",
            f"PUBLIC_ORIGIN={origin}",
            "-e",
            "PORT=8080",
            image,
        )
        port = docker("port", app, "8080").rsplit(":", 1)[1]
        base = f"http://127.0.0.1:{port}"
        wait(base + "/api/ready")
        assert docker("exec", app, "id", "-u") == "10001"
        assert httpx.get(base + "/bridge/health").status_code == 404
        assert httpx.get(base + "/api/dev/subject-list/programs").status_code == 404
        assert httpx.get(base + "/docs").status_code == 404
        docker(
            "exec",
            app,
            "python",
            "-c",
            "import socket; s=socket.socket(); s.settimeout(1); "
            "assert s.connect_ex((socket.gethostbyname(socket.gethostname()),8001)) != 0",
        )
        password = "container-test-password-123"
        with httpx.Client(
            base_url=base, headers={"Origin": origin}, timeout=15
        ) as client:
            credentials = {"login_name": "container_owner", "password": password}
            bad = client.post(
                "/api/auth/register",
                json=credentials,
                headers={"Origin": "https://evil.example"},
            )
            assert bad.status_code == 403
            registered = client.post("/api/auth/register", json=credentials)
            assert registered.status_code == 201
            auth = client.post("/api/auth/login", json=credentials)
            auth.raise_for_status()
            cookie = auth.headers["set-cookie"].lower()
            assert (
                "httponly" in cookie and "secure" in cookie and "samesite=lax" in cookie
            )
            assert "session_token" not in auth.json()
            # ローカルHTTPでの検証だけ、Secure Cookieを明示転送する。本番はVercelのHTTPS。
            session = auth.cookies.get("grad_checker_session")
            client.headers["Cookie"] = f"grad_checker_session={session}"
            headers = {"X-CSRF-Token": auth.json()["csrf_token"]}
            selection = {
                "program_id": str(snapshot.program_id),
                "curriculum_id": str(snapshot.curriculum_id),
                "expected_revision": 0,
            }
            assert client.put("/api/me/program", json=selection).status_code == 403
            assert (
                client.put(
                    "/api/me/program", json=selection, headers=headers
                ).status_code
                == 200
            )
            from tests.unit.test_requirement_evaluation import grade, uid

            attempts = [grade(uid(i)).model_dump() for i in (10, 11, 13, 15)]
            grades = client.put(
                "/api/me/grades",
                headers=headers,
                json={"expected_revision": 1, "grades": attempts},
            )
            assert grades.status_code == 200
            assert (
                client.get("/api/me/graduation-requirements").json()["result"] == "pass"
            )
            check = client.post(
                "/api/checks", headers=headers, json={"expected_revision": 2}
            )
            assert check.status_code == 201
            saved = check.json()
            assert client.get(f"/api/checks/{saved['id']}").json() == saved
            assert client.get("/api/checks").json()["total_count"] == 1
            other = {"login_name": "container_other", "password": password}
            assert client.post("/api/auth/register", json=other).status_code == 201
            other_auth = client.post("/api/auth/login", json=other)
            other_auth.raise_for_status()
            assert (
                client.get(
                    f"/api/checks/{saved['id']}",
                    headers={
                        "Cookie": f"grad_checker_session={other_auth.cookies.get('grad_checker_session')}"
                    },
                ).status_code
                == 404
            )
            memory = docker("stats", "--no-stream", "--format", "{{.MemUsage}}", app)
            peak = docker(
                "exec",
                app,
                "sh",
                "-c",
                "cat /sys/fs/cgroup/memory.peak 2>/dev/null || true",
            )
            start = time.monotonic()
            docker("stop", "--time", "9", app)
            duration = time.monotonic() - start
            state = json.loads(docker("inspect", "--format", "{{json .State}}", app))
            assert state["ExitCode"] == 0 and not state["OOMKilled"] and duration < 9
            docker("start", app)
            port = docker("port", app, "8080").rsplit(":", 1)[1]
            base = f"http://127.0.0.1:{port}"
            client.base_url = base
            wait(base + "/api/ready")
            assert client.get(f"/api/checks/{saved['id']}").json() == saved
            docker("stop", postgres)
            assert client.get("/api/ready").status_code == 503
            assert client.get("/api/health").status_code == 200
            docker("start", postgres)
            wait(base + "/api/ready")
            # 子プロセスだけが死んだ場合もコンテナを失敗として終了させる。
            docker(
                "exec",
                app,
                "python",
                "-c",
                "import os,signal; "
                "pids=[int(p) for p in os.listdir('/proc') if p.isdigit()]; "
                "pid=next(p for p in pids if b'uvicorn' in open(f'/proc/{p}/cmdline','rb').read() and p != os.getpid()); "
                "os.kill(pid,signal.SIGTERM)",
            )
            for _ in range(100):
                if docker("inspect", "--format", "{{.State.Running}}", app) == "false":
                    break
                time.sleep(0.1)
            assert docker("inspect", "--format", "{{.State.ExitCode}}", app) == "1"
            print(
                json.dumps(
                    {
                        "result": "passed",
                        "memory_limit": "512MiB",
                        "memory_usage": memory,
                        "peak_bytes": peak,
                        "shutdown_seconds": round(duration, 2),
                        "flows": [
                            "readiness",
                            "TLS PostgreSQL",
                            "secure cookie",
                            "CSRF",
                            "owner isolation",
                            "grades",
                            "graduation",
                            "history",
                            "restart persistence",
                            "dependency failure",
                            "child failure",
                        ],
                    }
                )
            )
        return 0
    finally:
        if engine is not None:
            engine.dispose()
        for name in (app, postgres):
            docker("rm", "--force", name, check=False)
        docker("network", "rm", network, check=False)


if __name__ == "__main__":
    raise SystemExit(main())

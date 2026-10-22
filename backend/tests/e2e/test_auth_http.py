"""実Go → Python → SQLiteの登録・ログインを検証する。"""

import os
import shutil
import subprocess
from pathlib import Path

import httpx
import pytest

from tests.e2e.test_subject_list_http import unused_port, wait_for_server

BACKEND = Path(__file__).resolve().parents[2]
ORIGIN = "http://127.0.0.1:5173"
PASSWORD = "app-only-password-123"


@pytest.fixture
def auth_services(tmp_path, request):
    go = shutil.which("go")
    if go is None:
        pytest.skip("Goが必要です。PATHに追加して検証してください。")
    binary = tmp_path / "api"
    subprocess.run(
        [go, "build", "-o", str(binary), "./apps/api"], cwd=BACKEND, check=True
    )
    python_port, go_port = [unused_port() for _ in range(2)]
    commands = [
        [
            str(BACKEND / ".venv/bin/python"),
            "-m",
            "uvicorn",
            "apps.bridge.main:app",
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
            *getattr(request, "param", []),
        ],
    ]
    processes = []
    logs = []
    environment = {
        **os.environ,
        "DATABASE_URL": f"sqlite:///{tmp_path / 'auth.db'}",
        "PUBLIC_ORIGIN": ORIGIN,
    }
    try:
        for index, command in enumerate(commands):
            path = tmp_path / f"server-{index}.log"
            log = path.open("w")
            logs.append(log)
            process = subprocess.Popen(
                command,
                cwd=BACKEND,
                env=environment,
                stdout=log,
                stderr=subprocess.STDOUT,
            )
            processes.append(process)
            url = (
                f"http://127.0.0.1:{python_port}/bridge/auth"
                if index == 0
                else f"http://127.0.0.1:{go_port}/api/health"
            )

            def probe(url=url, index=index):
                try:
                    response = (
                        httpx.post(url, json={"operation": "config"}, timeout=1)
                        if index == 0
                        else httpx.get(url, timeout=1)
                    )
                    return response.status_code == 200
                except httpx.ConnectError:
                    return False

            wait_for_server(process, path, probe)
        with httpx.Client(
            base_url=f"http://127.0.0.1:{go_port}", headers={"Origin": ORIGIN}
        ) as client:
            yield client
    finally:
        for process in reversed(processes):
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        for log in logs:
            log.close()


def test_real_registration_recovery_and_session(auth_services):
    client = auth_services
    credentials = {"login_name": "Student_01", "password": PASSWORD}
    assert client.get("/api/auth/config").json()["policy"]["password_min_length"] == 12
    assert client.get("/api/auth/session").status_code == 401
    assert (
        client.post(
            "/api/auth/register",
            json=credentials,
            headers={"Origin": "https://evil.example"},
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/auth/register",
            content='{"login_name":"abc","login_name":"def","password":"password"}',
            headers={"Content-Type": "application/json"},
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/auth/register", json={"email": "student@edu.teu.ac.jp"}
        ).status_code
        == 422
    )
    assert client.post("/api/auth/verify", json={}).status_code == 404
    response = client.post("/api/auth/register", json=credentials)
    assert response.status_code == 201
    recovery = response.json()["recovery_code"]
    assert response.headers["cache-control"] == "no-store"
    assert not client.cookies
    assert (
        client.post(
            "/api/auth/register", json={**credentials, "login_name": "student_01"}
        ).status_code
        == 409
    )
    response = client.post("/api/auth/login", json=credentials)
    assert response.status_code == 200
    assert response.json()["student"]["login_name"] == "student_01"
    assert "session_token" not in response.text and "recovery_code" not in response.text
    cookie = response.headers["set-cookie"]
    assert "HttpOnly" in cookie and "SameSite=Lax" in cookie and "Path=/" in cookie
    session = client.get("/api/auth/session")
    assert session.json() == response.json()
    csrf = session.json()["csrf_token"]
    assert client.post("/api/auth/logout", json={}).status_code == 403
    assert (
        client.post(
            "/api/auth/logout", json={}, headers={"X-CSRF-Token": "x" * 64}
        ).status_code
        == 403
    )
    old_cookie = client.cookies.get("grad_checker_session")
    assert (
        client.post(
            "/api/auth/logout", json={}, headers={"X-CSRF-Token": csrf}
        ).status_code
        == 200
    )
    assert (
        client.get(
            "/api/auth/session",
            headers={"Cookie": f"grad_checker_session={old_cookie}"},
        ).status_code
        == 401
    )
    assert client.post("/api/auth/login", json=credentials).status_code == 200
    old_cookie = client.cookies.get("grad_checker_session")
    recovered = client.post(
        "/api/auth/recover",
        json={
            "login_name": "STUDENT_01",
            "recovery_code": recovery,
            "password": "new-application-password",
        },
    )
    assert recovered.status_code == 200
    assert recovered.json()["recovery_code"] != recovery
    assert (
        client.get(
            "/api/auth/session",
            headers={"Cookie": f"grad_checker_session={old_cookie}"},
        ).status_code
        == 401
    )
    assert client.post("/api/auth/login", json=credentials).status_code == 401
    assert (
        client.post(
            "/api/auth/login",
            json={**credentials, "password": "new-application-password"},
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/auth/recover",
            json={
                "login_name": "student_01",
                "recovery_code": recovery,
                "password": PASSWORD,
            },
        ).status_code
        == 400
    )

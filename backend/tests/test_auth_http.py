"""実Go → Python → SQLite → SMTP配送の登録・ログインを検証する。"""

import os
import re
import shutil
import subprocess
from email import policy
from email.parser import BytesParser
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest
from aiosmtpd.controller import Controller
from test_subject_list_http import unused_port, wait_for_server

BACKEND = Path(__file__).resolve().parents[1]
ORIGIN = "http://127.0.0.1:5173"
PASSWORD = "app-only-password-123"


class Receiver:
    def __init__(self):
        self.messages: list[bytes] = []

    async def handle_DATA(self, _server, _session, envelope):  # noqa: N802
        self.messages.append(envelope.original_content)
        return "250 OK"


@pytest.fixture
def auth_services(tmp_path):
    go = shutil.which("go")
    if go is None:
        pytest.skip("Goが必要です。PATHに追加して検証してください。")
    binary = tmp_path / "api"
    subprocess.run([go, "build", "-o", str(binary), "./api"], cwd=BACKEND, check=True)
    python_port, go_port, smtp_port = [unused_port() for _ in range(3)]
    receiver = Receiver()
    smtp = Controller(receiver, hostname="127.0.0.1", port=smtp_port)
    smtp.start()
    commands = [
        [
            str(BACKEND / ".venv/bin/python"),
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
    processes = []
    logs = []
    environment = {
        **os.environ,
        "DATABASE_URL": f"sqlite:///{tmp_path / 'auth.db'}",
        "SMTP_HOST": "127.0.0.1",
        "SMTP_PORT": str(smtp_port),
        "SMTP_STARTTLS": "false",
        "SMTP_SENDER": "app@example.test",
        "SMTP_USERNAME": "",
        "SMTP_PASSWORD": "",
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
                f"http://127.0.0.1:{python_port}/internal/auth"
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
            yield client, receiver, smtp
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
        if not smtp.loop.is_closed():
            smtp.stop()


def test_real_registration_mail_verification_and_session(auth_services):
    client, receiver, smtp = auth_services
    config = client.get("/api/auth/config")
    assert config.status_code == 200
    assert config.json()["policy"]["password_min_length"] == 12
    assert client.get("/api/auth/session").status_code == 401
    assert (
        client.post(
            "/api/auth/register",
            json={"email": "student@edu.teu.ac.jp"},
            headers={"Origin": "https://evil.example"},
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/auth/register", json={"email": "student@edu.teu.ac.jp.evil.example"}
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/auth/register",
            content='{"email":"x@edu.teu.ac.jp","email":"y@edu.teu.ac.jp"}',
            headers={"Content-Type": "application/json"},
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/auth/register",
            json={"email": "student@edu.teu.ac.jp", "password": PASSWORD},
        ).status_code
        == 422
    )
    response = client.post(
        "/api/auth/register", json={"email": "student@edu.teu.ac.jp"}
    )
    assert response.status_code == 202
    assert "token" not in response.text
    assert len(receiver.messages) == 1
    message = BytesParser(policy=policy.default).parsebytes(receiver.messages[0])
    assert message["To"] == "student@edu.teu.ac.jp"
    part = message.get_body(preferencelist=("plain",))
    assert part is not None
    body = part.get_content()
    match = re.search(r"http://[^\s]+", body)
    assert match is not None
    link = match.group()
    token = parse_qs(urlsplit(link).fragment)["verification_token"][0]
    assert not urlsplit(link).query
    assert (
        client.post(
            "/api/auth/login",
            json={"email": "student@edu.teu.ac.jp", "password": PASSWORD},
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/api/auth/verify", json={"token": token, "password": PASSWORD}
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/auth/verify", json={"token": token, "password": PASSWORD}
        ).status_code
        == 400
    )
    response = client.post(
        "/api/auth/login", json={"email": "student@edu.teu.ac.jp", "password": PASSWORD}
    )
    assert response.status_code == 200
    assert "session_token" not in response.text
    cookie = response.headers["set-cookie"]
    assert "HttpOnly" in cookie and "SameSite=Lax" in cookie and "Path=/" in cookie
    assert response.headers["cache-control"] == "no-store"
    session = client.get("/api/auth/session")
    assert session.status_code == 200
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
    smtp.stop()
    assert (
        client.post(
            "/api/auth/register", json={"email": "another@edu.teu.ac.jp"}
        ).status_code
        == 503
    )

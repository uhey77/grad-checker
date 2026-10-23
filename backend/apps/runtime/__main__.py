"""Pythonの準備完了後にGoを起動し、終了時はGo→Pythonの順に停止する。"""

import os
import signal
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import urlopen

from sqlalchemy.engine import make_url

from apps.settings import Settings


def main() -> int:
    children = []
    stopping = False

    def stop(_signum, _frame):
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    try:
        settings = Settings()
        url = make_url(settings.database_url)
        if url.get_backend_name() != "postgresql" or url.query.get("sslmode") not in {
            "require",
            "verify-ca",
            "verify-full",
        }:
            raise ValueError("Runtime requires PostgreSQL with TLS")
        if not settings.public_origin.startswith("https://"):
            raise ValueError("Runtime requires an HTTPS public origin")
        if settings.direct_database_url:
            raise ValueError(
                "Direct database credentials must not reach the web runtime"
            )
        port = int(os.environ.get("PORT", "8080"))
        if not 1 <= port <= 65535:
            raise ValueError("Invalid PORT")
        python = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "apps.bridge.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                "8001",
                "--no-access-log",
                "--timeout-graceful-shutdown",
                "2",
            ]
        )
        children.append(python)
        deadline = time.monotonic() + 180
        while not stopping:
            if python.poll() is not None or time.monotonic() > deadline:
                raise RuntimeError("Python startup failed")
            try:
                with urlopen(
                    "http://127.0.0.1:8001/bridge/health", timeout=1
                ) as response:
                    if response.status == 200:
                        break
            except OSError, URLError:
                time.sleep(0.1)
        if stopping:
            return 0
        go = subprocess.Popen(
            [
                "/app/bin/api",
                "-listen",
                f"0.0.0.0:{port}",
                "-python-url",
                "http://127.0.0.1:8001",
                "-public-origin",
                settings.public_origin,
            ]
        )
        children.append(go)
        while not stopping:
            if any(child.poll() is not None for child in children):
                raise RuntimeError("A service process exited")
            time.sleep(0.1)
        return 0
    except Exception as error:
        print(f"Runtime failed: {type(error).__name__}", file=sys.stderr)
        return 1
    finally:
        # Goは最大5秒で要求をdrain。その間Pythonを生かし、計8秒以内に終了する。
        for child in reversed(children):
            if child.poll() is None:
                child.terminate()
                try:
                    child.wait(
                        timeout=5.5
                        if child is children[-1] and len(children) > 1
                        else 2.5
                    )
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait()


if __name__ == "__main__":
    raise SystemExit(main())

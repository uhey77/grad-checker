"""固定digestで非公開サービスを初回作成する。既存サービスは変更しない。"""

import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

PROJECT = "grad-checker-512505"
REGION = "asia-northeast1"
PARENT = f"projects/{PROJECT}/locations/{REGION}"
NAME = f"{PARENT}/services/grad-checker-api"
API = "https://run.googleapis.com/v2/"
IMAGE = f"{REGION}-docker.pkg.dev/{PROJECT}/grad-checker/api"
RUNTIME = f"grad-checker-runtime@{PROJECT}.iam.gserviceaccount.com"


def command(*args):
    result = subprocess.run(args, capture_output=True, text=True, timeout=900)
    if result.returncode:
        raise RuntimeError(f"Command failed: {args[0]} {args[1]}")
    return result.stdout.strip()


def request(path, token, method="GET", body=None):
    if not any(
        path.startswith(parent + "/")
        for parent in (PARENT, f"projects/602914367926/locations/{REGION}")
    ):
        raise RuntimeError("Unexpected API target")
    req = urllib.request.Request(
        API + path,
        data=json.dumps(body).encode() if body is not None else None,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        # Never include response bodies, access tokens or database details.
        raise RuntimeError(f"Cloud API {method} failed: HTTP {error.code}") from None


def manifest(digest):
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
        raise ValueError("Invalid image digest")
    return {
        "ingress": "INGRESS_TRAFFIC_ALL",
        "invokerIamDisabled": False,
        "scaling": {"maxInstanceCount": 1},
        "template": {
            "serviceAccount": RUNTIME,
            "maxInstanceRequestConcurrency": 4,
            "timeout": "30s",
            "scaling": {"minInstanceCount": 0, "maxInstanceCount": 1},
            "containers": [
                {
                    "image": f"{IMAGE}@{digest}",
                    "ports": [{"containerPort": 8080}],
                    "resources": {
                        "limits": {"cpu": "1", "memory": "512Mi"},
                        "cpuIdle": True,
                        "startupCpuBoost": False,
                    },
                    "env": [
                        {
                            "name": "PUBLIC_ORIGIN",
                            "value": "https://grad-checker-chi.vercel.app",
                        },
                        {
                            "name": "DATABASE_URL",
                            "valueSource": {
                                "secretKeyRef": {
                                    "secret": "grad-checker-database-url",
                                    "version": "1",
                                }
                            },
                        },
                    ],
                    "startupProbe": {
                        "httpGet": {"path": "/api/ready", "port": 8080},
                        "timeoutSeconds": 4,
                        "periodSeconds": 5,
                        "failureThreshold": 36,
                    },
                    "livenessProbe": {
                        "httpGet": {"path": "/api/health", "port": 8080},
                        "timeoutSeconds": 1,
                        "periodSeconds": 30,
                        "failureThreshold": 3,
                    },
                }
            ],
        },
    }


def create():
    sha = os.environ["GITHUB_SHA"]
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise RuntimeError("Invalid source SHA")
    token = command("gcloud", "auth", "print-access-token")
    services = request(f"{PARENT}/services", token)
    if any(s.get("name") == NAME for s in services.get("services", [])):
        raise RuntimeError("Service already exists; initial creation stopped")
    # A paginated list must not be mistaken for complete inventory.
    if services.get("nextPageToken"):
        raise RuntimeError("Unexpected paginated service inventory")
    repository = json.loads(
        command(
            "gcloud",
            "artifacts",
            "repositories",
            "describe",
            "grad-checker",
            f"--project={PROJECT}",
            f"--location={REGION}",
            "--format=json",
        )
    )
    if (
        repository["name"] != f"{PARENT}/repositories/grad-checker"
        or repository["format"] != "DOCKER"
    ):
        raise RuntimeError("Unexpected registry")
    tag = f"{IMAGE}:{sha}"
    # No tag overwrite. list output contains metadata only.
    tags = json.loads(
        command(
            "gcloud",
            "artifacts",
            "docker",
            "images",
            "list",
            IMAGE.rsplit("/", 1)[0],
            f"--project={PROJECT}",
            "--include-tags",
            "--format=json",
        )
    )
    if any(
        tag.rsplit(":", 1)[-1] == sha for image in tags for tag in image.get("tags", [])
    ):
        raise RuntimeError("Commit tag already exists; stopped")
    command("gcloud", "auth", "configure-docker", f"{REGION}-docker.pkg.dev", "--quiet")
    command("docker", "push", tag)
    image = json.loads(
        command(
            "gcloud",
            "artifacts",
            "docker",
            "images",
            "describe",
            tag,
            f"--project={PROJECT}",
            "--format=json",
        )
    )
    digest = image["image_summary"]["digest"]
    body = manifest(digest)
    Path(os.environ["RUNNER_TEMP"], "initial-cloud-run.json").write_text(
        json.dumps(body, indent=2)
    )
    operation = request(
        f"{PARENT}/services?serviceId=grad-checker-api", token, "POST", body
    )
    deadline = time.monotonic() + 600
    while not operation.get("done") and time.monotonic() < deadline:
        time.sleep(5)
        operation = request(operation["name"], token)
    if not operation.get("done") or "error" in operation:
        raise RuntimeError(
            "Initial service creation did not succeed; inspect restricted cloud logs"
        )
    service = request(NAME, token)
    if service.get("terminalCondition", {}).get("state") != "CONDITION_SUCCEEDED":
        raise RuntimeError("Cloud Run revision not ready")
    if service.get("latestReadyRevision") != service.get("latestCreatedRevision"):
        raise RuntimeError("Latest created revision is not ready")
    actual = service["template"]
    container = actual["containers"][0]
    if (
        actual["serviceAccount"] != RUNTIME
        or container["image"] != f"{IMAGE}@{digest}"
        or actual["maxInstanceRequestConcurrency"] != 4
        or actual["scaling"].get("maxInstanceCount") != 1
        or actual["scaling"].get("minInstanceCount", 0) != 0
        or container["resources"]["limits"] != {"cpu": "1", "memory": "512Mi"}
        or container["env"] != body["template"]["containers"][0]["env"]
        or not container["resources"].get("cpuIdle", False)
        or container["resources"].get("startupCpuBoost", False)
        or service.get("invokerIamDisabled", False)
    ):
        raise RuntimeError(
            "Actual service configuration differs from approved manifest"
        )
    policy = request(NAME + ":getIamPolicy", token)
    if any(
        set(b.get("members", [])) & {"allUsers", "allAuthenticatedUsers"}
        for b in policy.get("bindings", [])
    ):
        raise RuntimeError("Unexpected public IAM on initial private service")
    uri = service["uri"]
    if not re.fullmatch(r"https://[a-z0-9.-]+\.run\.app", uri):
        raise RuntimeError("Unexpected service URL")
    result = {
        "source_sha": sha,
        "image": f"{IMAGE}@{digest}",
        "service": NAME,
        "revision": service["latestReadyRevision"],
        "uri": uri,
        "private": True,
    }
    print(json.dumps(result))
    Path(os.environ["RUNNER_TEMP"], "initial-result.json").write_text(
        json.dumps(result, indent=2)
    )
    with open(os.environ["GITHUB_OUTPUT"], "a") as output:
        output.write(f"uri={uri}\n")


def probe():
    uri = os.environ["SERVICE_URI"]
    if not re.fullmatch(r"https://[a-z0-9.-]+\.run\.app", uri):
        raise RuntimeError("Unexpected service URL")
    try:
        urllib.request.urlopen(uri + "/api/ready", timeout=20)
    except urllib.error.HTTPError as error:
        if error.code not in (401, 403):
            raise RuntimeError("Unexpected anonymous readiness response") from None
    else:
        raise RuntimeError("Private readiness accessible without authentication")
    req = urllib.request.Request(
        uri + "/api/ready",
        headers={"Authorization": "Bearer " + os.environ["SERVICE_ID_TOKEN"]},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.load(response)
            if response.status != 200 or data != {"status": "ok"}:
                raise RuntimeError("Readiness response differs from expected result")
    except urllib.error.HTTPError as error:
        raise RuntimeError(
            f"Authenticated readiness failed: HTTP {error.code}"
        ) from None
    print(json.dumps({"authenticated_readiness": "PASS", "anonymous_access": "DENIED"}))


if __name__ == "__main__":
    try:
        {"create": create, "probe": probe}[sys.argv[1]]()
    except Exception as error:
        # Only controlled messages; third-party exceptions can contain credentials.
        print(f"Initial deployment stopped ({type(error).__name__})", file=sys.stderr)
        if isinstance(error, RuntimeError):
            print(str(error), file=sys.stderr)
        sys.exit(1)

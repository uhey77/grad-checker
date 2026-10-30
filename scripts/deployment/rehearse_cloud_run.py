"""承認済み正常digestで一時revisionを作り、既存正常revisionへ復旧する。"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import time
import urllib.request
from pathlib import Path

PROJECT = "grad-checker-512505"
REGION = "asia-northeast1"
SERVICE = "grad-checker-api"
BASELINE = "grad-checker-api-00001-g9l"
DIGEST = "sha256:d3a2081572a5595f0ed7ab8f67f97650f445b366579c63870e6d0f8bd0331571"
IMAGE = f"{REGION}-docker.pkg.dev/{PROJECT}/grad-checker/api@{DIGEST}"
ORIGIN = "https://grad-checker-api-hmhzqixo4q-an.a.run.app"


STAGE = "initialization"


class RehearsalError(RuntimeError):
    def __init__(self, code, *, exit_code=None):
        super().__init__(code)
        self.code = code
        self.exit_code = exit_code


def failure_report(error):
    report = {
        "rehearsal": "FAIL",
        "stage": STAGE,
        "error_type": type(error).__name__,
    }
    if isinstance(error, RehearsalError):
        report["error_code"] = error.code
        if error.exit_code is not None:
            report["exit_code"] = error.exit_code
    return report


def command(*args):
    try:
        result = subprocess.run(
            args, capture_output=True, text=True, timeout=600, check=False
        )
    except subprocess.TimeoutExpired:
        raise RehearsalError("command_timeout") from None
    if result.returncode:
        raise RehearsalError("command_failed", exit_code=result.returncode)
    return result.stdout.strip()


def gcloud(*args):
    return json.loads(
        command(
            "gcloud",
            "run",
            *args,
            f"--project={PROJECT}",
            f"--region={REGION}",
            "--format=json",
            "--quiet",
        )
        or "{}"
    )


def fingerprint(service):
    template = service["spec"]["template"]
    annotations = template["metadata"].get("annotations", {})
    config = {
        "spec": template["spec"],
        "annotations": {
            k: v
            for k, v in annotations.items()
            if k.startswith("autoscaling.")
            or k
            in (
                "run.googleapis.com/cpu-throttling",
                "run.googleapis.com/startup-cpu-boost",
            )
        },
    }
    return hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()


def validate_revision(revision, name):
    if revision.get("metadata", {}).get("name") != name:
        raise RehearsalError("revision_name_mismatch")
    status = revision.get("status", {})
    if not any(
        c.get("type") == "Ready" and c.get("status") == "True"
        for c in status.get("conditions", [])
    ):
        raise RehearsalError("revision_not_ready")
    if status.get("imageDigest") != IMAGE:
        raise RehearsalError("revision_image_mismatch")


def traffic_is(service, revision):
    traffic = service["status"].get("traffic", [])
    return (
        len(traffic) == 1
        and traffic[0].get("revisionName") == revision
        and traffic[0].get("percent") == 100
        and not traffic[0].get("tag")
    )


def validate_baseline(service):
    spec = service["spec"]["template"]["spec"]
    container = spec["containers"][0]
    if (
        service["metadata"]["name"] != SERVICE
        or service["status"].get("url") != ORIGIN
        or service["status"].get("latestReadyRevisionName") != BASELINE
        or not traffic_is(service, BASELINE)
        or container["image"] != IMAGE
        or spec.get("containerConcurrency") != 4
        or container.get("resources", {}).get("limits", {}).get("cpu")
        not in ("1", "1000m")
        or container.get("resources", {}).get("limits", {}).get("memory") != "512Mi"
        or spec.get("serviceAccountName")
        != f"grad-checker-runtime@{PROJECT}.iam.gserviceaccount.com"
    ):
        raise ValueError("Production baseline differs; re-review recovery target")


def readiness():
    for _ in range(12):
        try:
            with urllib.request.urlopen(ORIGIN + "/api/ready", timeout=30) as response:
                if response.status == 200 and json.load(response).get("status") == "ok":
                    return
        except (OSError, ValueError):
            pass
        time.sleep(5)
    raise RehearsalError("readiness_failed")


def save(path, state):
    path.write_text(json.dumps(state))
    path.chmod(0o600)


def update(path, run_id):
    global STAGE
    STAGE = "baseline_validation"
    if not re.fullmatch(r"[0-9]{1,20}", run_id):
        raise ValueError("Invalid rehearsal run id")
    service = gcloud("services", "describe", SERVICE)
    validate_baseline(service)
    STAGE = "baseline_readiness"
    readiness()
    suffix = f"rehearsal-{run_id}"
    revision = f"{SERVICE}-{suffix}"
    state = {
        "baseline": BASELINE,
        "revision": revision,
        "fingerprint": fingerprint(service),
        "mutation_started": True,
    }
    save(path, state)
    # 同一digest・既存サービス設定を維持。IAM/Secret/DDL/Seedは変更しない。
    STAGE = "revision_creation"
    gcloud(
        "deploy",
        SERVICE,
        f"--image={IMAGE}",
        f"--revision-suffix={suffix}",
        "--no-traffic",
    )
    STAGE = "revision_validation"
    validate_revision(gcloud("revisions", "describe", revision), revision)
    STAGE = "configuration_validation"
    service = gcloud("services", "describe", SERVICE)
    if fingerprint(service) != state["fingerprint"]:
        raise RehearsalError("configuration_mismatch")
    if not traffic_is(service, BASELINE):
        raise RehearsalError("unexpected_traffic_before_switch")
    STAGE = "traffic_switch"
    gcloud("services", "update-traffic", SERVICE, f"--to-revisions={revision}=100")
    if not traffic_is(gcloud("services", "describe", SERVICE), revision):
        raise RehearsalError("traffic_switch_not_verified")
    STAGE = "updated_readiness"
    readiness()
    state["update_verified"] = True
    save(path, state)
    print(
        json.dumps({"cloud_run_update": "PASS", "revision": revision, "digest": DIGEST})
    )


def restore(path):
    global STAGE
    STAGE = "restore"
    if not path.exists():
        print(json.dumps({"cloud_run_restore": "not_needed"}))
        return
    state = json.loads(path.read_text())
    if state.get("baseline") != BASELINE or not re.fullmatch(
        rf"{SERVICE}-rehearsal-[0-9]{{1,20}}", state.get("revision", "")
    ):
        raise ValueError("Invalid recovery state")
    service = gcloud("services", "describe", SERVICE)
    if any(
        t.get("revisionName") not in (BASELINE, state["revision"])
        for t in service["status"].get("traffic", [])
    ):
        raise RuntimeError(
            "Unexpected concurrent traffic change; manual recovery required"
        )
    gcloud("services", "update-traffic", SERVICE, f"--to-revisions={BASELINE}=100")
    service = gcloud("services", "describe", SERVICE)
    if not traffic_is(service, BASELINE):
        raise RuntimeError("Baseline traffic restoration not verified")
    readiness()
    state["restore_verified"] = True
    save(path, state)
    if fingerprint(service) != state["fingerprint"]:
        raise RuntimeError(
            "Traffic restored; latest template differs and requires review"
        )
    print(
        json.dumps(
            {
                "cloud_run_restore": "PASS",
                "revision": BASELINE,
                "configuration_unchanged": True,
            }
        )
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("operation", choices=("update", "restore"))
    args = parser.parse_args()
    if (
        os.environ.get("GITHUB_REPOSITORY") != "uhey77/grad-checker"
        or os.environ.get("GITHUB_REF") != "refs/heads/main"
        or os.environ.get("REHEARSAL_CONFIRM") != "REHEARSE_AND_RESTORE"
    ):
        raise ValueError("Reviewed main and explicit rehearsal confirmation required")
    path = Path(os.environ["RUNNER_TEMP"]) / "cloud-run-rehearsal.json"
    if args.operation == "update":
        update(path, os.environ["GITHUB_RUN_ID"])
    else:
        restore(path)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:  # noqa: BLE001 -- Secretを含み得るCLI応答を出さない
        print(json.dumps(failure_report(error)))
        raise SystemExit(1) from None

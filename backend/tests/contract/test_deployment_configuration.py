"""本番への権限昇格前のゲートと初回Cloud Run設定の契約。"""

import os
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]


def workflow(name):
    return yaml.safe_load((ROOT / ".github/workflows" / name).read_text())


def test_cloud_run_manifest_limits_resources_and_injects_only_runtime_secret():
    service = yaml.safe_load((ROOT / "infra/cloud-run.yaml").read_text())
    assert service["metadata"]["name"] == "grad-checker-api"
    template = service["spec"]["template"]
    annotations = template["metadata"]["annotations"]
    assert annotations["autoscaling.knative.dev/minScale"] == "0"
    assert annotations["autoscaling.knative.dev/maxScale"] == "1"
    assert annotations["run.googleapis.com/cpu-throttling"] == "true"
    assert annotations["run.googleapis.com/startup-cpu-boost"] == "false"
    spec = template["spec"]
    assert spec["serviceAccountName"] == (
        "grad-checker-runtime@grad-checker-512505.iam.gserviceaccount.com"
    )
    assert spec["containerConcurrency"] == 4
    assert spec["timeoutSeconds"] == 30
    assert len(spec["containers"]) == 1
    container = spec["containers"][0]
    assert container["resources"]["limits"] == {"cpu": "1", "memory": "512Mi"}
    assert container["ports"] == [{"containerPort": 8080}]
    assert container["env"] == [
        {"name": "PUBLIC_ORIGIN", "value": "https://grad-checker-chi.vercel.app"},
        {
            "name": "DATABASE_URL",
            "valueFrom": {
                "secretKeyRef": {"name": "grad-checker-database-url", "key": "1"}
            },
        },
    ]
    assert container["startupProbe"]["httpGet"] == {
        "path": "/api/ready",
        "port": 8080,
    }
    assert container["livenessProbe"]["httpGet"] == {
        "path": "/api/health",
        "port": 8080,
    }


def test_wif_and_deployments_require_main_flag_and_production_environment():
    jobs = workflow("deploy.yml")["jobs"]
    backend = jobs["backend"]
    assert backend["if"] == (
        "github.ref == 'refs/heads/main' && vars.PRODUCTION_DEPLOY_ENABLED == 'true'"
    )
    assert backend["environment"] == "production"
    assert backend["permissions"]["id-token"] == "write"
    steps = backend["steps"]
    policy = next(
        i
        for i, step in enumerate(steps)
        if step.get("run") == "node scripts/deployment/check-release-policy.mjs"
    )
    auth = next(
        i
        for i, step in enumerate(steps)
        if step.get("uses", "").startswith("google-github-actions/auth@")
    )
    assert policy < auth
    frontend = jobs["frontend"]
    assert frontend["needs"] == "backend"
    assert frontend["environment"] == "production"
    assert "id-token" not in frontend["permissions"]
    assert not any(
        step.get("uses", "").startswith("google-github-actions/")
        for step in frontend["steps"]
    )


def test_database_secrets_are_only_available_after_main_approval_policy():
    job = workflow("database-connectivity.yml")["jobs"]["check"]
    assert job["if"] == "github.ref == 'refs/heads/main'"
    assert job["environment"] == "production"
    policy = next(
        i
        for i, step in enumerate(job["steps"])
        if step.get("run") == "node scripts/deployment/check-release-policy.mjs"
    )
    secret_steps = [
        i
        for i, step in enumerate(job["steps"])
        if "secrets." in str(step.get("env", {}))
    ]
    assert len(secret_steps) == 2
    assert all(i > policy for i in secret_steps)
    assert all("--connection-only" in job["steps"][i]["run"] for i in secret_steps)


def test_vercel_token_audit_is_manual_exact_commit_and_has_no_cloud_auth():
    job = workflow("check.yml")["jobs"]["vercel-audit"]
    assert "github.event_name == 'workflow_dispatch'" in job["if"]
    assert "inputs.audit_vercel" in job["if"]
    assert "github.sha == inputs.expected_sha" in job["if"]
    assert "id-token" not in job["permissions"]
    assert "environment" not in job  # 未設定のproduction環境を暗黙作成しない。
    assert [step.get("run") for step in job["steps"] if "run" in step] == [
        "node scripts/deployment/audit-vercel-project.mjs"
    ]


def test_cloud_run_render_accepts_only_fixed_registry_and_commit_tag():
    for image, expected in [
        (
            "asia-northeast1-docker.pkg.dev/grad-checker-512505/grad-checker/api:"
            + "a" * 40,
            0,
        ),
        (
            "asia-northeast1-docker.pkg.dev/grad-checker-512505/grad-checker/api:latest",
            1,
        ),
        ("other.example/api:" + "a" * 40, 1),
    ]:
        result = subprocess.run(
            [sys.executable, "scripts/deployment/render_cloud_run.py"],
            cwd=ROOT,
            env={**os.environ, "DEPLOY_IMAGE": image},
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == expected
        if expected == 0:
            assert (
                yaml.safe_load(result.stdout)["spec"]["template"]["spec"]["containers"][
                    0
                ]["image"]
                == image
            )


def test_preflight_is_manual_exact_main_and_separates_secrets_from_wif():
    config = workflow("production-preflight.yml")
    # PyYAMLのYAML 1.1ではonがTrueとして読まれる。
    triggers = config.get("on", config.get(True))
    assert set(triggers) == {"workflow_dispatch"}
    jobs = config["jobs"]
    for job in jobs.values():
        assert "github.ref == 'refs/heads/main'" in job["if"]
        assert "github.sha == inputs.expected_sha" in job["if"]
        assert job["environment"] == "production"
        policy = next(
            i
            for i, step in enumerate(job["steps"])
            if step.get("run") == "node scripts/deployment/check-release-policy.mjs"
        )
        sensitive = [
            i
            for i, step in enumerate(job["steps"])
            if "secrets." in str(step.get("env", {}))
            or step.get("uses", "").startswith("google-github-actions/auth@")
        ]
        assert sensitive and all(i > policy for i in sensitive)
    assert "id-token" not in jobs["database"]["permissions"]
    assert jobs["wif"]["needs"] == "database"
    assert jobs["wif"]["permissions"]["id-token"] == "write"
    assert "secrets." not in str(jobs["wif"])
    commands = "\n".join(
        step.get("run", "") for job in jobs.values() for step in job["steps"]
    )
    for prohibited in (
        "--apply",
        "docker push",
        "services replace",
        "add-iam-policy-binding",
        "vercel promote",
    ):
        assert prohibited not in commands

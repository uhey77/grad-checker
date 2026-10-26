"""認証済みCloud Shell用。固定対象のmetadata/IAMだけを取得し、値を絞って報告する。"""

import json
import re
import subprocess
import sys

PROJECT = "grad-checker-512505"
REGION = "asia-northeast1"
DEPLOYER = f"grad-checker-deployer@{PROJECT}.iam.gserviceaccount.com"
RUNTIME = f"grad-checker-runtime@{PROJECT}.iam.gserviceaccount.com"
MEMBER = f"serviceAccount:{DEPLOYER}"


def read(*args):
    result = subprocess.run(
        ["gcloud", *args, f"--project={PROJECT}", "--format=json", "--quiet"],
        capture_output=True,
        text=True,
        check=True,
        timeout=45,
    )
    return json.loads(result.stdout)


def granted(policy, role, member):
    return any(
        b.get("role") == role
        and member in b.get("members", [])
        and not b.get("condition")
        for b in policy.get("bindings", [])
    )


def main():
    try:
        repository = read(
            "artifacts",
            "repositories",
            "describe",
            "grad-checker",
            f"--location={REGION}",
        )
        assert repository["name"] == (
            f"projects/{PROJECT}/locations/{REGION}/repositories/grad-checker"
        )
        assert repository["format"] == "DOCKER"
        for account in (DEPLOYER, RUNTIME):
            assert not read("iam", "service-accounts", "describe", account).get(
                "disabled"
            )
        provider = read(
            "iam",
            "workload-identity-pools",
            "providers",
            "describe",
            "github-provider",
            "--workload-identity-pool=github-pool",
            "--location=global",
        )
        assert provider["state"] == "ACTIVE"
        assert not provider.get("disabled")
        assert (
            provider["oidc"]["issuerUri"]
            == "https://token.actions.githubusercontent.com"
        )
        condition = re.sub(r"[\s()]", "", provider["attributeCondition"]).replace(
            '"', "'"
        )
        assert sorted(condition.split("&&")) == sorted(
            [
                "assertion.repository=='uhey77/grad-checker'",
                "assertion.ref=='refs/heads/main'",
            ]
        )
        assert (
            provider["attributeMapping"]["attribute.repository"]
            == "assertion.repository"
        )
        project_policy = read("projects", "get-iam-policy", PROJECT)
        assert granted(project_policy, "roles/run.developer", MEMBER)
        registry_policy = read(
            "artifacts",
            "repositories",
            "get-iam-policy",
            "grad-checker",
            f"--location={REGION}",
        )
        assert granted(registry_policy, "roles/artifactregistry.writer", MEMBER)
        assert granted(
            read("iam", "service-accounts", "get-iam-policy", RUNTIME),
            "roles/iam.serviceAccountUser",
            MEMBER,
        )
        principal = (
            "principalSet://iam.googleapis.com/projects/602914367926/locations/global/"
            "workloadIdentityPools/github-pool/attribute.repository/uhey77/grad-checker"
        )
        assert granted(
            read("iam", "service-accounts", "get-iam-policy", DEPLOYER),
            "roles/iam.workloadIdentityUser",
            principal,
        )
        for secret in ("grad-checker-database-url", "grad-checker-direct-database-url"):
            assert (
                read("secrets", "versions", "describe", "1", f"--secret={secret}")[
                    "state"
                ]
                == "ENABLED"
            )
        runtime_secret_policy = read(
            "secrets", "get-iam-policy", "grad-checker-database-url"
        )
        assert granted(
            runtime_secret_policy,
            "roles/secretmanager.secretAccessor",
            f"serviceAccount:{RUNTIME}",
        )
        services = read(
            "run",
            "services",
            "list",
            f"--region={REGION}",
            "--filter=metadata.name=grad-checker-api",
        )
        assert not services, (
            "Existing service requires revision/IAM review before initial creation"
        )
    except (
        OSError,
        subprocess.SubprocessError,
        ValueError,
        KeyError,
        TypeError,
        AssertionError,
    ):
        print(
            "GCP initial audit failed; metadata/IAM must be reviewed; details suppressed"
        )
        return 1
    print(
        json.dumps(
            {
                "gcp_initial_metadata_iam": "passed",
                "wif_repository_and_main_only": True,
                "initial_cloud_run_absent": True,
                "secret_values_read": False,
                "inherited_direct_secret_permissions": "not_evaluated",
                "organization_public_access_policy": "not_evaluated",
            }
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

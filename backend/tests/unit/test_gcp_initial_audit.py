import importlib.util
from pathlib import Path

import pytest


@pytest.fixture
def audit():
    path = (
        Path(__file__).resolve().parents[3] / "scripts/deployment/audit-gcp-initial.py"
    )
    spec = importlib.util.spec_from_file_location("gcp_initial_audit", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def responses(audit, *, ref="refs/heads/main", services=None):
    def read(*args):
        if args[:3] == ("artifacts", "repositories", "describe"):
            return {
                "name": "projects/grad-checker-512505/locations/asia-northeast1/"
                "repositories/grad-checker",
                "format": "DOCKER",
            }
        if args[:3] == ("iam", "service-accounts", "describe"):
            return {"disabled": False}
        if args[:3] == ("iam", "workload-identity-pools", "providers"):
            return {
                "state": "ACTIVE",
                "oidc": {"issuerUri": "https://token.actions.githubusercontent.com"},
                "attributeCondition": "assertion.repository=='uhey77/grad-checker'"
                f" && assertion.ref=='{ref}'",
                "attributeMapping": {"attribute.repository": "assertion.repository"},
            }
        if args[:3] == ("secrets", "versions", "describe"):
            return {"state": "ENABLED"}
        if args[:3] == ("run", "services", "list"):
            return services or []
        return {
            "bindings": [
                {"role": role, "members": [member]}
                for role, member in [
                    ("roles/run.developer", audit.MEMBER),
                    ("roles/artifactregistry.writer", audit.MEMBER),
                    ("roles/iam.serviceAccountUser", audit.MEMBER),
                    (
                        "roles/iam.workloadIdentityUser",
                        "principalSet://iam.googleapis.com/projects/602914367926/"
                        "locations/global/workloadIdentityPools/github-pool/"
                        "attribute.repository/uhey77/grad-checker",
                    ),
                    (
                        "roles/secretmanager.secretAccessor",
                        f"serviceAccount:{audit.RUNTIME}",
                    ),
                ]
            ]
        }

    return read


def test_wif_feature_ref_and_existing_service_block_initial_creation(
    audit, monkeypatch, capsys
):
    monkeypatch.setattr(audit, "read", responses(audit))
    assert audit.main() == 0
    for ref, services in [
        ("refs/heads/feature", None),
        ("refs/heads/main", [{"metadata": {"name": "grad-checker-api"}}]),
    ]:
        monkeypatch.setattr(audit, "read", responses(audit, ref=ref, services=services))
        assert audit.main() == 1
    assert "gcp_initial_metadata_iam" in capsys.readouterr().out


def test_authentication_errors_never_print_raw_response(audit, monkeypatch, capsys):
    def fail(*_args):
        raise ValueError("do-not-log-sensitive-response")

    monkeypatch.setattr(audit, "read", fail)
    assert audit.main() == 1
    assert "do-not-log-sensitive-response" not in capsys.readouterr().out

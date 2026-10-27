"""認証済みCloud Shell用。ログ本文・認証情報を出さず実測と予算を監査する。"""

import json
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime, timedelta

PROJECT = "grad-checker-512505"
SERVICE = "grad-checker-api"
REGION = "asia-northeast1"
BUDGET = "grad-checker-monthly-1000JPY"


def command(*args):
    r = subprocess.run(
        ["gcloud", *args, "--quiet"], capture_output=True, text=True, timeout=60
    )
    return r.stdout.strip() if r.returncode == 0 else None


def read(*args):
    raw = command(*args, "--format=json")
    return json.loads(raw) if raw else None


def metric(token, kind, aligner):
    now = datetime.now(UTC)
    params = {
        "filter": f'resource.type="cloud_run_revision" AND resource.labels.service_name="{SERVICE}" AND resource.labels.location="{REGION}" AND metric.type="run.googleapis.com/{kind}"',
        "interval.endTime": now.isoformat(),
        "interval.startTime": (now - timedelta(hours=1)).isoformat(),
        "aggregation.alignmentPeriod": "60s",
        "aggregation.perSeriesAligner": aligner,
        "view": "FULL",
    }
    request = urllib.request.Request(
        f"https://monitoring.googleapis.com/v3/projects/{PROJECT}/timeSeries?"
        + urllib.parse.urlencode(params),
        headers={"Authorization": f"Bearer {token}"},
    )
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            data = json.load(response)
    except urllib.error.HTTPError as error:
        return {"available": False, "http_status": error.code}
    values = [
        float(p["value"].get("doubleValue", p["value"].get("int64Value", 0)))
        for series in data.get("timeSeries", [])
        for p in series.get("points", [])
    ]
    return {
        "available": bool(values),
        "points": len(values),
        "maximum_aligned_value": max(values) if values else None,
        "sum_aligned_values": sum(values) if aligner == "ALIGN_SUM" else None,
        "truncated": bool(data.get("nextPageToken")),
    }


def main():
    report = {}
    service = read(
        "run",
        "services",
        "describe",
        SERVICE,
        f"--project={PROJECT}",
        f"--region={REGION}",
    )
    if service:
        template = service["spec"]["template"]["spec"]
        assert template["containers"][0]["image"] == (
            "asia-northeast1-docker.pkg.dev/grad-checker-512505/grad-checker/api@sha256:"
            "d3a2081572a5595f0ed7ab8f67f97650f445b366579c63870e6d0f8bd0331571"
        )
        report["service"] = {
            "ready_revision": service["status"].get("latestReadyRevisionName"),
            "runtime_service_account": template["serviceAccountName"],
            "resources": template["containers"][0]["resources"],
            "concurrency": template["containerConcurrency"],
            "revision_annotations": service["spec"]["template"]["metadata"].get(
                "annotations", {}
            ),
        }
    else:
        report["service"] = {"available": False}
    policy = read(
        "run",
        "services",
        "get-iam-policy",
        SERVICE,
        f"--project={PROJECT}",
        f"--region={REGION}",
    )
    report["public_iam"] = (
        [
            {
                "role": b["role"],
                "public_principals": [
                    m
                    for m in b.get("members", [])
                    if m in ("allUsers", "allAuthenticatedUsers")
                ],
            }
            for b in policy.get("bindings", [])
            if any(
                m in ("allUsers", "allAuthenticatedUsers") for m in b.get("members", [])
            )
        ]
        if policy is not None
        else {"available": False}
    )
    since = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
    logs = read(
        "logging",
        "read",
        f'resource.type="cloud_run_revision" AND resource.labels.service_name="{SERVICE}" AND severity>=ERROR AND timestamp>="{since}"',
        f"--project={PROJECT}",
        "--limit=100",
    )
    report["cloud_run_errors_last_hour"] = {
        "available": logs is not None,
        "count": len(logs) if logs is not None else None,
        "limit": 100,
    }
    token = command("auth", "print-access-token")
    if token:
        for kind in (
            "container/memory/utilizations",
            "container/cpu/utilizations",
            "request_count",
        ):
            report[kind] = metric(
                token,
                kind,
                "ALIGN_SUM" if kind == "request_count" else "ALIGN_PERCENTILE_95",
            )
    billing = read("billing", "projects", "describe", PROJECT)
    if billing:
        report["billing_enabled"] = billing.get("billingEnabled")
        account = billing.get("billingAccountName", "")
        if account.startswith("billingAccounts/"):
            identity = account.split("/")[-1]
            detail = read("billing", "accounts", "describe", identity)
            currency = detail.get("currencyCode") if detail else None
            report["billing_currency"] = currency
            budgets = read(
                "billing", "budgets", "list", f"--billing-account={identity}"
            )
            existing = [b for b in budgets or [] if b.get("displayName") == BUDGET]
            if (
                "--configure-budget" in sys.argv
                and currency == "JPY"
                and budgets is not None
                and not existing
            ):
                created = read(
                    "billing",
                    "budgets",
                    "create",
                    f"--billing-account={identity}",
                    f"--display-name={BUDGET}",
                    "--budget-amount=1000JPY",
                    "--calendar-period=month",
                    "--filter-projects=projects/602914367926",
                    "--threshold-rule=percent=0.5",
                    "--threshold-rule=percent=1.0",
                )
                existing = [created] if created else []
            # Report only this project's dedicated budget, never other account budgets or recipients.
            report["budget"] = [
                {
                    "amount": b.get("amount"),
                    "filter": b.get("budgetFilter"),
                    "threshold_rules": b.get("thresholdRules"),
                    "default_iam_recipients_disabled": b.get("allUpdatesRule", {}).get(
                        "disableDefaultIamRecipients", False
                    ),
                }
                for b in existing
            ]
            if not existing:
                report["budget_not_configured"] = (
                    "currency_or_permissions_or_not_requested"
                )
    else:
        report["billing_metadata_available"] = False
    report["budget_is_not_a_spending_cap"] = True
    report["actual_invoice_amount"] = "not_available_from_this_audit"
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(json.dumps({"audit": "FAIL", "error_type": type(error).__name__}))
        sys.exit(1)

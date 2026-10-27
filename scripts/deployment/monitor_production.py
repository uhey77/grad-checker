"""固定本番の読取り監査。Secret値・ログ本文は出力しない。"""

import argparse
import json
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime, timedelta

PROJECT = "grad-checker-512505"
SERVICE = "grad-checker-api"
REGION = "asia-northeast1"
LOG_LIMIT = 10000


def read(*args, projection="json"):
    try:
        result = subprocess.run(
            ["gcloud", *args, f"--format={projection}", "--quiet"],
            check=False,
            capture_output=True,
            text=True,
            timeout=55,
        )
        if result.returncode:
            return None
        return json.loads(result.stdout)
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return None


def metric(token, kind, aligner, start, end, extra=""):
    params = {
        "filter": f'resource.type="cloud_run_revision" AND resource.labels.service_name="{SERVICE}" AND resource.labels.location="{REGION}" AND metric.type="run.googleapis.com/{kind}"{extra}',
        "interval.startTime": start,
        "interval.endTime": end,
        "aggregation.alignmentPeriod": "300s",
        "aggregation.perSeriesAligner": aligner,
        "view": "FULL",
        "pageSize": "1000",
    }
    values = []
    # 上限を明示し、欠測・ページ打切りを0件として扱わない。
    try:
        for _ in range(20):
            request = urllib.request.Request(
                f"https://monitoring.googleapis.com/v3/projects/{PROJECT}/timeSeries?"
                + urllib.parse.urlencode(params),
                headers={"Authorization": f"Bearer {token}"},
            )
            with urllib.request.urlopen(request, timeout=45) as response:
                data = json.load(response)
            for series in data.get("timeSeries", []):
                for point in series.get("points", []):
                    value = point["value"]
                    number = value.get("doubleValue", value.get("int64Value"))
                    if number is not None:
                        values.append(float(number))
            if not data.get("nextPageToken"):
                break
            params["pageToken"] = data["nextPageToken"]
        return {
            "available": True,
            "points": len(values),
            "maximum_aligned_value": max(values) if values else None,
            "sum_aligned_values": sum(values) if aligner == "ALIGN_SUM" else None,
            "truncated": bool(data.get("nextPageToken")),
            "alignment_seconds": 300,
            "aligner": aligner,
        }
    except urllib.error.HTTPError as error:
        return {"available": False, "http_status": error.code}
    except (OSError, ValueError, KeyError):
        return {"available": False}


def log_count(query, start, end):
    rows = read(
        "logging",
        "read",
        f'resource.type="cloud_run_revision" AND resource.labels.service_name="{SERVICE}" AND resource.labels.location="{REGION}" AND timestamp>="{start}" AND timestamp<="{end}" AND ({query})',
        f"--project={PROJECT}",
        f"--limit={LOG_LIMIT}",
        projection="json(insertId)",
    )
    return {
        "available": rows is not None,
        "count": len(rows) if rows is not None else None,
        "possibly_truncated": len(rows) >= LOG_LIMIT if rows is not None else None,
        "limit": LOG_LIMIT,
    }


def report(hours, now=None):
    now = now or datetime.now(UTC)
    start, end = (now - timedelta(hours=hours)).isoformat(), now.isoformat()
    result = {
        "project": PROJECT,
        "service": SERVICE,
        "window_start": start,
        "window_end": end,
        "requested_hours": hours,
    }
    service = read(
        "run",
        "services",
        "describe",
        SERVICE,
        f"--project={PROJECT}",
        f"--region={REGION}",
    )
    if service:
        spec = service["spec"]["template"]
        result["service"] = {
            "ready_revision": service["status"].get("latestReadyRevisionName"),
            "conditions": [
                {"type": c.get("type"), "status": c.get("status")}
                for c in service["status"].get("conditions", [])
            ],
            "traffic": [
                {k: t.get(k) for k in ("revisionName", "percent", "latestRevision")}
                for t in service["status"].get("traffic", [])
            ],
            "image": spec["spec"]["containers"][0]["image"],
            "resources": spec["spec"]["containers"][0].get("resources"),
            "concurrency": spec["spec"].get("containerConcurrency"),
            "scaling": {
                k: v
                for k, v in spec.get("metadata", {}).get("annotations", {}).items()
                if k
                in (
                    "autoscaling.knative.dev/minScale",
                    "autoscaling.knative.dev/maxScale",
                )
            },
        }
    else:
        result["service"] = {"available": False}
    # ログ本文はgcloudの射影で捨て、出力は集計のみ。
    for name, query in {
        "errors": "severity>=ERROR",
        "oom_signals": 'SEARCH("Memory limit") OR SEARCH("OOM") OR SEARCH("out of memory")',
        "termination_signals": 'SEARCH("SIGKILL") OR SEARCH("terminated") OR SEARCH("container exited")',
        "database_connection_signals": 'SEARCH("OperationalError") OR SEARCH("connection refused") OR SEARCH("connection timeout") OR SEARCH("too many connections")',
    }.items():
        result[name] = log_count(query, start, end)
    # tokenはメモリ内だけで利用し、stdout/stderr/例外を出力しない。
    try:
        auth = subprocess.run(
            ["gcloud", "auth", "print-access-token", "--quiet"],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
        token = auth.stdout.strip() if auth.returncode == 0 else ""
    except (OSError, subprocess.TimeoutExpired):
        token = ""
    specs = {
        "cpu_p95": ("container/cpu/utilizations", "ALIGN_PERCENTILE_95", ""),
        "memory_p95": ("container/memory/utilizations", "ALIGN_PERCENTILE_95", ""),
        "requests": ("request_count", "ALIGN_SUM", ""),
        "http_5xx": (
            "request_count",
            "ALIGN_SUM",
            ' AND metric.labels.response_code_class="5xx"',
        ),
        "latency_p95_ms": ("request_latencies", "ALIGN_PERCENTILE_95", ""),
        "instances": ("container/instance_count", "ALIGN_MAX", ""),
    }
    result["metrics"] = {
        name: metric(token, kind, aligner, start, end, extra)
        if token
        else {"available": False}
        for name, (kind, aligner, extra) in specs.items()
    }
    result["actual_invoice_amount"] = "not_available_from_monitoring_api"
    result["limitations"] = [
        "No points is missing data, not proof of zero errors.",
        "Log signals are heuristic counts, not exact restart/connection-error totals.",
        "Maximum of 5-minute per-series p95 is not whole-window p95 or an instantaneous peak.",
        "Coverage starts at deployment/metric availability; a requested 48h window does not prove 48h uptime.",
    ]
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--hours", type=int, choices=(1, 24, 48), default=24)
    args = parser.parse_args()
    try:
        print(json.dumps(report(args.hours), ensure_ascii=False))
    except Exception as error:  # noqa: BLE001 -- 認証情報を含み得る例外本文を出さない
        print(json.dumps({"audit": "FAIL", "error_type": type(error).__name__}))
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()

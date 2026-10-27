"""欠測の誤判定、情報漏えいと監査中の変更操作を防ぐ。"""

import importlib.util
import json
import subprocess
import unittest
import urllib.error
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    "monitor", Path(__file__).with_name("monitor_production.py")
)
monitor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(monitor)


class Response:
    def __init__(self, data):
        self.data = data

    def __enter__(self):
        return self

    def __exit__(self, *_):
        pass

    def read(self, *_):
        return json.dumps(self.data).encode()


class MonitorTests(unittest.TestCase):
    def test_missing_logs_are_not_zero_and_limit_is_explicit(self):
        with patch.object(monitor, "read", return_value=None):
            self.assertEqual(
                monitor.log_count("severity>=ERROR", "start", "end")["count"], None
            )
        with patch.object(monitor, "read", return_value=[{}] * monitor.LOG_LIMIT):
            self.assertTrue(
                monitor.log_count("severity>=ERROR", "start", "end")[
                    "possibly_truncated"
                ]
            )

    def test_metric_pages_are_accumulated_without_zero_filling(self):
        pages = [
            Response(
                {
                    "nextPageToken": "page2",
                    "timeSeries": [{"points": [{"value": {"int64Value": "3"}}]}],
                }
            ),
            Response({"timeSeries": [{"points": [{"value": {"int64Value": "2"}}]}]}),
        ]
        with patch.object(
            monitor.urllib.request, "urlopen", side_effect=pages
        ) as request:
            result = monitor.metric(
                "synthetic-token", "request_count", "ALIGN_SUM", "start", "end"
            )
            self.assertEqual(result["sum_aligned_values"], 5)
            self.assertFalse(result["truncated"])
            self.assertIn("pageToken=page2", request.call_args.args[0].full_url)
        with patch.object(monitor.urllib.request, "urlopen", return_value=Response({})):
            result = monitor.metric(
                "token", "request_count", "ALIGN_SUM", "start", "end"
            )
            self.assertEqual(result["maximum_aligned_value"], None)
            self.assertEqual(result["points"], 0)
            self.assertIsNone(result["sum_aligned_values"])

    def test_permissions_failure_exposes_no_error_body_or_token(self):
        failure = urllib.error.HTTPError("url", 403, "synthetic-secret", {}, None)
        with patch.object(monitor.urllib.request, "urlopen", side_effect=failure):
            result = monitor.metric(
                "synthetic-token", "request_count", "ALIGN_SUM", "start", "end"
            )
        self.assertEqual(result, {"available": False, "http_status": 403})

    def test_report_is_read_only_and_retains_failed_coverage(self):
        calls = []

        def command(args, **_):
            calls.append(args)
            return subprocess.CompletedProcess(args, 1, "", "synthetic-secret")

        with patch.object(monitor.subprocess, "run", side_effect=command):
            result = monitor.report(48, datetime(2026, 10, 27, tzinfo=UTC))
        self.assertEqual(result["window_start"], "2026-10-25T00:00:00+00:00")
        self.assertFalse(result["service"]["available"])
        self.assertFalse(result["metrics"]["http_5xx"]["available"])
        self.assertNotIn("synthetic-secret", json.dumps(result))
        for args in calls:
            self.assertTrue(
                args[1:3]
                in (
                    ["run", "services"],
                    ["logging", "read"],
                    ["auth", "print-access-token"],
                )
            )
            self.assertFalse(
                set(args) & {"create", "update", "replace", "delete", "deploy"}
            )
        logging_calls = [args for args in calls if args[1:3] == ["logging", "read"]]
        self.assertTrue(
            all("--format=json(insertId)" in args for args in logging_calls)
        )


if __name__ == "__main__":
    unittest.main()

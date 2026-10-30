"""本番試験の対象固定と失敗時の復旧をクラウド変更なしで検証する。"""

import copy
import importlib.util
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from test_monitor_production import Response


def load(name, filename):
    spec = importlib.util.spec_from_file_location(
        name, Path(__file__).with_name(filename)
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


cloud = load("cloud_rehearsal", "rehearse_cloud_run.py")
alias = load("alias_verifier", "verify_rehearsal_alias.py")


def baseline():
    return {
        "metadata": {"name": cloud.SERVICE},
        "spec": {
            "template": {
                "metadata": {"annotations": {}},
                "spec": {
                    "serviceAccountName": f"grad-checker-runtime@{cloud.PROJECT}.iam.gserviceaccount.com",
                    "containerConcurrency": 4,
                    "containers": [
                        {
                            "image": cloud.IMAGE,
                            "resources": {"limits": {"cpu": "1", "memory": "512Mi"}},
                            "env": [{"name": "synthetic", "value": "not-for-output"}],
                        }
                    ],
                },
            }
        },
        "status": {
            "url": cloud.ORIGIN,
            "latestReadyRevisionName": cloud.BASELINE,
            "traffic": [{"revisionName": cloud.BASELINE, "percent": 100}],
        },
    }


class CloudTests(unittest.TestCase):
    def test_changed_production_stops_before_any_mutation(self):
        for change in ("image", "traffic", "runtime", "memory"):
            service = baseline()
            if change == "image":
                service["spec"]["template"]["spec"]["containers"][0]["image"] = (
                    "unreviewed"
                )
            elif change == "traffic":
                service["status"]["traffic"][0]["revisionName"] = "unreviewed"
            elif change == "runtime":
                service["spec"]["template"]["spec"]["serviceAccountName"] = "other"
            else:
                service["spec"]["template"]["spec"]["containers"][0]["resources"][
                    "limits"
                ]["memory"] = "1Gi"
            with (
                tempfile.TemporaryDirectory() as directory,
                patch.object(cloud, "gcloud", return_value=service) as command,
            ):
                with self.assertRaises(ValueError):
                    cloud.update(Path(directory) / "state", "123")
                self.assertEqual(command.call_count, 1)

    def test_failed_deployment_retains_state_for_always_restore(self):
        calls = []

        def command(*args):
            calls.append(args)
            if args[0] == "deploy":
                raise RuntimeError("synthetic deployment failure")
            return baseline()

        with (
            tempfile.TemporaryDirectory() as directory,
            patch.object(cloud, "gcloud", side_effect=command),
            patch.object(cloud, "readiness"),
        ):
            path = Path(directory) / "state"
            with self.assertRaises(RuntimeError):
                cloud.update(path, "123")
            self.assertTrue(json.loads(path.read_text())["mutation_started"])
            self.assertNotIn("not-for-output", path.read_text())
            cloud.restore(path)
            self.assertTrue(json.loads(path.read_text())["restore_verified"])
        self.assertIn(
            (
                "services",
                "update-traffic",
                cloud.SERVICE,
                f"--to-revisions={cloud.BASELINE}=100",
            ),
            calls,
        )

    def test_success_switches_only_reviewed_revisions_and_restores(self):
        service = baseline()
        calls = []

        def command(*args):
            calls.append(args)
            if args[0] == "deploy":
                self.assertIn(f"--image={cloud.IMAGE}", args)
                self.assertIn("--no-traffic", args)
                # --no-trafficではサービスのlatestReadyを判定根拠にしない。
            if args[:2] == ("revisions", "describe"):
                return {
                    "metadata": {"name": args[2]},
                    "status": {
                        "imageDigest": cloud.IMAGE,
                        "conditions": [{"type": "Ready", "status": "True"}],
                    },
                }
            if args[:2] == ("services", "update-traffic"):
                revision = args[-1].removeprefix("--to-revisions=").removesuffix("=100")
                service["status"]["traffic"] = [
                    {"revisionName": revision, "percent": 100}
                ]
            return copy.deepcopy(service)

        with (
            tempfile.TemporaryDirectory() as directory,
            patch.object(cloud, "gcloud", side_effect=command),
            patch.object(cloud, "readiness"),
        ):
            path = Path(directory) / "state"
            cloud.update(path, "123")
            cloud.restore(path)
            state = json.loads(path.read_text())
            self.assertTrue(state["update_verified"] and state["restore_verified"])
        self.assertTrue(cloud.traffic_is(service, cloud.BASELINE))
        self.assertFalse(
            any(
                set(call) & {"delete", "set-iam-policy", "add-iam-policy-binding"}
                for call in calls
            )
        )

    def test_revision_failures_and_configuration_changes_prevent_switch(self):
        for failure in ("name", "ready", "image", "configuration", "traffic"):
            with self.subTest(failure=failure):
                service = baseline()
                calls = []

                def command(*args, calls=calls, failure=failure, service=service):
                    calls.append(args)
                    if args[0] == "deploy":
                        if failure == "configuration":
                            service["spec"]["template"]["spec"]["containers"][0]["env"][
                                0
                            ]["value"] = "changed-secret-value"
                        if failure == "traffic":
                            service["status"]["traffic"][0]["revisionName"] = "other"
                    if args[:2] == ("revisions", "describe"):
                        return {
                            "metadata": {
                                "name": "other" if failure == "name" else args[2]
                            },
                            "status": {
                                "imageDigest": "wrong"
                                if failure == "image"
                                else cloud.IMAGE,
                                "conditions": [
                                    {
                                        "type": "Ready",
                                        "status": "False"
                                        if failure == "ready"
                                        else "True",
                                    }
                                ],
                            },
                        }
                    return copy.deepcopy(service)

                with (
                    tempfile.TemporaryDirectory() as directory,
                    patch.object(cloud, "gcloud", side_effect=command),
                    patch.object(cloud, "readiness"),
                ):
                    with self.assertRaises(cloud.RehearsalError) as caught:
                        cloud.update(Path(directory) / "state", "123")
                    expected = {
                        "name": "revision_name_mismatch",
                        "ready": "revision_not_ready",
                        "image": "revision_image_mismatch",
                        "configuration": "configuration_mismatch",
                        "traffic": "unexpected_traffic_before_switch",
                    }
                    self.assertEqual(caught.exception.code, expected[failure])
                    self.assertNotIn(
                        "changed-secret-value",
                        json.dumps(cloud.failure_report(caught.exception)),
                    )
                self.assertFalse(
                    any(c[:2] == ("services", "update-traffic") for c in calls)
                )

    def test_command_diagnostics_never_include_cli_output_or_arguments(self):
        result = subprocess.CompletedProcess(
            [], 1, "synthetic-secret", "synthetic-secret"
        )
        with (
            patch.object(cloud.subprocess, "run", return_value=result),
            self.assertRaises(cloud.RehearsalError) as caught,
        ):
            cloud.command("gcloud", "synthetic-secret")
        report = cloud.failure_report(caught.exception)
        self.assertEqual(report["error_code"], "command_failed")
        self.assertEqual(report["exit_code"], 1)
        self.assertNotIn("synthetic-secret", json.dumps(report))
        with (
            patch.object(
                cloud.subprocess,
                "run",
                side_effect=subprocess.TimeoutExpired("synthetic-secret", 600),
            ),
            self.assertRaises(cloud.RehearsalError) as caught,
        ):
            cloud.command("gcloud")
        self.assertEqual(
            cloud.failure_report(caught.exception)["error_code"], "command_timeout"
        )

    def test_concurrent_unknown_traffic_is_not_overwritten(self):
        service = baseline()
        service["status"]["traffic"][0]["revisionName"] = "external-update"
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.object(cloud, "gcloud", return_value=service) as command,
        ):
            path = Path(directory) / "state"
            cloud.save(
                path,
                {
                    "baseline": cloud.BASELINE,
                    "revision": f"{cloud.SERVICE}-rehearsal-123",
                },
            )
            with self.assertRaises(RuntimeError):
                cloud.restore(path)
            self.assertEqual(command.call_count, 1)

    def test_invalid_run_id_cannot_start(self):
        with patch.object(cloud, "gcloud") as command:
            with self.assertRaises(ValueError):
                cloud.update(Path("unused"), "123;bad")
            command.assert_not_called()


class AliasTests(unittest.TestCase):
    def test_stage_project_and_ready_state_are_verified_before_alias(self):
        project = "prj_QgFMi1xMYgrYLGPI1Yi9h0kdkNzW"
        deployment = {
            "project": {"id": project},
            "target": "production",
            "readyState": "READY",
            "id": "dpl_stage",
        }
        alias_data = {"projectId": project, "deploymentId": "dpl_stage"}
        with patch.dict(
            os.environ,
            {
                "EXPECTED_DEPLOYMENT": "https://grad-checker-test.vercel.app",
                "VERCEL_TOKEN": "synthetic-token",
            },
        ):
            with patch.object(
                alias.urllib.request,
                "urlopen",
                side_effect=[Response(deployment), Response(alias_data)],
            ):
                alias.verify()
            with patch.object(
                alias.urllib.request,
                "urlopen",
                return_value=Response({**deployment, "target": "preview"}),
            ) as request:
                with self.assertRaises(ValueError):
                    alias.verify()
                self.assertEqual(request.call_count, 1)

    def test_alias_must_match_both_project_and_deployment(self):
        good = {
            "projectId": "prj_QgFMi1xMYgrYLGPI1Yi9h0kdkNzW",
            "deploymentId": "dpl_expected",
        }
        for value in (
            good,
            {**good, "projectId": "other"},
            {**good, "deploymentId": "dpl_other"},
        ):
            with (
                patch.dict(
                    os.environ,
                    {
                        "EXPECTED_DEPLOYMENT": "dpl_expected",
                        "VERCEL_TOKEN": "synthetic-token",
                    },
                ),
                patch.object(
                    alias.urllib.request, "urlopen", return_value=Response(value)
                ),
            ):
                if value == good:
                    alias.verify()
                else:
                    with self.assertRaises(ValueError):
                        alias.verify()

    def test_untrusted_stage_url_is_rejected_before_authentication(self):
        with (
            patch.dict(
                os.environ,
                {
                    "EXPECTED_DEPLOYMENT": "https://evil.example",
                    "VERCEL_TOKEN": "synthetic-token",
                },
            ),
            patch.object(alias.urllib.request, "urlopen") as request,
        ):
            with self.assertRaises(ValueError):
                alias.verify()
            request.assert_not_called()


if __name__ == "__main__":
    unittest.main()

"""本番試験の対象固定と失敗時の復旧をクラウド変更なしで検証する。"""

import copy
import importlib.util
import json
import os
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
                service["status"]["latestReadyRevisionName"] = (
                    f"{cloud.SERVICE}-rehearsal-123"
                )
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

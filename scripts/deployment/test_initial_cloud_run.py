"""初回manifestの対象制限とデータ・公開保護を検証する。"""

import unittest
from initial_cloud_run import IMAGE, RUNTIME, manifest


class InitialManifestTest(unittest.TestCase):
    def test_invalid_digest_cannot_render(self):
        for value in ("latest", "sha256:abc", "a" * 64, "sha256:" + "G" * 64):
            with self.assertRaises(ValueError):
                manifest(value)

    def test_approved_resources_and_runtime_secret_only(self):
        digest = "sha256:" + "a" * 64
        service = manifest(digest)
        self.assertFalse(service["invokerIamDisabled"])
        template = service["template"]
        self.assertEqual(template["serviceAccount"], RUNTIME)
        self.assertEqual(
            template["scaling"], {"minInstanceCount": 0, "maxInstanceCount": 1}
        )
        self.assertEqual(template["maxInstanceRequestConcurrency"], 4)
        container = template["containers"][0]
        self.assertEqual(container["image"], IMAGE + "@" + digest)
        self.assertEqual(
            container["resources"]["limits"], {"cpu": "1", "memory": "512Mi"}
        )
        self.assertTrue(container["resources"]["cpuIdle"])
        self.assertFalse(container["resources"]["startupCpuBoost"])
        env = {item["name"]: item for item in container["env"]}
        self.assertEqual(set(env), {"DATABASE_URL", "PUBLIC_ORIGIN"})
        self.assertEqual(
            env["DATABASE_URL"]["valueSource"]["secretKeyRef"],
            {"secret": "grad-checker-database-url", "version": "1"},
        )
        self.assertEqual(container["startupProbe"]["httpGet"]["path"], "/api/ready")


if __name__ == "__main__":
    unittest.main()

import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, mkdirSync, writeFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { spawnSync } from "node:child_process";

function verify({
  project = "expected",
  data = "CLOUD_RUN_API_ORIGIN=https://api.example.run.app\n",
} = {}) {
  const cwd = mkdtempSync(join(tmpdir(), "grad-checker-env-"));
  try {
    mkdirSync(join(cwd, ".vercel"));
    writeFileSync(
      join(cwd, ".vercel/project.json"),
      JSON.stringify({
        projectId: project,
        orgId: "expected-team",
        settings: {
          rootDirectory: "frontend",
          framework: "vite",
          nodeVersion: "24.x",
        },
      }),
    );
    writeFileSync(join(cwd, ".vercel/.env.production.local"), data);
    return spawnSync(
      process.execPath,
      [resolve("scripts/deployment/verify-frontend-env.mjs")],
      {
        cwd,
        encoding: "utf8",
        env: {
          ...process.env,
          VERCEL_PROJECT_ID: "expected",
          VERCEL_ORG_ID: "expected-team",
        },
      },
    );
  } finally {
    rmSync(cwd, { recursive: true, force: true });
  }
}

test("existing frontend project and nonsecret proxy setting are accepted", () => {
  const result = verify();
  assert.equal(result.status, 0, result.stderr);
});

test("a different Vercel project is rejected before building", () => {
  assert.notEqual(verify({ project: "different-project" }).status, 0);
});

test("database credentials are rejected without logging their values", () => {
  const marker = "synthetic-private-value";
  const result = verify({ data: `DATABASE_URL=${marker}\n` });
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /Server credentials/);
  assert.doesNotMatch(result.stderr + result.stdout, new RegExp(marker));
});

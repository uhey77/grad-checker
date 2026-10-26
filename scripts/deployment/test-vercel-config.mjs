import { test } from "node:test";
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";

function load(origin) {
  const environment = { ...process.env };
  delete environment.CLOUD_RUN_API_ORIGIN;
  if (origin) environment.CLOUD_RUN_API_ORIGIN = origin;
  return spawnSync(process.execPath, ["--input-type=module", "-e", "const { config } = await import('./frontend/vercel.mjs'); console.log(JSON.stringify(config));"], { env: environment, encoding: "utf8" });
}

test("missing or unsafe proxy destination fails closed", () => {
  for (const origin of [undefined, "http://api.run.app", "https://evil.example", "https://api.run.app/path", "https://user:password@api.run.app"]) {
    assert.notEqual(load(origin).status, 0);
  }
});

test("API proxy precedes SPA fallback and automatic Git releases are disabled", () => {
  const result = load("https://grad-checker-api.example.run.app");
  assert.equal(result.status, 0, result.stderr);
  const config = JSON.parse(result.stdout);
  assert.equal(config.git.deploymentEnabled, false);
  assert.equal(config.rewrites[0].source, "/api/:path*");
  assert.equal(config.rewrites[0].destination, "https://grad-checker-api.example.run.app/api/:path*");
  assert.equal(config.rewrites[1].destination, "/index.html");
  assert.equal(config.headers[0].headers[0].value, "private, no-store");
  assert.doesNotMatch(result.stdout, /DATABASE_URL/);
});

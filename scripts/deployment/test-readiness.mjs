import { test } from "node:test";
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";

function verify(input) {
  return spawnSync(process.execPath, ["scripts/deployment/verify-readiness.mjs"], {
    input,
    encoding: "utf8",
  });
}

test("readiness accepts the API success response", () => {
  assert.equal(verify('{"status":"ok"}').status, 0);
});

test("readiness rejects SPA HTML and unhealthy JSON without logging the body", () => {
  for (const input of ['<html><div id="root">sensitive-body</div></html>', '{"status":"unavailable"}', 'null', '{}']) {
    const result = verify(input);
    assert.notEqual(result.status, 0);
    assert.ok(!result.stderr.includes(input));
    assert.ok(!result.stdout.includes("sensitive-body"));
  }
});

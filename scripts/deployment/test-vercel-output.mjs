import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, writeFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { spawnSync } from "node:child_process";

const origin = "https://grad-checker-audit.invalid.run.app";
function verify(routes) {
  const dir = mkdtempSync(join(tmpdir(), "vercel-output-"));
  try {
    const file = join(dir, "config.json");
    writeFileSync(file, JSON.stringify({ version: 3, framework: { slug: "vite" }, routes }));
    return spawnSync(process.execPath, ["scripts/deployment/verify-vercel-output.mjs", file], { env: { ...process.env, CLOUD_RUN_API_ORIGIN: origin }, encoding: "utf8" });
  } finally { rmSync(dir, { recursive: true }); }
}
const routes = [
  { src: "^/api(?:/(.*))?$", continue: true, headers: { "Cache-Control": "private, no-store" } },
  { handle: "filesystem" },
  { src: "^/api(?:/(.*))?$", dest: origin + "/api/$1" },
  { src: "^/((?!api(?:/|$)|assets/).*)$", dest: "/index.html" },
];
test("compiled API rewrites preserve paths and SPA excludes API and assets", () => {
  const result = verify(routes);
  assert.equal(result.status, 0, result.stderr);
});
test("compiled output rejects missing, wrong or shadowed API rewrites", () => {
  for (const broken of [routes.slice(0, 2), [{ src: "^/(.*)$", dest: "/index.html" }, ...routes], routes.map(r => r.dest?.startsWith(origin) ? { ...r, dest: "https://wrong.run.app/api/$1" } : r)]) {
    assert.notEqual(verify(broken).status, 0);
  }
});

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const origin = process.env.CLOUD_RUN_API_ORIGIN;
const url = new URL(origin);
assert.ok(url.protocol === "https:" && url.origin === origin && url.hostname.endsWith(".run.app"), "Invalid Cloud Run origin");
const config = JSON.parse(readFileSync(process.argv[2] ?? ".vercel/output/config.json", "utf8"));
assert.equal(config.version, 3);
assert.equal(config.framework?.slug, "vite");
const rewrites = config.routes.filter((route) => route.dest);
function destination(path) {
  const route = rewrites.find((candidate) => new RegExp(candidate.src).test(path));
  return route ? path.replace(new RegExp(route.src), route.dest) : undefined;
}
for (const path of ["/api", "/api/ready", "/api/auth/session", "/api/unknown/path"]) {
  assert.equal(destination(path), origin + (path === "/api" ? "/api/" : path));
}
for (const path of ["/", "/acceptance-check", "/grades"]) {
  assert.equal(destination(path), "/index.html");
}
assert.notEqual(destination("/assets/missing.js"), "/index.html");
const apiHeaders = config.routes.find((route) => route.continue && new RegExp(route.src).test("/api/ready") && route.headers?.["Cache-Control"]);
assert.match(apiHeaders?.headers["Cache-Control"] ?? "", /no-store/);
console.log("Vercel build output verified: API proxy, SPA fallback, assets, no-store");

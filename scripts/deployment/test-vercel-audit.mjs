import { test } from "node:test";
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";

const target = { id: "prj_QgFMi1xMYgrYLGPI1Yi9h0kdkNzW", accountId: "team_tZDGBnNdyZxvlZvkV86h6SGv", name: "grad-checker", rootDirectory: "frontend", nodeVersion: "24.x", framework: "vite", buildCommand: "npm run build", installCommand: "npm ci", link: null, gitProviderOptions: { createDeployments: "disabled", disableRepositoryDispatchEvents: true } };
function audit(project = target, status = 200) {
  const code = `globalThis.fetch=async(url,options)=>{if(options.method!=="GET" || options.redirect!=="error" || url!=="https://api.vercel.com/v9/projects/prj_QgFMi1xMYgrYLGPI1Yi9h0kdkNzW?teamId=team_tZDGBnNdyZxvlZvkV86h6SGv") throw new Error("unsafe request");return {ok:${status === 200},status:${status},json:async()=>(${JSON.stringify(project)})}};await import('./scripts/deployment/audit-vercel-project.mjs');`;
  return spawnSync(process.execPath, ["--input-type=module", "-e", code], { env: { ...process.env, VERCEL_TOKEN: "test-secret-marker" }, encoding: "utf8" });
}
test("manual token audit only accepts the fixed project and disabled Git releases", () => {
  assert.equal(audit().status, 0);
  for (const p of [{ ...target, id: "other" }, { ...target, rootDirectory: "." }, { ...target, nodeVersion: "22.x" }, { ...target, link: { repo: "grad-checker" } }, { ...target, gitProviderOptions: {} }]) assert.notEqual(audit(p).status, 0);
});
test("token audit reports authorization failures without response bodies or secrets", () => {
  const r = audit({ error: "test-secret-marker" }, 403);
  assert.notEqual(r.status, 0);
  assert.match(r.stderr, /HTTP 403/);
  assert.ok(!(r.stdout+r.stderr).includes("test-secret-marker"));
});

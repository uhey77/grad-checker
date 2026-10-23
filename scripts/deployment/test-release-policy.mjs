import { test } from "node:test";
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";

function check({
  repository = "uhey77/grad-checker",
  ref = "refs/heads/main",
  reviews = true,
  policies = [{ name: "main", type: "branch" }],
  available = true,
} = {}) {
  const replies = [
    {
      protection_rules: reviews
        ? [{ type: "required_reviewers", reviewers: [{}] }]
        : [],
      deployment_branch_policy: { custom_branch_policies: true },
    },
    { branch_policies: policies },
  ];
  const mock = `const replies=${JSON.stringify(replies)}; globalThis.fetch=async()=>({ok:${available},json:async()=>replies.shift()}); await import('./scripts/deployment/check-release-policy.mjs');`;
  return spawnSync(process.execPath, ["--input-type=module", "-e", mock], {
    env: {
      ...process.env,
      GITHUB_REPOSITORY: repository,
      GITHUB_REF: ref,
      GH_TOKEN: "test-only",
    },
    encoding: "utf8",
  });
}

test("production release requires the expected repository and main", () => {
  assert.notEqual(check({ repository: "other/repository" }).status, 0);
  assert.notEqual(check({ ref: "refs/heads/feature" }).status, 0);
});

test("missing reviewers, wildcard/tag policy, or unreadable environment blocks release", () => {
  assert.notEqual(check({ reviews: false }).status, 0);
  assert.notEqual(
    check({ policies: [{ name: "*", type: "branch" }] }).status,
    0,
  );
  assert.notEqual(
    check({ policies: [{ name: "main", type: "tag" }] }).status,
    0,
  );
  assert.notEqual(check({ available: false }).status, 0);
});

test("protected production environment restricted to main permits release", () => {
  const result = check();
  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout, /policy verified/);
});

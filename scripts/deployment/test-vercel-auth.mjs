import { test } from "node:test";
import assert from "node:assert/strict";
import { checkVercelAuth } from "./check-vercel-auth.mjs";

const marker = "secret-or-private-identity";
async function check({ token = marker, status = 200, networkError = false, cliStatus = 0, cliError = false } = {}) {
  const messages = [];
  let requests = 0;
  let cliCalls = 0;
  const passed = await checkVercelAuth({
    token,
    request: async (url, options) => {
      requests++;
      assert.equal(url, "https://api.vercel.com/v2/user");
      assert.equal(options.method, "GET");
      assert.equal(options.redirect, "error");
      assert.equal(options.headers.Authorization, `Bearer ${marker}`);
      if (networkError) throw new Error(marker);
      return { ok: status === 200, status, json() { throw new Error("Do not read private identity"); } };
    },
    run: (command, args, options) => {
      cliCalls++;
      assert.equal(command, "vercel");
      assert.deepEqual(args, ["whoami", "--non-interactive"]);
      assert.equal(options.env.VERCEL_TOKEN, marker);
      assert.equal(options.stdio, "ignore");
      assert.equal(options.timeout, 30000);
      return { status: cliStatus, error: cliError ? new Error(marker) : undefined, stdout: marker, stderr: marker };
    },
    report: (message) => messages.push(message),
  });
  assert.ok(!messages.join("\n").includes(marker));
  return { passed, requests, cliCalls, messages: messages.join("\n") };
}

test("missing Secret stops before API or CLI access", async () => {
  for (const token of ["", "  "]) {
    const result = await check({ token });
    assert.equal(result.passed, false);
    assert.equal(result.requests, 0);
    assert.equal(result.cliCalls, 0);
  }
});

test("API authentication failures and network errors stop before CLI access", async () => {
  for (const status of [401, 403, 404, 500]) {
    const result = await check({ status });
    assert.equal(result.passed, false);
    assert.equal(result.cliCalls, 0);
    assert.match(result.messages, new RegExp(`HTTP ${status}`));
  }
  const result = await check({ networkError: true });
  assert.equal(result.passed, false);
  assert.equal(result.cliCalls, 0);
  assert.match(result.messages, /network/);
});

test("CLI failure is distinguished from successful API authentication", async () => {
  for (const options of [{ cliStatus: 1 }, { cliStatus: null, cliError: true }]) {
    const result = await check(options);
    assert.equal(result.passed, false);
    assert.match(result.messages, /CLI authentication failed after user API authentication passed/);
  }
});

test("valid API and CLI authentication passes without recording identity", async () => {
  const result = await check();
  assert.equal(result.passed, true);
  assert.equal(result.requests, 1);
  assert.equal(result.cliCalls, 1);
});

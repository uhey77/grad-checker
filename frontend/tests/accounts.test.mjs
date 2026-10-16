import assert from "node:assert/strict";
import test from "node:test";
import { pathToFileURL } from "node:url";
import { join } from "node:path";

const directory = process.env.SUBJECT_TEST_BUILD_DIRECTORY;
const { HttpAuthRepository } = await import(
  pathToFileURL(
    join(directory, "modules/accounts/infrastructure/HttpAuthRepository.js"),
  )
);
const { AuthUseCases } = await import(
  pathToFileURL(join(directory, "modules/accounts/application/AuthUseCases.js"))
);

test("認証のDTO変換とCookie・CSRFの送信契約", async (context) => {
  const requests = [];
  context.mock.method(globalThis, "fetch", async (url, options) => {
    requests.push({ url, options });
    if (url.endsWith("/config"))
      return Response.json({
        policy: {
          password_min_length: 12,
          password_max_length: 128,
        },
      });
    if (url.endsWith("/register"))
      return Response.json(
        { registered: true, recovery_code: "r".repeat(43) },
        { status: 201 },
      );
    if (url.endsWith("/recover"))
      return Response.json({ recovered: true, recovery_code: "n".repeat(43) });
    if (url.endsWith("/logout")) return Response.json({ authenticated: false });
    return Response.json({
      authenticated: true,
      student: { id: "student-id", login_name: "student_01" },
      csrf_token: "csrf",
      expires_at: "2026-10-12T00:00:00+00:00",
    });
  });
  const service = new AuthUseCases(new HttpAuthRepository("/api/auth"));
  assert.deepEqual(await service.config(), {
    passwordMinLength: 12,
    passwordMaxLength: 128,
  });
  assert.equal(
    await service.register("student_01", "application-password"),
    "r".repeat(43),
  );
  assert.equal(
    await service.recover("student_01", "r".repeat(43), "new-password-123"),
    "n".repeat(43),
  );
  const session = await service.login("student_01", "application-password");
  assert.equal(session.student.loginName, "student_01");
  assert.equal(session.csrfToken, "csrf");
  assert.deepEqual(await service.session(), session);
  await service.logout(session.csrfToken);
  for (const request of requests) {
    assert.equal(request.options.credentials, "same-origin");
    assert.equal(request.options.cache, "no-store");
    assert.ok(!request.url.includes("r".repeat(43)));
  }
  assert.deepEqual(JSON.parse(requests[1].options.body), {
    login_name: "student_01",
    password: "application-password",
  });
  assert.deepEqual(JSON.parse(requests[2].options.body), {
    login_name: "student_01",
    recovery_code: "r".repeat(43),
    password: "new-password-123",
  });
  assert.equal(requests.at(-1).options.headers["X-CSRF-Token"], "csrf");
});

test("未認証と通信失敗・不正応答を区別する", async (context) => {
  const repository = new HttpAuthRepository("/api/auth");
  const fetch = context.mock.method(globalThis, "fetch", async () =>
    Response.json({ detail: "未認証" }, { status: 401 }),
  );
  assert.equal(await repository.session(), null);
  fetch.mock.mockImplementation(async () =>
    Response.json({ detail: "試行上限です" }, { status: 429 }),
  );
  await assert.rejects(
    repository.login("student_01", "password"),
    (error) => error.status === 429 && error.detail === "試行上限です",
  );
  fetch.mock.mockImplementation(async () =>
    Response.json({ authenticated: true, student: {} }),
  );
  await assert.rejects(repository.session(), (error) => error.status === 502);
  fetch.mock.mockImplementation(async () => {
    throw new TypeError("network");
  });
  await assert.rejects(repository.session(), (error) => error.status === 0);
});

test("キャンセルは認証エラーへ変換しない", async (context) => {
  const controller = new AbortController();
  controller.abort();
  const reason = new DOMException("Aborted", "AbortError");
  context.mock.method(globalThis, "fetch", async () => {
    throw reason;
  });
  await assert.rejects(
    new HttpAuthRepository("/api/auth").session(controller.signal),
    (error) => error === reason,
  );
});

test("JSONでない応答でもHTTPエラーを保ち、成功時の不正応答と区別する", async (context) => {
  const repository = new HttpAuthRepository("/api/auth");
  const fetch = context.mock.method(
    globalThis,
    "fetch",
    async () => new Response("Service unavailable", { status: 503 }),
  );
  await assert.rejects(repository.session(), (error) => error.status === 503);
  fetch.mock.mockImplementation(async () => new Response("not json"));
  await assert.rejects(repository.session(), (error) => error.status === 502);
  fetch.mock.mockImplementation(
    async () => new Response("Unauthorized", { status: 401 }),
  );
  assert.equal(await repository.session(), null);
});

test("不正なパスワード長の設定を受け入れない", async (context) => {
  const repository = new HttpAuthRepository("/api/auth");
  const fetch = context.mock.method(globalThis, "fetch", async () =>
    Response.json({
      policy: { password_min_length: 0, password_max_length: 128 },
    }),
  );
  await assert.rejects(repository.config(), (error) => error.status === 502);
  fetch.mock.mockImplementation(async () =>
    Response.json({
      policy: { password_min_length: 32, password_max_length: 12 },
    }),
  );
  await assert.rejects(repository.config(), (error) => error.status === 502);
});
